from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional

from app.schemas.test import Test


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
    tests: List[Test] = []

    model_config = ConfigDict(from_attributes=True)


class LessonWithCompletion(Lesson):
    is_completed: bool = False
