"""
Tests for /api/v1/enrollments
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, DifficultyLevel
from app.models.enrollment import Enrollment
from app.models.user import User

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def published_course(db_session: AsyncSession, instructor_user: User) -> Course:
    """Create and return a published course."""
    course = Course(
        title="Enrollment Test Course",
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
    """Create and return an unpublished course."""
    course = Course(
        title="Unpublished Course",
        instructor_id=instructor_user.id,
        difficulty_level=DifficultyLevel.BEGINNER,
        is_published=False,
    )
    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)
    return course


@pytest_asyncio.fixture
async def existing_enrollment(
    db_session: AsyncSession, student_user: User, published_course: Course
) -> Enrollment:
    """Create an enrollment record: student is already enrolled in the course."""
    enrollment = Enrollment(
        user_id=student_user.id,
        course_id=published_course.id,
        progress_percentage=0.0,
    )
    db_session.add(enrollment)
    await db_session.commit()
    await db_session.refresh(enrollment)
    return enrollment


class TestGetMyEnrollments:
    async def test_get_empty_enrollments(self, student_client: AsyncClient):
        """Student with no enrollments receives an empty list."""
        response = await student_client.get("/api/v1/enrollments/my")
        assert response.status_code == 200
        assert response.json() == []

    async def test_get_enrollments_with_data(
        self,
        student_client: AsyncClient,
        existing_enrollment: Enrollment,
    ):
        """Student can see their active enrollments."""
        response = await student_client.get("/api/v1/enrollments/my")
        assert response.status_code == 200
        enrollments = response.json()
        assert len(enrollments) == 1
        assert enrollments[0]["id"] == existing_enrollment.id


class TestEnrollInCourse:
    async def test_enroll_success(
        self, student_client: AsyncClient, published_course: Course
    ):
        """Successfully enroll in a published course."""
        response = await student_client.post(
            "/api/v1/enrollments/",
            json={"course_id": published_course.id},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["course_id"] == published_course.id
        assert data["progress_percentage"] == 0.0

    async def test_enroll_unpublished_course(
        self, student_client: AsyncClient, unpublished_course: Course
    ):
        """Enrolling in an unpublished course should return 400."""
        response = await student_client.post(
            "/api/v1/enrollments/",
            json={"course_id": unpublished_course.id},
        )
        assert response.status_code == 400
        assert "not published" in response.json()["detail"]

    async def test_enroll_nonexistent_course(self, student_client: AsyncClient):
        """Enrolling in a non-existent course should return 404."""
        response = await student_client.post(
            "/api/v1/enrollments/",
            json={"course_id": 99999},
        )
        assert response.status_code == 404

    async def test_enroll_twice(
        self,
        student_client: AsyncClient,
        published_course: Course,
        existing_enrollment: Enrollment,
    ):
        """Re-enrolling in the same course should return 400."""
        response = await student_client.post(
            "/api/v1/enrollments/",
            json={"course_id": published_course.id},
        )
        assert response.status_code == 400
        assert "Already enrolled" in response.json()["detail"]


class TestGetCourseProgress:
    async def test_get_progress_enrolled(
        self,
        student_client: AsyncClient,
        published_course: Course,
        existing_enrollment: Enrollment,
    ):
        """An enrolled student sees their current progress."""
        response = await student_client.get(
            f"/api/v1/enrollments/course/{published_course.id}/progress"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["progress_percentage"] == 0.0
        assert data["is_completed"] is False

    async def test_get_progress_not_enrolled(
        self, student_client: AsyncClient, published_course: Course
    ):
        """A student not enrolled in the course receives 404."""
        response = await student_client.get(
            f"/api/v1/enrollments/course/{published_course.id}/progress"
        )
        assert response.status_code == 404
