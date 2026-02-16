from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.models.patent import Patent
from typing import List, Optional, Tuple
from uuid import UUID
import logging
from app.config import settings
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


async def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding vector for text using configured embedding service.
    
    Args:
        text: Input text to embed
        
    Returns:
        List of floats representing the embedding vector
    """
    try:
        embedding = await embedding_service.generate_embedding(text)
        return embedding
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        # Return zero vector as fallback
        return [0.0] * settings.EMBEDDING_DIMENSION


async def search_top_5_patents(
    db: AsyncSession,
    query_text: str,
    project_id: Optional[UUID] = None,
    similarity_threshold: float = 0.5
) -> List[Tuple[Patent, float]]:
    """
    Search for top 5 most similar patents using cosine similarity.
    Uses pgvector's <=> operator for optimized cosine distance.
    
    Args:
        db: Database session
        query_text: Text query to search for
        project_id: Optional project ID to filter results
        similarity_threshold: Minimum similarity score (0-1)
        
    Returns:
        List of (Patent, similarity_score) tuples, ordered by similarity (desc)
    """
    # Generate embedding for query
    query_embedding = await generate_embedding(query_text)
    
    # Build SQL query with cosine distance operator
    # Note: <=> returns distance (0 = identical, 2 = opposite)
    # similarity = 1 - (distance / 2) for normalized [0, 1] range
    # But pgvector's cosine_distance already returns [0, 2], so we use 1 - distance/2
    # Actually, for normalized vectors: cosine_similarity = 1 - cosine_distance
    
    query_sql = text("""
        SELECT 
            p.*,
            (1 - (p.embedding <=> :query_embedding)) AS similarity_score
        FROM patents p
        WHERE p.embedding IS NOT NULL
          AND (1 - (p.embedding <=> :query_embedding)) >= :threshold
          AND (:project_id IS NULL OR p.project_id = :project_id)
        ORDER BY p.embedding <=> :query_embedding
        LIMIT 5
    """)
    
    # Execute query
    result = await db.execute(
        query_sql,
        {
            "query_embedding": query_embedding,
            "threshold": similarity_threshold,
            "project_id": str(project_id) if project_id else None
        }
    )
    
    # Parse results
    rows = result.fetchall()
    patents_with_scores = []
    
    for row in rows:
        # Create Patent object from row
        patent = Patent(
            id=row.id,
            patent_number=row.patent_number,
            title=row.title,
            description=row.description,
            content=row.content,
            filing_date=row.filing_date,
            embedding=row.embedding,
            project_id=row.project_id,
            created_at=row.created_at,
            updated_at=row.updated_at
        )
        similarity_score = float(row.similarity_score)
        patents_with_scores.append((patent, similarity_score))
    
    logger.info(f"Found {len(patents_with_scores)} similar patents for query")
    return patents_with_scores


async def search_similar_patents(
    db: AsyncSession,
    query_embedding: List[float],
    project_id: Optional[UUID] = None,
    limit: int = 10,
    similarity_threshold: float = 0.7
) -> List[Tuple[Patent, float]]:
    """
    Search for similar patents using vector similarity.
    Returns list of (Patent, similarity_score) tuples.
    
    Args:
        db: Database session
        query_embedding: Pre-computed embedding vector
        project_id: Optional project ID to filter results
        limit: Maximum number of results
        similarity_threshold: Minimum similarity score
        
    Returns:
        List of (Patent, similarity_score) tuples
    """
    # Build query with pgvector's cosine similarity
    query = select(
        Patent,
        (1 - Patent.embedding.cosine_distance(query_embedding)).label("similarity")
    ).where(
        Patent.embedding.isnot(None)
    )
    
    # Filter by project if specified
    if project_id:
        query = query.where(Patent.project_id == project_id)
    
    # Filter by similarity threshold and order by similarity
    query = query.where(
        (1 - Patent.embedding.cosine_distance(query_embedding)) >= similarity_threshold
    ).order_by(
        text("similarity DESC")
    ).limit(limit)
    
    result = await db.execute(query)
    rows = result.all()
    
    return [(row[0], row[1]) for row in rows]


async def search_patents_by_text(
    db: AsyncSession,
    query_text: str,
    project_id: Optional[UUID] = None,
    limit: int = 10,
    similarity_threshold: float = 0.7
) -> List[Tuple[Patent, float]]:
    """
    Search patents by text query.
    Generates embedding for query text and performs similarity search.
    
    Args:
        db: Database session
        query_text: Text query
        project_id: Optional project filter
        limit: Maximum results
        similarity_threshold: Minimum similarity
        
    Returns:
        List of (Patent, similarity_score) tuples
    """
    # Generate embedding for query text
    query_embedding = await generate_embedding(query_text)
    
    # Perform similarity search
    results = await search_similar_patents(
        db=db,
        query_embedding=query_embedding,
        project_id=project_id,
        limit=limit,
        similarity_threshold=similarity_threshold
    )
    
    return results
