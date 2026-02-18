from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentInstructor, CurrentUser, DbSession
from app.models.course import Course as CourseModel
from app.models.enrollment import Enrollment as EnrollmentModel
from app.models.lesson import Lesson as LessonModel
from app.models.lesson_completion import LessonCompletion as LessonCompletionModel
from app.schemas.lesson import (
    LessonCreate,
    LessonRead,
    LessonUpdate,
    LessonWithCompletionRead,
)

router = APIRouter(prefix="/lessons", tags=["Lessons"])


@router.get("/course/{course_id}", response_model=List[LessonWithCompletionRead])
async def get_course_lessons(
    course_id: int,
    current_user: CurrentUser = None,
    db: DbSession = None,
):
    """Get a list of lessons for a specific course with completion status"""
    course_stmt = select(CourseModel).where(CourseModel.id == course_id)
    course_result = await db.execute(course_stmt)
    course = course_result.scalar_one_or_none()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    lessons_stmt = (
        select(LessonModel)
        .where(LessonModel.course_id == course_id)
        .order_by(LessonModel.order_index)
    )
    lessons_result = await db.execute(lessons_stmt)
    lessons = lessons_result.scalars().all()

    enrollment_stmt = select(EnrollmentModel).where(
        EnrollmentModel.user_id == current_user.id,
        EnrollmentModel.course_id == course_id,
    )
    enrollment_result = await db.execute(enrollment_stmt)
    is_enrolled = enrollment_result.scalar_one_or_none() is not None

    completed_ids = set()
    if is_enrolled and lessons:
        lesson_ids = [lesson.id for lesson in lessons]
        completions_stmt = select(LessonCompletionModel.lesson_id).where(
            LessonCompletionModel.user_id == current_user.id,
            LessonCompletionModel.lesson_id.in_(lesson_ids),
        )
        completions_result = await db.execute(completions_stmt)
        completed_ids = {lesson_id for lesson_id in completions_result.scalars().all()}

    return [
        LessonWithCompletionRead(
            **{c.name: getattr(lesson, c.name) for c in lesson.__table__.columns},
            is_completed=lesson.id in completed_ids,
        )
        for lesson in lessons
    ]


@router.get("/{lesson_id}", response_model=LessonWithCompletionRead)
async def get_lesson(
    lesson_id: int,
    current_user: CurrentUser = None,
    db: DbSession = None,
):
    """Get lesson details with completion flag"""
    lesson_stmt = select(LessonModel).where(LessonModel.id == lesson_id)
    lesson_result = await db.execute(lesson_stmt)
    lesson = lesson_result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )

    completion_stmt = select(LessonCompletionModel).where(
        LessonCompletionModel.user_id == current_user.id,
        LessonCompletionModel.lesson_id == lesson_id,
    )
    completion_result = await db.execute(completion_stmt)
    is_completed = completion_result.scalar_one_or_none() is not None

    return LessonWithCompletionRead(
        **{c.name: getattr(lesson, c.name) for c in lesson.__table__.columns},
        is_completed=is_completed,
    )


@router.post("/", response_model=LessonRead, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    lesson_data: LessonCreate,
    current_user: CurrentInstructor = None,
    db: DbSession = None,
):
    """Create a new lesson (instructors only)"""
    course_stmt = select(CourseModel).where(CourseModel.id == lesson_data.course_id)
    course_result = await db.execute(course_stmt)
    course = course_result.scalar_one_or_none()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    if course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    db_lesson = LessonModel(**lesson_data.model_dump())
    db.add(db_lesson)
    await db.commit()

    stmt = (
        select(LessonModel)
        .where(LessonModel.id == db_lesson.id)
        .options(selectinload(LessonModel.tests))
    )
    result = await db.execute(stmt)
    db_lesson = result.scalar_one()

    return db_lesson


@router.put("/{lesson_id}", response_model=LessonRead)
async def update_lesson(
    lesson_id: int,
    lesson_data: LessonUpdate,
    current_user: CurrentInstructor = None,
    db: DbSession = None,
):
    """Update lesson details"""
    lesson_stmt = select(LessonModel).where(LessonModel.id == lesson_id)
    lesson_result = await db.execute(lesson_stmt)
    lesson = lesson_result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )

    course_stmt = select(CourseModel).where(CourseModel.id == lesson.course_id)
    course_result = await db.execute(course_stmt)
    course = course_result.scalar_one_or_none()

    if course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    update_data = lesson_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lesson, field, value)

    await db.commit()
    await db.refresh(lesson)

    return lesson


@router.delete("/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson(
    lesson_id: int,
    current_user: CurrentInstructor = None,
    db: DbSession = None,
):
    """Delete a lesson"""
    lesson_stmt = select(LessonModel).where(LessonModel.id == lesson_id)
    lesson_result = await db.execute(lesson_stmt)
    lesson = lesson_result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )

    course_stmt = select(CourseModel).where(CourseModel.id == lesson.course_id)
    course_result = await db.execute(course_stmt)
    course = course_result.scalar_one_or_none()

    if course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    await db.delete(lesson)
    await db.commit()

    return None


@router.post("/{lesson_id}/complete", status_code=status.HTTP_201_CREATED)
async def mark_lesson_complete(
    lesson_id: int,
    current_user: CurrentUser = None,
    db: DbSession = None,
):
    """Mark a lesson as completed and update overall course progress"""
    lesson_stmt = select(LessonModel).where(LessonModel.id == lesson_id)
    lesson_result = await db.execute(lesson_stmt)
    lesson = lesson_result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )

    existing_stmt = select(LessonCompletionModel).where(
        LessonCompletionModel.user_id == current_user.id,
        LessonCompletionModel.lesson_id == lesson_id,
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Lesson already completed"
        )

    completion = LessonCompletionModel(user_id=current_user.id, lesson_id=lesson_id)
    db.add(completion)
    await db.commit()
    await db.refresh(completion)

    enrollment_stmt = select(EnrollmentModel).where(
        EnrollmentModel.user_id == current_user.id,
        EnrollmentModel.course_id == lesson.course_id,
    )
    enrollment_result = await db.execute(enrollment_stmt)
    enrollment = enrollment_result.scalar_one_or_none()

    if enrollment:
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
        completed_lessons = completed_lessons_result.scalar()

        enrollment.progress_percentage = (
            (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
        )

        if enrollment.progress_percentage >= 100:
            enrollment.completed_at = datetime.now(timezone.utc)

        await db.commit()

    return {
        "message": "Lesson marked as completed",
        "completed_at": completion.completed_at,
    }


@router.delete("/{lesson_id}/complete", status_code=status.HTTP_204_NO_CONTENT)
async def remove_lesson_completion(
    lesson_id: int,
    current_user: CurrentUser = None,
    db: DbSession = None,
):
    """Remove completion status from a lesson"""
    completion_stmt = select(LessonCompletionModel).where(
        LessonCompletionModel.user_id == current_user.id,
        LessonCompletionModel.lesson_id == lesson_id,
    )
    completion_result = await db.execute(completion_stmt)
    completion = completion_result.scalar_one_or_none()

    if not completion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson completion record not found",
        )

    await db.delete(completion)
    await db.commit()

    return None
