from app.schemas.course import Course
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class EnrollmentCreate(BaseModel):
    course_id: int


class Enrollment(BaseModel):
    id: int
    user_id: int
    course_id: int
    enrolled_at: datetime
    completed_at: Optional[datetime] = None
    progress_percentage: float
    course: Course

    class Config:
        from_attributes = True


class LessonCompletionCreate(BaseModel):
    lesson_id: int
    time_spent_minutes: Optional[int] = None


class LessonCompletion(BaseModel):
    id: int
    user_id: int
    lesson_id: int
    completed_at: datetime
    time_spent_minutes: Optional[int] = None

    class Config:
        from_attributes = True
