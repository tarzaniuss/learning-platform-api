from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models.course import Course as CourseModel
from app.models.enrollment import Enrollment as EnrollmentModel
from app.models.lesson import Lesson as LessonModel
from app.models.lesson_completion import LessonCompletion as LessonCompletionModel
from app.schemas.enrollment import (
    EnrollmentCreate,
    EnrollmentRead,
    LessonCompletionCreate,
    LessonCompletionRead,
)

router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


@router.get("/my", response_model=List[EnrollmentRead])
async def get_my_enrollments(current_user: CurrentUser = None, db: DbSession = None):
    """Get all course enrollments for the current user"""
    stmt = select(EnrollmentModel).where(EnrollmentModel.user_id == current_user.id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=EnrollmentRead, status_code=status.HTTP_201_CREATED)
async def enroll_in_course(
    enrollment_data: EnrollmentCreate,
    current_user: CurrentUser = None,
    db: DbSession = None,
):
    """Enroll the current user in a course"""
    course_stmt = select(CourseModel).where(CourseModel.id == enrollment_data.course_id)
    course_result = await db.execute(course_stmt)
    course = course_result.scalar_one_or_none()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    if not course.is_published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Course is not published"
        )

    existing_stmt = select(EnrollmentModel).where(
        EnrollmentModel.user_id == current_user.id,
        EnrollmentModel.course_id == enrollment_data.course_id,
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already enrolled in this course",
        )

    enrollment = EnrollmentModel(
        user_id=current_user.id,
        course_id=enrollment_data.course_id,
        progress_percentage=0.0,
    )

    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)

    return enrollment


@router.post("/lessons/complete", response_model=LessonCompletionRead)
async def complete_lesson(
    completion_data: LessonCompletionCreate,
    current_user: CurrentUser = None,
    db: DbSession = None,
):
    """Mark a specific lesson as completed and update course progress"""
    lesson_stmt = select(LessonModel).where(LessonModel.id == completion_data.lesson_id)
    lesson_result = await db.execute(lesson_stmt)
    lesson = lesson_result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )

    enrollment_stmt = select(EnrollmentModel).where(
        EnrollmentModel.user_id == current_user.id,
        EnrollmentModel.course_id == lesson.course_id,
    )
    enrollment_result = await db.execute(enrollment_stmt)
    enrollment = enrollment_result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enrolled in this course",
        )

    existing_stmt = select(LessonCompletionModel).where(
        LessonCompletionModel.user_id == current_user.id,
        LessonCompletionModel.lesson_id == completion_data.lesson_id,
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Lesson already completed"
        )

    completion = LessonCompletionModel(
        user_id=current_user.id,
        lesson_id=completion_data.lesson_id,
        time_spent_minutes=completion_data.time_spent_minutes,
    )

    db.add(completion)

    total_lessons_stmt = (
        select(func.count())
        .select_from(LessonModel)
        .where(LessonModel.course_id == lesson.course_id)
    )
    total_lessons_result = await db.execute(total_lessons_stmt)
    total_lessons = total_lessons_result.scalar()

    completed_lessons_stmt = (
        select(func.count())
        .select_from(LessonCompletionModel)
        .join(LessonModel)
        .where(
            LessonCompletionModel.user_id == current_user.id,
            LessonModel.course_id == lesson.course_id,
        )
    )
    completed_lessons_result = await db.execute(completed_lessons_stmt)
    completed_lessons = completed_lessons_result.scalar() + 1

    enrollment.progress_percentage = (completed_lessons / total_lessons) * 100

    if enrollment.progress_percentage >= 100:
        enrollment.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(completion)

    return completion


@router.get("/course/{course_id}/progress")
async def get_course_progress(
    course_id: int,
    current_user: CurrentUser = None,
    db: DbSession = None,
):
    """Get detailed progress for a specific course"""
    enrollment_stmt = select(EnrollmentModel).where(
        EnrollmentModel.user_id == current_user.id,
        EnrollmentModel.course_id == course_id,
    )
    enrollment_result = await db.execute(enrollment_stmt)
    enrollment = enrollment_result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not enrolled in this course"
        )

    total_lessons_stmt = (
        select(func.count())
        .select_from(LessonModel)
        .where(LessonModel.course_id == course_id)
    )
    total_lessons_result = await db.execute(total_lessons_stmt)
    total_lessons = total_lessons_result.scalar()

    completed_lessons_stmt = (
        select(func.count())
        .select_from(LessonCompletionModel)
        .join(LessonModel)
        .where(
            LessonCompletionModel.user_id == current_user.id,
            LessonModel.course_id == course_id,
        )
    )
    completed_lessons_result = await db.execute(completed_lessons_stmt)
    completed_lessons = completed_lessons_result.scalar()

    return {
        "enrollment_id": enrollment.id,
        "progress_percentage": enrollment.progress_percentage,
        "completed_lessons": completed_lessons,
        "total_lessons": total_lessons,
        "is_completed": enrollment.completed_at is not None,
        "completed_at": enrollment.completed_at,
    }
