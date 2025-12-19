from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
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
    db: Session = Depends(get_db)
):
    """Отримати всі уроки курсу з відміткою про виконання"""
    course = db.query(CourseModel).filter(CourseModel.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    lessons = db.query(LessonModel).filter(
        LessonModel.course_id == course_id
    ).order_by(LessonModel.order_index).all()
    
    completed_lesson_ids = {
        lc.lesson_id for lc in db.query(LessonCompletion).filter(
            LessonCompletion.user_id == current_user.id,
            LessonCompletion.lesson_id.in_([l.id for l in lessons])
        ).all()
    }
    
    result = []
    for lesson in lessons:
        lesson_dict = {
            **lesson.__dict__,
            "is_completed": lesson.id in completed_lesson_ids
        }
        result.append(lesson_dict)
    
    return result


@router.get("/{lesson_id}", response_model=Lesson)
def get_lesson(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отримати деталі уроку"""
    lesson = db.query(LessonModel).filter(LessonModel.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    return lesson


@router.post("/", response_model=Lesson, status_code=status.HTTP_201_CREATED)
def create_lesson(
    lesson_data: LessonCreate,
    current_user: User = Depends(get_current_active_instructor),
    db: Session = Depends(get_db)
):
    """Створити новий урок (тільки для інструкторів)"""
    course = db.query(CourseModel).filter(CourseModel.id == lesson_data.course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    if course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
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
    db: Session = Depends(get_db)
):
    """Оновити урок"""
    lesson = db.query(LessonModel).filter(LessonModel.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    course = db.query(CourseModel).filter(CourseModel.id == lesson.course_id).first()
    if course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
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
    db: Session = Depends(get_db)
):
    """Видалити урок"""
    lesson = db.query(LessonModel).filter(LessonModel.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    course = db.query(CourseModel).filter(CourseModel.id == lesson.course_id).first()
    if course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    db.delete(lesson)
    db.commit()
    
    return None