from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, List
from uuid import UUID
from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.patent import (
    PatentCreate,
    PatentUpdate,
    PatentResponse,
    PatentSearchQuery,
    PatentSearchResult
)
from app.services.patent_service import (
    create_patent,
    get_patent,
    update_patent,
    delete_patent
)
from app.services.vector_service import search_patents_by_text
from app.services.celery_tasks import generate_patent_embedding_task


router = APIRouter(prefix="/patents", tags=["patents"])


@router.post("", response_model=PatentResponse, status_code=status.HTTP_201_CREATED)
async def create_new_patent(
    patent_data: PatentCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Create a new patent.
    Triggers async embedding generation.
    """
    # Create patent without embedding first
    patent = await create_patent(db, patent_data, embedding=None)
    
    # Trigger async embedding generation
    generate_patent_embedding_task.delay(str(patent.id), patent.content)
    
    return patent


@router.get("/{patent_id}", response_model=PatentResponse)
async def get_patent_by_id(
    patent_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Get a patent by ID.
    """
    patent = await get_patent(db, patent_id)
    
    if not patent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patent not found"
        )
    
    return patent


@router.put("/{patent_id}", response_model=PatentResponse)
async def update_patent_by_id(
    patent_id: UUID,
    patent_data: PatentUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Update a patent.
    """
    patent = await update_patent(db, patent_id, patent_data)
    
    if not patent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patent not found"
        )
    
    # If content was updated, regenerate embedding
    if "content" in patent_data.model_dump(exclude_unset=True):
        generate_patent_embedding_task.delay(str(patent.id), patent.content)
    
    return patent


@router.delete("/{patent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patent_by_id(
    patent_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Delete a patent.
    """
    success = await delete_patent(db, patent_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patent not found"
        )


@router.post("/search", response_model=List[PatentSearchResult])
async def search_patents(
    search_query: PatentSearchQuery,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Search patents using semantic similarity.
    """
    results = await search_patents_by_text(
        db=db,
        query_text=search_query.query_text,
        project_id=search_query.project_id,
        limit=search_query.limit,
        similarity_threshold=search_query.similarity_threshold
    )
    
    # Convert to response schema
    return [
        PatentSearchResult(**patent.__dict__, similarity_score=score)
        for patent, score in results
    ]


@router.post("/search/top5", response_model=List[PatentSearchResult])
async def search_top_5_similar_patents(
    search_query: PatentSearchQuery,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Search for top 5 most similar patents using optimized cosine similarity.
    Uses pgvector's <=> operator for fast vector search.
    """
    from app.services.vector_service import search_top_5_patents
    
    results = await search_top_5_patents(
        db=db,
        query_text=search_query.query_text,
        project_id=search_query.project_id,
        similarity_threshold=search_query.similarity_threshold
    )
    
    # Convert to response schema
    return [
        PatentSearchResult(**patent.__dict__, similarity_score=score)
        for patent, score in results
    ]


@router.get("/espacenet/{patent_number}")
async def fetch_espacenet_patent(
    patent_number: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Fetch patent metadata from Espacenet.
    Uses Redis cache for performance.
    """
    from app.services.patent_provider import patent_provider
    from app.schemas.espacenet import EspacenetPatentMetadata
    
    metadata = await patent_provider.fetch_patent_metadata(patent_number)
    
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patent {patent_number} not found on Espacenet"
        )
    
    return metadata


@router.post("/import/espacenet", response_model=PatentResponse, status_code=status.HTTP_201_CREATED)
async def import_patent_from_espacenet(
    patent_number: str,
    project_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Import a patent from Espacenet into a project.
    Fetches metadata, creates patent record, and generates embedding.
    """
    from app.services.patent_provider import patent_provider
    
    # Fetch from Espacenet
    metadata = await patent_provider.fetch_patent_metadata(patent_number)
    
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patent {patent_number} not found on Espacenet"
        )
    
    # Create patent from Espacenet data
    patent_data = PatentCreate(
        title=metadata.title,
        description=metadata.abstract,
        content=f"{metadata.title}\n\n{metadata.abstract}",
        patent_number=metadata.patent_number,
        filing_date=metadata.filing_date,
        project_id=project_id
    )
    
    patent = await create_patent(db, patent_data, embedding=None)
    
    # Trigger async embedding generation
    generate_patent_embedding_task.delay(str(patent.id), patent.content)
    
    return patent
