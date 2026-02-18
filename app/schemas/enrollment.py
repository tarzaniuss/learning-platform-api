from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.course import CourseRead


class EnrollmentCreate(BaseModel):
    course_id: int


class EnrollmentRead(BaseModel):
    id: int
    user_id: int
    course_id: int
    enrolled_at: datetime
    completed_at: Optional[datetime] = None
    progress_percentage: float
    course: CourseRead

    model_config = ConfigDict(from_attributes=True)


class LessonCompletionCreate(BaseModel):
    lesson_id: int
    time_spent_minutes: Optional[int] = None


class LessonCompletionRead(BaseModel):
    id: int
    user_id: int
    lesson_id: int
    completed_at: datetime
    time_spent_minutes: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
