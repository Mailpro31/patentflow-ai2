from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from datetime import datetime
from uuid import uuid4
from app.database import Base


class Patent(Base):
    """Patent model for storing patent information and embeddings."""
    
    __tablename__ = "patents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    patent_number = Column(String, unique=True, index=True, nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    filing_date = Column(DateTime, nullable=True)
    
    # Vector embedding for similarity search (1536 dimensions for OpenAI embeddings)
    # Adjust dimensions based on your embedding model
    embedding = Column(Vector(384), nullable=True)  # 384 for all-MiniLM-L6-v2
    
    # Foreign Keys
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="patents")
    
    def __repr__(self):
        return f"<Patent {self.patent_number or self.title}>"
