from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.course import Course, CourseCreate, CourseUpdate
from app.models.course import Course as CourseModel
from app.models.user import User
from app.api.deps import get_current_active_instructor

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get("/", response_model=List[Course])
def get_courses(
    skip: int = 0,
    limit: int = 100,
    is_published: bool = True,
    db: Session = Depends(get_db)
):
    """Отримати список курсів (каталог)"""
    query = db.query(CourseModel)
    if is_published:
        query = query.filter(CourseModel.is_published == True)
    
    courses = query.offset(skip).limit(limit).all()
    return courses


@router.get("/{course_id}", response_model=Course)
def get_course(course_id: int, db: Session = Depends(get_db)):
    """Отримати деталі курсу"""
    course = db.query(CourseModel).filter(CourseModel.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    return course


@router.post("/", response_model=Course, status_code=status.HTTP_201_CREATED)
def create_course(
    course_data: CourseCreate,
    current_user: User = Depends(get_current_active_instructor),
    db: Session = Depends(get_db)
):
    """Створити новий курс (тільки для інструкторів)"""
    db_course = CourseModel(
        **course_data.model_dump(),
        instructor_id=current_user.id
    )
    
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    
    return db_course


@router.put("/{course_id}", response_model=Course)
def update_course(
    course_id: int,
    course_data: CourseUpdate,
    current_user: User = Depends(get_current_active_instructor),
    db: Session = Depends(get_db)
):
    """Оновити курс"""
    course = db.query(CourseModel).filter(CourseModel.id == course_id).first()
    
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
    
    update_data = course_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(course, field, value)
    
    db.commit()
    db.refresh(course)
    
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: int,
    current_user: User = Depends(get_current_active_instructor),
    db: Session = Depends(get_db)
):
    """Видалити курс"""
    course = db.query(CourseModel).filter(CourseModel.id == course_id).first()
    
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
    
    db.delete(course)
    db.commit()
    
    return None