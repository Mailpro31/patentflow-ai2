from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from uuid import UUID
from typing import Optional, List
from app.utils.validators import sanitize_string


class PatentBase(BaseModel):
    """Base schema for Patent."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    content: str = Field(..., min_length=1)
    patent_number: Optional[str] = Field(None, max_length=100)
    filing_date: Optional[datetime] = None
    
    @field_validator('title', 'description', 'content', 'patent_number')
    @classmethod
    def sanitize_fields(cls, v):
        if v is not None and isinstance(v, str):
            return sanitize_string(v)
        return v


class PatentCreate(PatentBase):
    """Schema for creating a new patent."""
    project_id: UUID


class PatentUpdate(BaseModel):
    """Schema for updating patent information."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    content: Optional[str] = Field(None, min_length=1)
    patent_number: Optional[str] = Field(None, max_length=100)
    filing_date: Optional[datetime] = None
    
    @field_validator('title', 'description', 'content', 'patent_number')
    @classmethod
    def sanitize_fields(cls, v):
        if v is not None and isinstance(v, str):
            return sanitize_string(v)
        return v


class PatentResponse(PatentBase):
    """Schema for patent response."""
    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class PatentSearchQuery(BaseModel):
    """Schema for patent similarity search query."""
    query_text: str = Field(..., min_length=1, max_length=1000)
    project_id: Optional[UUID] = None
    limit: int = Field(default=10, ge=1, le=100)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class PatentSearchResult(PatentResponse):
    """Schema for patent search result with similarity score."""
    similarity_score: float
