from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.patent import Patent
from app.schemas.patent import PatentCreate, PatentUpdate
from typing import Optional, List
from uuid import UUID


async def create_patent(db: AsyncSession, patent_data: PatentCreate, embedding: Optional[List[float]] = None) -> Patent:
    """
    Create a new patent entry.
    """
    patent = Patent(
        **patent_data.model_dump(),
        embedding=embedding
    )
    
    db.add(patent)
    await db.commit()
    await db.refresh(patent)
    
    return patent


async def get_patent(db: AsyncSession, patent_id: UUID) -> Optional[Patent]:
    """
    Get a patent by ID.
    """
    result = await db.execute(select(Patent).where(Patent.id == patent_id))
    return result.scalar_one_or_none()


async def update_patent(db: AsyncSession, patent_id: UUID, patent_data: PatentUpdate) -> Optional[Patent]:
    """
    Update a patent.
    """
    result = await db.execute(select(Patent).where(Patent.id == patent_id))
    patent = result.scalar_one_or_none()
    
    if not patent:
        return None
    
    # Update only provided fields
    update_data = patent_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patent, field, value)
    
    await db.commit()
    await db.refresh(patent)
    
    return patent


async def delete_patent(db: AsyncSession, patent_id: UUID) -> bool:
    """
    Delete a patent.
    """
    result = await db.execute(select(Patent).where(Patent.id == patent_id))
    patent = result.scalar_one_or_none()
    
    if not patent:
        return False
    
    await db.delete(patent)
    await db.commit()
    
    return True


async def get_patents_by_project(db: AsyncSession, project_id: UUID) -> List[Patent]:
    """
    Get all patents for a specific project.
    """
    result = await db.execute(
        select(Patent).where(Patent.project_id == project_id).order_by(Patent.created_at.desc())
    )
    return list(result.scalars().all())
