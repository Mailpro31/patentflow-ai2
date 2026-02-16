"""
Modèle Payment pour enregistrer les paiements Stripe.
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class Payment(Base):
    """Enregistrement de paiement Stripe."""
    
    __tablename__ = "payments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Stripe IDs
    stripe_session_id = Column(String, unique=True, nullable=False)
    stripe_payment_intent_id = Column(String, unique=True)
    
    # Payment details
    amount = Column(Integer, nullable=False)  # in cents
    currency = Column(String(3), default="eur")
    status = Column(String(20), nullable=False)  # succeeded, failed, pending
    
    # Payment method
    payment_method = Column(String(50))  # card, sepa_debit, etc.
    receipt_url = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="payments")
    user = relationship("User", back_populates="payments")
    
    def __repr__(self):
        return f"<Payment {self.id} - {self.amount/100}€ - {self.status}>"
