from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class LessonBase(BaseModel):
    title: str
    content: Optional[str] = None
    video_url: Optional[str] = None
    order_index: int
    duration_minutes: Optional[int] = None


class LessonCreate(LessonBase):
    course_id: int


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    video_url: Optional[str] = None
    order_index: Optional[int] = None
    duration_minutes: Optional[int] = None


class Lesson(LessonBase):
    id: int
    course_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class LessonWithCompletion(Lesson):
    is_completed: bool = False