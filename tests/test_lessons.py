"""
Tests for /api/v1/lessons
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, DifficultyLevel
from app.models.enrollment import Enrollment
from app.models.lesson import Lesson
from app.models.user import User

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def course(db_session: AsyncSession, instructor_user: User) -> Course:
    """Create a published course with an instructor."""
    obj = Course(
        title="Course with Lessons",
        instructor_id=instructor_user.id,
        difficulty_level=DifficultyLevel.BEGINNER,
        is_published=True,
    )
    db_session.add(obj)
    await db_session.commit()
    await db_session.refresh(obj)
    return obj


@pytest_asyncio.fixture
async def lesson(db_session: AsyncSession, course: Course) -> Lesson:
    """Create a lesson for the given course."""
    obj = Lesson(
        course_id=course.id,
        title="Lesson 1: Introduction",
        content="Lesson content",
        order_index=1,
    )
    db_session.add(obj)
    await db_session.commit()
    await db_session.refresh(obj)
    return obj


@pytest_asyncio.fixture
async def enrollment(
    db_session: AsyncSession, student_user: User, course: Course
) -> Enrollment:
    """Enroll a student in the course."""
    obj = Enrollment(
        user_id=student_user.id,
        course_id=course.id,
        progress_percentage=0.0,
    )
    db_session.add(obj)
    await db_session.commit()
    await db_session.refresh(obj)
    return obj


class TestGetCourseLessons:
    async def test_get_lessons_enrolled_student(
        self,
        student_client: AsyncClient,
        course: Course,
        lesson: Lesson,
        enrollment: Enrollment,
    ):
        """An enrolled student can see the lessons of the course."""
        response = await student_client.get(f"/api/v1/lessons/course/{course.id}")
        assert response.status_code == 200
        lessons = response.json()
        assert len(lessons) == 1
        assert lessons[0]["id"] == lesson.id
        assert "is_completed" in lessons[0]
        assert lessons[0]["is_completed"] is False

    async def test_get_lessons_nonexistent_course(self, student_client: AsyncClient):
        """Requesting lessons for a non-existent course should return 404."""
        response = await student_client.get("/api/v1/lessons/course/99999")
        assert response.status_code == 404


class TestGetLesson:
    async def test_get_existing_lesson(
        self,
        student_client: AsyncClient,
        lesson: Lesson,
        enrollment: Enrollment,
    ):
        """Successfully retrieve a specific lesson's details."""
        response = await student_client.get(f"/api/v1/lessons/{lesson.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == lesson.id
        assert data["title"] == lesson.title
        assert "is_completed" in data

    async def test_get_nonexistent_lesson(self, student_client: AsyncClient):
        """Requesting a non-existent lesson should return 404."""
        response = await student_client.get("/api/v1/lessons/99999")
        assert response.status_code == 404


class TestCreateLesson:
    async def test_instructor_can_create_lesson(
        self, instructor_client: AsyncClient, course: Course
    ):
        """The instructor can add a lesson to their own course."""
        response = await instructor_client.post(
            "/api/v1/lessons/",
            json={
                "course_id": course.id,
                "title": "New Lesson",
                "content": "Content here",
                "order_index": 1,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Lesson"
        assert data["course_id"] == course.id

    async def test_student_cannot_create_lesson(
        self, student_client: AsyncClient, course: Course
    ):
        """Students are forbidden from creating lessons (403)."""
        response = await student_client.post(
            "/api/v1/lessons/",
            json={
                "course_id": course.id,
                "title": "My Lesson",
                "order_index": 1,
            },
        )
        assert response.status_code == 403

    async def test_create_lesson_nonexistent_course(
        self, instructor_client: AsyncClient
    ):
        """Creating a lesson for a non-existent course should return 404."""
        response = await instructor_client.post(
            "/api/v1/lessons/",
            json={
                "course_id": 99999,
                "title": "Ghost Lesson",
                "order_index": 1,
            },
        )
        assert response.status_code == 404


class TestMarkLessonComplete:
    async def test_mark_lesson_complete(
        self,
        student_client: AsyncClient,
        lesson: Lesson,
        enrollment: Enrollment,
    ):
        """A student can mark a lesson as completed."""
        response = await student_client.post(f"/api/v1/lessons/{lesson.id}/complete")
        assert response.status_code == 201
        data = response.json()
        assert "completed_at" in data
        assert data["message"] == "Lesson marked as completed"

    async def test_mark_lesson_complete_twice(
        self,
        student_client: AsyncClient,
        lesson: Lesson,
        enrollment: Enrollment,
    ):
        """Marking an already completed lesson as complete should return 400."""
        await student_client.post(f"/api/v1/lessons/{lesson.id}/complete")
        response = await student_client.post(f"/api/v1/lessons/{lesson.id}/complete")
        assert response.status_code == 400
        assert "already completed" in response.json()["detail"]


class TestDeleteLesson:
    async def test_instructor_can_delete_lesson(
        self, instructor_client: AsyncClient, lesson: Lesson
    ):
        """The instructor can delete a lesson from their course."""
        response = await instructor_client.delete(f"/api/v1/lessons/{lesson.id}")
        assert response.status_code == 204

    async def test_delete_nonexistent_lesson(self, instructor_client: AsyncClient):
        """Deleting a non-existent lesson should return 404."""
        response = await instructor_client.delete("/api/v1/lessons/99999")
        assert response.status_code == 404
