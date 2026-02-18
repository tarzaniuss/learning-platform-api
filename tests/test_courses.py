"""
Tests for /api/v1/courses
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, DifficultyLevel
from app.models.user import User

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def published_course(db_session: AsyncSession, instructor_user: User) -> Course:
    """Creates a published course for testing."""
    course = Course(
        title="Python for Beginners",
        description="Basic Python course",
        instructor_id=instructor_user.id,
        difficulty_level=DifficultyLevel.BEGINNER,
        is_published=True,
    )
    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)
    return course


@pytest_asyncio.fixture
async def unpublished_course(db_session: AsyncSession, instructor_user: User) -> Course:
    """Creates an unpublished course for testing."""
    course = Course(
        title="Secret Course",
        description="Not ready yet",
        instructor_id=instructor_user.id,
        difficulty_level=DifficultyLevel.INTERMEDIATE,
        is_published=False,
    )
    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)
    return course


class TestGetCourses:
    async def test_get_published_courses(
        self,
        student_client: AsyncClient,
        published_course: Course,
        unpublished_course: Course,
    ):
        """By default, returns only published courses."""
        response = await student_client.get("/api/v1/courses/")
        assert response.status_code == 200
        courses = response.json()
        ids = [c["id"] for c in courses]
        assert published_course.id in ids
        assert unpublished_course.id not in ids

    async def test_get_all_courses_with_flag(
        self, student_client: AsyncClient, unpublished_course: Course
    ):
        """Returns all courses when is_published=false parameter is provided."""
        response = await student_client.get("/api/v1/courses/?is_published=false")
        assert response.status_code == 200
        ids = [c["id"] for c in response.json()]
        assert unpublished_course.id in ids

    async def test_courses_have_is_enrolled_field(
        self, student_client: AsyncClient, published_course: Course
    ):
        """Ensures each course object contains the is_enrolled field."""
        response = await student_client.get("/api/v1/courses/")
        assert response.status_code == 200
        for course in response.json():
            assert "is_enrolled" in course


class TestGetCourse:
    async def test_get_existing_course(
        self, student_client: AsyncClient, published_course: Course
    ):
        """Retrieving an existing course by ID."""
        response = await student_client.get(f"/api/v1/courses/{published_course.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == published_course.id
        assert data["title"] == published_course.title

    async def test_get_nonexistent_course(self, student_client: AsyncClient):
        """Requesting a non-existent course returns 404."""
        response = await student_client.get("/api/v1/courses/99999")
        assert response.status_code == 404


class TestCreateCourse:
    async def test_instructor_can_create_course(self, instructor_client: AsyncClient):
        """An instructor is authorized to create a course."""
        response = await instructor_client.post(
            "/api/v1/courses/",
            json={
                "title": "New Course",
                "description": "Course description",
                "difficulty_level": "beginner",
                "is_published": False,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Course"
        assert "id" in data

    async def test_student_cannot_create_course(self, student_client: AsyncClient):
        """A student is not authorized to create a course — returns 403."""
        response = await student_client.post(
            "/api/v1/courses/",
            json={
                "title": "Course by Student",
                "difficulty_level": "beginner",
                "is_published": False,
            },
        )
        assert response.status_code == 403

    async def test_create_course_missing_title(self, instructor_client: AsyncClient):
        """Creating a course without a title returns 422 (Unprocessable Entity)."""
        response = await instructor_client.post(
            "/api/v1/courses/",
            json={"difficulty_level": "beginner", "is_published": False},
        )
        assert response.status_code == 422


class TestUpdateCourse:
    async def test_instructor_can_update_own_course(
        self, instructor_client: AsyncClient, published_course: Course
    ):
        """An instructor can update a course they own."""
        response = await instructor_client.put(
            f"/api/v1/courses/{published_course.id}",
            json={"title": "Updated Title"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    async def test_cannot_update_others_course(
        self,
        db_session: AsyncSession,
        student_client: AsyncClient,  # Using student as a "different" user
        published_course: Course,
    ):
        """Users cannot update courses owned by others — returns 403."""
        # student_client is authorized as a student, not the course owner
        response = await student_client.put(
            f"/api/v1/courses/{published_course.id}",
            json={"title": "Hacked Course"},
        )
        assert response.status_code == 403

    async def test_update_nonexistent_course(self, instructor_client: AsyncClient):
        """Updating a non-existent course returns 404."""
        response = await instructor_client.put(
            "/api/v1/courses/99999",
            json={"title": "Does Not Exist"},
        )
        assert response.status_code == 404


class TestDeleteCourse:
    async def test_instructor_can_delete_own_course(
        self, instructor_client: AsyncClient, published_course: Course
    ):
        """An instructor can delete a course they own."""
        response = await instructor_client.delete(
            f"/api/v1/courses/{published_course.id}"
        )
        assert response.status_code == 204

    async def test_delete_nonexistent_course(self, instructor_client: AsyncClient):
        """Deleting a non-existent course returns 404."""
        response = await instructor_client.delete("/api/v1/courses/99999")
        assert response.status_code == 404
