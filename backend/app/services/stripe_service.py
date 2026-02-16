"""
Service de gestion des paiements Stripe.
Checkout Sessions, Webhooks, et activation automatique des projets.
"""

import logging
import stripe
from typing import Dict, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.config import settings
from app.models.project import Project
from app.models.payment import Payment

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_API_KEY


# Pricing tiers (in cents)
PRICING_TIERS = {
    "provisional": {
        "amount": 29900,  # 299€
        "name": "Brevet Provisoire",
        "description": "Dépôt provisoire de brevet avec PatentFlowIA"
    },
    "full": {
        "amount": 79900,  # 799€
        "name": "Brevet Complet",
        "description": "Dépôt complet de brevet avec génération IA"
    },
    "pct": {
        "amount": 149900,  # 1499€
        "name": "Brevet PCT International",
        "description": "Dépôt PCT avec protection internationale"
    }
}


class StripePaymentService:
    """
    Service de paiement Stripe avec checkout et webhooks.
    """
    
    def __init__(self):
        """Initialize Stripe service."""
        if not settings.STRIPE_API_KEY:
            logger.warning("Stripe API key not configured")
        else:
            logger.info("Stripe service initialized")
    
    async def create_checkout_session(
        self,
        project_id: UUID,
        user_id: UUID,
        user_email: str,
        patent_type: str,
        success_url: str,
        cancel_url: str
    ) -> Dict:
        """
        Crée une session Stripe Checkout.
        
        Args:
            project_id: ID du projet
            user_id: ID de l'utilisateur
            user_email: Email de l'utilisateur
            patent_type: Type de brevet (provisional, full, pct)
            success_url: URL de redirection succès
            cancel_url: URL de redirection annulation
            
        Returns:
            Dict avec session_id, url, amount
        """
        if patent_type not in PRICING_TIERS:
            raise ValueError(f"Invalid patent type: {patent_type}")
        
        pricing = PRICING_TIERS[patent_type]
        
        try:
            # Create Stripe Checkout Session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'eur',
                        'product_data': {
                            'name': pricing['name'],
                            'description': pricing['description'],
                            'metadata': {
                                'project_id': str(project_id),
                                'patent_type': patent_type
                            }
                        },
                        'unit_amount': pricing['amount'],
                    },
                    'quantity': 1,
                    'tax_behavior': 'exclusive'  # Stripe Tax will add VAT
                }],
                mode='payment',
                success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url,
                metadata={
                    'project_id': str(project_id),
                    'user_id': str(user_id),
                    'patent_type': patent_type
                },
                customer_email=user_email,
                automatic_tax={'enabled': settings.STRIPE_TAX_ENABLED},
                expires_at=int(datetime.utcnow().timestamp()) + 1800  # 30 minutes
            )
            
            logger.info(
                f"Created Stripe checkout session {session.id} "
                f"for project {project_id}"
            )
            
            return {
                'session_id': session.id,
                'url': session.url,
                'amount': pricing['amount'],
                'currency': 'eur',
                'expires_at': session.expires_at
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def handle_webhook(
        self,
        payload: bytes,
        signature: str,
        db: AsyncSession
    ) -> Dict:
        """
        Traite les événements webhook Stripe.
        
        Args:
            payload: Raw webhook payload
            signature: Stripe signature header
            db: Database session
            
        Returns:
            Status dict
        """
        # Verify webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            logger.error("Invalid webhook payload")
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid webhook signature")
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Handle different event types
        event_type = event['type']
        logger.info(f"Processing webhook event: {event_type}")
        
        if event_type == 'checkout.session.completed':
            session = event['data']['object']
            await self._handle_checkout_completed(session, db)
        
        elif event_type == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            await self._handle_payment_succeeded(payment_intent, db)
        
        elif event_type == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            await self._handle_payment_failed(payment_intent, db)
        
        else:
            logger.info(f"Unhandled event type: {event_type}")
        
        return {'status': 'success', 'event_type': event_type}
    
    async def _handle_checkout_completed(
        self,
        session: Dict,
        db: AsyncSession
    ) -> None:
        """
        Traite un checkout complété avec succès.
        Active le projet et crée l'enregistrement de paiement.
        """
        project_id = UUID(session['metadata']['project_id'])
        user_id = UUID(session['metadata']['user_id'])
        patent_type = session['metadata']['patent_type']
        
        logger.info(f"Checkout completed for project {project_id}")
        
        # Get project
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            logger.error(f"Project {project_id} not found")
            return
        
        # Update project status
        project.payment_status = 'paid'
        project.payment_date = datetime.utcnow()
        project.stripe_session_id = session['id']
        project.amount_paid = session.get('amount_total', 0)
        project.currency = session.get('currency', 'eur')
        
        # Create payment record
        payment = Payment(
            project_id=project_id,
            user_id=user_id,
            stripe_session_id=session['id'],
            stripe_payment_intent_id=session.get('payment_intent', ''),
            amount=session.get('amount_total', 0),
            currency=session.get('currency', 'eur'),
            status='succeeded',
            payment_method=session.get('payment_method_types', ['card'])[0],
            receipt_url=session.get('receipt_url'),
            created_at=datetime.utcnow()
        )
        db.add(payment)
        
        await db.commit()
        
        logger.info(f"Project {project_id} activated after payment")
        
        # TODO: Send confirmation email
        # TODO: Trigger blockchain anchoring (Celery task)
    
    async def _handle_payment_succeeded(
        self,
        payment_intent: Dict,
        db: AsyncSession
    ) -> None:
        """Confirme le paiement réussi."""
        logger.info(f"Payment intent succeeded: {payment_intent['id']}")
        
        # Update payment record if exists
        result = await db.execute(
            select(Payment).where(
                Payment.stripe_payment_intent_id == payment_intent['id']
            )
        )
        payment = result.scalar_one_or_none()
        
        if payment:
            payment.status = 'succeeded'
            payment.updated_at = datetime.utcnow()
            await db.commit()
    
    async def _handle_payment_failed(
        self,
        payment_intent: Dict,
        db: AsyncSession
    ) -> None:
        """Traite un paiement échoué."""
        logger.warning(f"Payment intent failed: {payment_intent['id']}")
        
        # Update payment record
        result = await db.execute(
            select(Payment).where(
                Payment.stripe_payment_intent_id == payment_intent['id']
            )
        )
        payment = result.scalar_one_or_none()
        
        if payment:
            payment.status = 'failed'
            payment.updated_at = datetime.utcnow()
            await db.commit()
        
        # TODO: Send failure notification email
    
    async def get_payment_status(
        self,
        project_id: UUID,
        db: AsyncSession
    ) -> Optional[Dict]:
        """
        Récupère le statut de paiement d'un projet.
        """
        result = await db.execute(
            select(Payment).where(Payment.project_id == project_id)
        )
        payment = result.scalar_one_or_none()
        
        if not payment:
            return None
        
        return {
            'status': payment.status,
            'amount': payment.amount,
            'currency': payment.currency,
            'payment_date': payment.created_at,
            'receipt_url': payment.receipt_url,
            'payment_method': payment.payment_method
        }
    
    def get_pricing_info(self) -> Dict:
        """Retourne les informations de tarification."""
        return {
            tier: {
                'amount': info['amount'],
                'amount_eur': info['amount'] / 100,
                'name': info['name'],
                'description': info['description']
            }
            for tier, info in PRICING_TIERS.items()
        }


# Instance globale
stripe_service = StripePaymentService()
