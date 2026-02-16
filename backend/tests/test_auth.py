import pytest
from httpx import AsyncClient
from app.models.user import User
from app.utils.security import create_access_token

@pytest.mark.asyncio
async def test_magic_link_request(client: AsyncClient):
    """Test requesting a magic link."""
    response = await client.post("/api/auth/magic-link", json={"email": "test@example.com"})
    assert response.status_code == 200
    assert response.json()["message"] == "Magic link sent"

@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient):
    """Test accessing protected route without token."""
    response = await client.get("/api/users/me")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_current_user_authorized(client: AsyncClient, db_session):
    """Test accessing protected route with valid token."""
    # Create test user
    user = User(
        email="test@example.com",
        full_name="Test User",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    # Create token
    token = create_access_token(data={"sub": str(user.id)})
    
    # Make request with token
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/users/me", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"
