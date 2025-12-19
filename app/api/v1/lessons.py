from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from app.database import get_db
from app.models.enrollment import Enrollment as EnrollmentModel
from app.schemas.lesson import Lesson, LessonCreate, LessonUpdate, LessonWithCompletion
from app.models.lesson import Lesson as LessonModel
from app.models.course import Course as CourseModel
from app.models.lesson_completion import LessonCompletion
from app.models.user import User
from app.api.deps import get_current_user, get_current_active_instructor

router = APIRouter(prefix="/lessons", tags=["Lessons"])


@router.get("/course/{course_id}", response_model=List[LessonWithCompletion])
def get_course_lessons(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = db.query(CourseModel).filter(CourseModel.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    lessons = (
        db.query(LessonModel)
        .filter(LessonModel.course_id == course_id)
        .order_by(LessonModel.order_index)
        .all()
    )

    is_enrolled = (
        db.query(EnrollmentModel)
        .filter_by(user_id=current_user.id, course_id=course_id)
        .first()
        is not None
    )

    completed_ids = set()
    if is_enrolled:
        completed_ids = {
            lc.lesson_id
            for lc in db.query(LessonCompletion).filter(
                LessonCompletion.user_id == current_user.id,
                LessonCompletion.lesson_id.in_([l.id for l in lessons]),
            )
        }

    return [
        LessonWithCompletion(
            **{**lesson.__dict__, "is_completed": lesson.id in completed_ids}
        )
        for lesson in lessons
    ]


@router.get("/{lesson_id}", response_model=LessonWithCompletion)
def get_lesson(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Отримати деталі уроку з прапорцем виконання"""
    lesson = db.query(LessonModel).filter(LessonModel.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )

    is_completed = (
        db.query(LessonCompletion)
        .filter(
            LessonCompletion.user_id == current_user.id,
            LessonCompletion.lesson_id == lesson_id,
        )
        .first()
        is not None
    )

    return LessonWithCompletion(
        **{c.name: getattr(lesson, c.name) for c in lesson.__table__.columns},
        is_completed=is_completed,
    )


@router.post("/", response_model=Lesson, status_code=status.HTTP_201_CREATED)
def create_lesson(
    lesson_data: LessonCreate,
    current_user: User = Depends(get_current_active_instructor),
    db: Session = Depends(get_db),
):
    """Створити новий урок (тільки для інструкторів)"""
    course = (
        db.query(CourseModel).filter(CourseModel.id == lesson_data.course_id).first()
    )
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
    db.commit()
    db.refresh(db_lesson)

    return db_lesson


@router.put("/{lesson_id}", response_model=Lesson)
def update_lesson(
    lesson_id: int,
    lesson_data: LessonUpdate,
    current_user: User = Depends(get_current_active_instructor),
    db: Session = Depends(get_db),
):
    """Оновити урок"""
    lesson = db.query(LessonModel).filter(LessonModel.id == lesson_id).first()

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )

    course = db.query(CourseModel).filter(CourseModel.id == lesson.course_id).first()
    if course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    update_data = lesson_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lesson, field, value)

    db.commit()
    db.refresh(lesson)

    return lesson


@router.delete("/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson(
    lesson_id: int,
    current_user: User = Depends(get_current_active_instructor),
    db: Session = Depends(get_db),
):
    """Видалити урок"""
    lesson = db.query(LessonModel).filter(LessonModel.id == lesson_id).first()

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )

    course = db.query(CourseModel).filter(CourseModel.id == lesson.course_id).first()
    if course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    db.delete(lesson)
    db.commit()

    return None


@router.post("/{lesson_id}/complete", status_code=status.HTTP_201_CREATED)
def mark_lesson_complete(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Позначити урок як пройдений"""
    lesson = db.query(LessonModel).filter(LessonModel.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )

    existing = (
        db.query(LessonCompletion)
        .filter(
            LessonCompletion.user_id == current_user.id,
            LessonCompletion.lesson_id == lesson_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Lesson already completed"
        )

    completion = LessonCompletion(user_id=current_user.id, lesson_id=lesson_id)
    db.add(completion)
    db.commit()
    db.refresh(completion)

    enrollment = (
        db.query(EnrollmentModel)
        .filter(
            EnrollmentModel.user_id == current_user.id,
            EnrollmentModel.course_id == lesson.course_id,
        )
        .first()
    )

    if enrollment:
        total_lessons = (
            db.query(LessonModel)
            .filter(LessonModel.course_id == lesson.course_id)
            .count()
        )

        completed_lessons = (
            db.query(LessonCompletion)
            .join(LessonModel)
            .filter(
                LessonCompletion.user_id == current_user.id,
                LessonModel.course_id == lesson.course_id,
            )
            .count()
        )

        enrollment.progress_percentage = (
            (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
        )

        if enrollment.progress_percentage >= 100:
            enrollment.completed_at = datetime.now(timezone.utc)

        db.commit()

    return {
        "message": "Lesson marked as completed",
        "completed_at": completion.completed_at,
    }


@router.delete("/{lesson_id}/complete", status_code=status.HTTP_204_NO_CONTENT)
def remove_lesson_completion(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Видалити позначку про виконання уроку"""
    completion = (
        db.query(LessonCompletion)
        .filter(
            LessonCompletion.user_id == current_user.id,
            LessonCompletion.lesson_id == lesson_id,
        )
        .first()
    )
    if not completion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson completion record not found",
        )

    db.delete(completion)
    db.commit()

    return None
