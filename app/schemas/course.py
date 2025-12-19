from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.course import DifficultyLevel


class CourseBase(BaseModel):
    title: str
    description: Optional[str] = None
    duration_hours: Optional[int] = None
    category: Optional[str] = None
    difficulty_level: DifficultyLevel = DifficultyLevel.BEGINNER
    is_published: bool = False


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    duration_hours: Optional[int] = None
    category: Optional[str] = None
    difficulty_level: Optional[DifficultyLevel] = None
    is_published: Optional[bool] = None


class Course(CourseBase):
    id: int
    instructor_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CourseWithLessonsCount(Course):
    lessons_count: int
    enrolled_students_count: int