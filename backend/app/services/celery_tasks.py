from celery import Celery
from app.config import settings
from app.services.vector_service import generate_embedding
import logging


# Initialize Celery
celery_app = Celery(
    "patentflow",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

logger = logging.getLogger(__name__)


@celery_app.task(name="generate_patent_embedding")
def generate_patent_embedding_task(patent_id: str, content: str):
    """
    Async task to generate and store patent embedding.
    """
    try:
        # This is a sync task, but we can use asyncio.run for async functions
        import asyncio
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.database import AsyncSessionLocal
        from app.models.patent import Patent
        from sqlalchemy import select
        from uuid import UUID
        
        async def update_embedding():
            async with AsyncSessionLocal() as db:
                # Generate embedding
                embedding = await generate_embedding(content)
                
                # Update patent with embedding
                result = await db.execute(select(Patent).where(Patent.id == UUID(patent_id)))
                patent = result.scalar_one_or_none()
                
                if patent:
                    patent.embedding = embedding
                    await db.commit()
                    logger.info(f"Generated embedding for patent {patent_id}")
                else:
                    logger.error(f"Patent {patent_id} not found")
        
        asyncio.run(update_embedding())
        return {"status": "success", "patent_id": patent_id}
        
    except Exception as e:
        logger.error(f"Failed to generate embedding for patent {patent_id}: {e}")
        return {"status": "error", "patent_id": patent_id, "error": str(e)}


@celery_app.task(name="send_email")
def send_email_task(to_email: str, subject: str, body: str):
    """
    Async task to send email notifications.
    """
    try:
        # Implement email sending logic here
        # For example, using SMTP or a service like SendGrid
        logger.info(f"Sending email to {to_email}: {subject}")
        
        # Placeholder implementation
        return {"status": "success", "to_email": to_email}
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return {"status": "error", "to_email": to_email, "error": str(e)}
