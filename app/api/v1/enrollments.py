from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from app.database import get_db
from app.schemas.enrollment import (
    Enrollment,
    EnrollmentCreate,
    LessonCompletionCreate,
    LessonCompletion,
)
from app.models.enrollment import Enrollment as EnrollmentModel
from app.models.lesson_completion import LessonCompletion as LessonCompletionModel
from app.models.course import Course as CourseModel
from app.models.lesson import Lesson as LessonModel
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


@router.get("/my", response_model=List[Enrollment])
def get_my_enrollments(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Отримати мої записи на курси"""
    return (
        db.query(EnrollmentModel)
        .filter(EnrollmentModel.user_id == current_user.id)
        .all()
    )


@router.post("/", response_model=Enrollment, status_code=status.HTTP_201_CREATED)
def enroll_in_course(
    enrollment_data: EnrollmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Записатися на курс"""
    course = (
        db.query(CourseModel)
        .filter(CourseModel.id == enrollment_data.course_id)
        .first()
    )

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    if not course.is_published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Course is not published"
        )

    existing = (
        db.query(EnrollmentModel)
        .filter(
            EnrollmentModel.user_id == current_user.id,
            EnrollmentModel.course_id == enrollment_data.course_id,
        )
        .first()
    )

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
    db.commit()
    db.refresh(enrollment)

    return enrollment


@router.post("/lessons/complete", response_model=LessonCompletion)
def complete_lesson(
    completion_data: LessonCompletionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Відмітити урок як виконаний"""
    lesson = (
        db.query(LessonModel)
        .filter(LessonModel.id == completion_data.lesson_id)
        .first()
    )

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )

    enrollment = (
        db.query(EnrollmentModel)
        .filter(
            EnrollmentModel.user_id == current_user.id,
            EnrollmentModel.course_id == lesson.course_id,
        )
        .first()
    )

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enrolled in this course",
        )

    existing = (
        db.query(LessonCompletionModel)
        .filter(
            LessonCompletionModel.user_id == current_user.id,
            LessonCompletionModel.lesson_id == completion_data.lesson_id,
        )
        .first()
    )

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

    total_lessons = (
        db.query(LessonModel).filter(LessonModel.course_id == lesson.course_id).count()
    )

    completed_lessons = (
        db.query(LessonCompletionModel)
        .join(LessonModel)
        .filter(
            LessonCompletionModel.user_id == current_user.id,
            LessonModel.course_id == lesson.course_id,
        )
        .count()
        + 1
    )

    enrollment.progress_percentage = (completed_lessons / total_lessons) * 100

    if enrollment.progress_percentage >= 100:
        enrollment.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(completion)

    return completion


@router.get("/course/{course_id}/progress")
def get_course_progress(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Отримати прогрес по курсу"""
    enrollment = (
        db.query(EnrollmentModel)
        .filter(
            EnrollmentModel.user_id == current_user.id,
            EnrollmentModel.course_id == course_id,
        )
        .first()
    )

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not enrolled in this course"
        )

    total_lessons = (
        db.query(LessonModel).filter(LessonModel.course_id == course_id).count()
    )

    completed_lessons = (
        db.query(LessonCompletionModel)
        .join(LessonModel)
        .filter(
            LessonCompletionModel.user_id == current_user.id,
            LessonModel.course_id == course_id,
        )
        .count()
    )

    return {
        "enrollment_id": enrollment.id,
        "progress_percentage": enrollment.progress_percentage,
        "completed_lessons": completed_lessons,
        "total_lessons": total_lessons,
        "is_completed": enrollment.completed_at is not None,
        "completed_at": enrollment.completed_at,
    }
