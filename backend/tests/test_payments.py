import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from app.models.user import User
from app.utils.security import create_access_token

@pytest.fixture
async def authenticated_client(client, db_session):
    user = User(email="test@example.com", full_name="Test User", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    token = create_access_token(data={"sub": str(user.id)})
    # Need to update headers properly for each request or recreate client
    # For simplicity in this test file context, we might need a better fixture setup
    # But let's assume client fixture is per-function or used directly
    return client, token

@pytest.mark.asyncio
async def test_create_checkout_session(client, db_session):
    # Setup auth
    user = User(email="payer@example.com", full_name="Payer User", is_active=True)
    db_session.add(user)
    await db_session.commit()
    token = create_access_token(data={"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    mock_checkout_session = {
        "id": "cs_test_123",
        "url": "https://checkout.stripe.com/pay/cs_test_123"
    }

    with patch("stripe.checkout.Session.create", return_value=mock_checkout_session) as mock_create:
        payload = {"price_id": "price_fake_123"}
        response = await client.post("/api/payments/create-checkout", json=payload, headers=headers)
        
        # Depending on implementation, it might redirect or return URL
        # Assuming JSON return for SPA
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "https://checkout.stripe.com/pay/cs_test_123"
