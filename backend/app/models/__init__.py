# Import all models here for Alembic to detect them
from app.models.user import User
from app.models.project import Project
from app.models.patent import Patent
from app.models.payment import Payment
from app.models.blockchain_anchor import BlockchainAnchor
from app.models.generation_mode import GenerationMode

__all__ = [
    "User", 
    "Project", 
    "Patent", 
    "Payment", 
    "BlockchainAnchor", 
    "GenerationMode"
]
