"""
Service d'horodatage blockchain via Woleet API.
Preuve d'antériorité sur la blockchain Bitcoin.
"""

import logging
import hashlib
import httpx
from typing import Dict, Optional
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.blockchain_anchor import BlockchainAnchor

logger = logging.getLogger(__name__)


class BlockchainTimestampService:
    """
    Service d'ancrage blockchain avec Woleet.
    Génère des preuves d'antériorité horodatées.
    """
    
    def __init__(self):
        """Initialize blockchain service."""
        if not settings.WOLEET_API_KEY:
            logger.warning("Woleet API key not configured")
        else:
            logger.info("Blockchain timestamp service initialized")
    
    async def anchor_document(
        self,
        project_id: UUID,
        document_content: str,
        db: AsyncSession
    ) -> Dict:
        """
        Ancre un document sur la blockchain Bitcoin.
        
        Args:
            project_id: ID du projet
            document_content: Contenu du document à ancrer
            db: Database session
            
        Returns:
            Dict avec anchor_id, document_hash, status
        """
        logger.info(f"Anchoring document for project {project_id}")
        
        # Calculate SHA-256 hash
        doc_hash = hashlib.sha256(
            document_content.encode('utf-8')
        ).hexdigest()
        
        logger.info(f"Document hash: {doc_hash}")
        
        try:
            # Call Woleet API to create anchor
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.WOLEET_API_URL}/anchor",
                    headers={
                        "Authorization": f"Bearer {settings.WOLEET_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "hash": doc_hash,
                        "name": f"Patent Project {project_id}",
                        "metadata": {
                            "project_id": str(project_id),
                            "timestamp": datetime.utcnow().isoformat(),
                            "type": "patent_document"
                        }
                    }
                )
                response.raise_for_status()
                woleet_data = response.json()
            
            # Create anchor record
            anchor = BlockchainAnchor(
                id=uuid4(),
                project_id=project_id,
                document_hash=doc_hash,
                woleet_anchor_id=woleet_data['id'],
                status='pending',
                created_at=datetime.utcnow()
            )
            db.add(anchor)
            await db.commit()
            
            logger.info(
                f"Anchor created: {anchor.id}, "
                f"Woleet ID: {woleet_data['id']}"
            )
            
            return {
                'anchor_id': str(anchor.id),
                'document_hash': doc_hash,
                'woleet_id': woleet_data['id'],
                'status': 'pending',
                'message': 'Document anchored, waiting for blockchain confirmation'
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Woleet API error: {e}")
            raise Exception(f"Failed to anchor document: {str(e)}")
    
    async def verify_anchor(
        self,
        anchor_id: UUID,
        db: AsyncSession
    ) -> Dict:
        """
        Vérifie le statut d'un ancrage blockchain.
        
        Args:
            anchor_id: ID de l'ancrage
            db: Database session
            
        Returns:
            Dict avec status, tx_id, block_height, etc.
        """
        # Get anchor from database
        result = await db.execute(
            select(BlockchainAnchor).where(BlockchainAnchor.id == anchor_id)
        )
        anchor = result.scalar_one_or_none()
        
        if not anchor:
            raise ValueError(f"Anchor {anchor_id} not found")
        
        # Check Woleet for updates
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{settings.WOLEET_API_URL}/anchor/{anchor.woleet_anchor_id}",
                    headers={
                        "Authorization": f"Bearer {settings.WOLEET_API_KEY}"
                    }
                )
                response.raise_for_status()
                woleet_data = response.json()
            
            # Update if confirmed
            if woleet_data['status'] == 'confirmed' and anchor.status != 'confirmed':
                anchor.status = 'confirmed'
                anchor.tx_id = woleet_data.get('txId')
                anchor.block_height = woleet_data.get('blockHeight')
                anchor.confirmed_at = datetime.fromisoformat(
                    woleet_data['confirmedAt'].replace('Z', '+00:00')
                )
                await db.commit()
                
                logger.info(f"Anchor {anchor_id} confirmed on blockchain")
            
            return {
                'anchor_id': str(anchor.id),
                'status': anchor.status,
                'document_hash': anchor.document_hash,
                'tx_id': anchor.tx_id,
                'block_height': anchor.block_height,
                'confirmed_at': anchor.confirmed_at.isoformat() if anchor.confirmed_at else None,
                'proof_url': f"https://woleet.io/receipt/{anchor.woleet_anchor_id}",
                'blockchain_explorer': f"https://blockstream.info/tx/{anchor.tx_id}" if anchor.tx_id else None
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Woleet verification error: {e}")
            # Return cached data
            return {
                'anchor_id': str(anchor.id),
                'status': anchor.status,
                'document_hash': anchor.document_hash,
                'tx_id': anchor.tx_id,
                'block_height': anchor.block_height,
                'confirmed_at': anchor.confirmed_at.isoformat() if anchor.confirmed_at else None,
                'error': 'Unable to verify with Woleet API'
            }
    
    async def generate_proof_certificate(
        self,
        anchor_id: UUID,
        db: AsyncSession
    ) -> bytes:
        """
        Génère un certificat PDF de preuve d'antériorité.
        
        Args:
            anchor_id: ID de l'ancrage
            db: Database session
            
        Returns:
            PDF bytes
        """
        # Get anchor
        result = await db.execute(
            select(BlockchainAnchor).where(BlockchainAnchor.id == anchor_id)
        )
        anchor = result.scalar_one_or_none()
        
        if not anchor:
            raise ValueError(f"Anchor {anchor_id} not found")
        
        if anchor.status != 'confirmed':
            raise ValueError("Anchor must be confirmed to generate certificate")
        
        # Generate PDF (simplified version)
        # TODO: Use reportlab for professional PDF
        from io import BytesIO
        
        pdf_content = f"""
        CERTIFICAT DE PREUVE D'ANTÉRIORITÉ
        
        Projet: {anchor.project_id}
        Hash SHA-256: {anchor.document_hash}
        
        Transaction Bitcoin: {anchor.tx_id}
        Bloc: {anchor.block_height}
        Date de confirmation: {anchor.confirmed_at}
        
        Vérification: https://woleet.io/receipt/{anchor.woleet_anchor_id}
        
        Blockchain Explorer: https://blockstream.info/tx/{anchor.tx_id}
        """
        
        # Simple text-based PDF for now
        buffer = BytesIO()
        buffer.write(pdf_content.encode('utf-8'))
        buffer.seek(0)
        
        return buffer.getvalue()
    
    def calculate_hash(self, content: str) -> str:
        """Calcule le hash SHA-256 d'un contenu."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def verify_hash(self, content: str, expected_hash: str) -> bool:
        """Vérifie qu'un contenu correspond à un hash."""
        actual_hash = self.calculate_hash(content)
        return actual_hash == expected_hash


# Instance globale
blockchain_service = BlockchainTimestampService()
