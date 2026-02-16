"""
Pydantic schemas pour paiements, blockchain, et annuités.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date


# ============ Payment Schemas ============

class CheckoutRequest(BaseModel):
    """Requête de création de checkout Stripe."""
    
    project_id: UUID
    patent_type: str = Field(
        ...,
        pattern="^(provisional|full|pct)$",
        description="Type de brevet"
    )
    success_url: str = Field(..., description="URL de redirection succès")
    cancel_url: str = Field(..., description="URL d'annulation")


class CheckoutResponse(BaseModel):
    """Réponse de création de checkout."""
    
    session_id: str
    url: str
    amount: int
    currency: str
    expires_at: int


class PaymentStatusResponse(BaseModel):
    """Statut d'un paiement."""
    
    status: str
    amount: Optional[int] = None
    currency: Optional[str] = None
    payment_date: Optional[datetime] = None
    receipt_url: Optional[str] = None
    payment_method: Optional[str] = None


class PricingInfo(BaseModel):
    """Information de tarification."""
    
    amount: int
    amount_eur: float
    name: str
    description: str


class PricingResponse(BaseModel):
    """Tous les tarifs disponibles."""
    
    provisional: PricingInfo
    full: PricingInfo
    pct: PricingInfo


# ============ Blockchain Schemas ============

class AnchorRequest(BaseModel):
    """Requête d'ancrage blockchain."""
    
    project_id: UUID
    document_content: str = Field(
        ...,
        description="Contenu du document à ancrer"
    )


class AnchorResponse(BaseModel):
    """Réponse d'ancrage."""
    
    anchor_id: str
    document_hash: str
    woleet_id: str
    status: str
    message: str


class AnchorVerificationResponse(BaseModel):
    """Vérification d'un ancrage."""
    
    anchor_id: str
    status: str
    document_hash: str
    tx_id: Optional[str] = None
    block_height: Optional[int] = None
    confirmed_at: Optional[str] = None
    proof_url: str
    blockchain_explorer: Optional[str] = None
    error: Optional[str] = None


# ============ INPI Annuity Schemas ============

class AnnuityPayment(BaseModel):
    """Détails d'un paiement d'annuité."""
    
    year: int
    due_date: str
    amount: int
    late_fee: int
    total_with_late_fee: int
    grace_deadline: Optional[str] = None
    status: str


class AnnuityScheduleResponse(BaseModel):
    """Calendrier complet des annuités."""
    
    project_id: UUID
    filing_date: date
    schedule: List[AnnuityPayment]


class AnnuityCumulativeCost(BaseModel):
    """Coût cumulatif par année."""
    
    year: int
    annual_cost: int
    cumulative_cost: int


class AnnuityCostsResponse(BaseModel):
    """Coûts totaux sur N années."""
    
    total_nominal: int
    total_npv: float
    years: int
    discount_rate: float
    cumulative: List[AnnuityCumulativeCost]
    average_per_year: float
    min_annual: int
    max_annual: int


class UpcomingPaymentsResponse(BaseModel):
    """Paiements à venir."""
    
    upcoming_payments: List[AnnuityPayment]


class AnnuityRate(BaseModel):
    """Tarif d'une année."""
    
    year: int
    amount: int


class AnnuityRatesResponse(BaseModel):
    """Tableau complet des tarifs."""
    
    rates: List[AnnuityRate]
