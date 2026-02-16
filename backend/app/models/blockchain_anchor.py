"""
Modèle BlockchainAnchor pour horodatage blockchain.
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class BlockchainAnchor(Base):
    """Ancrage blockchain pour preuve d'antériorité."""
    
    __tablename__ = "blockchain_anchors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    
    # Document hash
    document_hash = Column(String(64), nullable=False)  # SHA-256
    
    # Woleet API
    woleet_anchor_id = Column(String, unique=True, nullable=False)
    
    # Blockchain confirmation
    status = Column(String(20), nullable=False)  # pending, confirmed, failed
    tx_id = Column(String, nullable=True)  # Bitcoin transaction ID
    block_height = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="blockchain_anchors")
    
    def __repr__(self):
        return f"<BlockchainAnchor {self.id} - {self.status}>"
