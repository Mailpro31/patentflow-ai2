from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class EspacenetPatentMetadata(BaseModel):
    """Metadata for a patent from Espacenet."""
    patent_number: str = Field(..., description="Patent number (e.g., EP1234567)")
    title: str = Field(..., description="Patent title")
    abstract: str = Field(..., description="Patent abstract/summary")
    filing_date: Optional[datetime] = Field(None, description="Filing date")
    publication_date: Optional[datetime] = Field(None, description="Publication date")
    applicants: List[str] = Field(default_factory=list, description="List of applicants")
    inventors: List[str] = Field(default_factory=list, description="List of inventors")
    ipc_classes: List[str] = Field(default_factory=list, description="IPC classification codes")
    
    model_config = {"from_attributes": True}


class EspacenetSearchRequest(BaseModel):
    """Request for searching patents on Espacenet."""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")


class EspacenetSearchResult(BaseModel):
    """Single result from Espacenet search."""
    patent_number: str
    title: str
    abstract: Optional[str] = None
    score: float = Field(default=1.0, description="Relevance score")


class EspacenetSearchResponse(BaseModel):
    """Response from Espacenet search."""
    query: str
    total_results: int
    results: List[EspacenetSearchResult]
    cached: bool = Field(default=False, description="Whether results were from cache")
