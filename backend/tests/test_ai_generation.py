import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from app.models.user import User
from app.utils.security import create_access_token

@pytest.fixture
async def authenticated_client(client, db_session):
    user = User(email="user@ai.com", full_name="AI User", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    token = create_access_token(data={"sub": str(user.id)})
    client.headers = {"Authorization": f"Bearer {token}"}
    return client

@pytest.mark.asyncio
async def test_generate_patent_document(authenticated_client):
    """Test full patent generation endpoint."""
    mock_response = {
        "title": "AI Coffee Maker",
        "abstract": "A smart coffee maker...",
        "description": "Detailed description...",
        "claims": ["Claim 1", "Claim 2"],
        "novelty_score": 85,
        "inventive_step_score": 90
    }
    
    with patch("app.services.ai_writer_service.generate_patent_draft", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_response
        
        payload = {
            "idea_description": "Smart coffee maker with AI",
            "mode": "LARGE",
            "inventor_name": "Test Inventor"
        }
        
        response = await authenticated_client.post("/api/ai/generate", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "AI Coffee Maker"
        assert "claims" in data
