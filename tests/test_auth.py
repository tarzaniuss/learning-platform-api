"""
Tests for /api/v1/auth
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        """Successful registration of a new user."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@test.com",
                "password": "securepassword",
                "full_name": "New User",
                "role": "student",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["full_name"] == "New User"
        assert data["role"] == "student"
        assert "id" in data
        assert "password" not in data
        assert "hashed_password" not in data

    async def test_register_duplicate_email(self, client: AsyncClient, student_user):
        """Registration with an existing email returns 400."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": student_user.email,
                "password": "password123",
                "full_name": "Another User",
                "role": "student",
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    async def test_register_invalid_email(self, client: AsyncClient):
        """Registration with an invalid email format returns 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "password123",
                "full_name": "User",
                "role": "student",
            },
        )
        assert response.status_code == 422

    async def test_register_instructor_role(self, client: AsyncClient):
        """Registration with an instructor role."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "instructor_new@test.com",
                "password": "password123",
                "full_name": "New Instructor",
                "role": "instructor",
            },
        )
        assert response.status_code == 201
        assert response.json()["role"] == "instructor"


class TestLogin:
    async def test_login_success(self, client: AsyncClient, student_user):
        """Successful login returns a JWT token."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": student_user.email, "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, student_user):
        """Invalid password returns 401."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": student_user.email, "password": "wrongpassword"},
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Login with a non-existent email returns 401."""
        # Note: Depending on your security policy, some prefer 404,
        # but 401 is standard for auth failures.
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@test.com", "password": "password123"},
        )
        assert response.status_code == 401


class TestGetMe:
    async def test_get_me_authenticated(
        self, student_client: AsyncClient, student_user
    ):
        """Authenticated user retrieves their own profile."""
        response = await student_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == student_user.email
        assert data["full_name"] == student_user.full_name

    async def test_get_me_unauthorized(self, client: AsyncClient):
        """Unauthorized request returns 401/403 (HTTPBearer without token)."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code in (401, 403)

    async def test_get_me_with_token(
        self, client: AsyncClient, student_user, student_token: str
    ):
        """Request using a real JWT token in the Authorization header."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == student_user.email
