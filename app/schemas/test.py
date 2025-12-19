from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.models.test import QuestionType


class AnswerOptionBase(BaseModel):
    option_text: str
    is_correct: bool
    order_index: int


class AnswerOptionCreate(AnswerOptionBase):
    pass


class AnswerOption(AnswerOptionBase):
    id: int
    question_id: int

    class Config:
        from_attributes = True


class QuestionBase(BaseModel):
    question_text: str
    question_type: QuestionType
    points: int = 1
    order_index: int


class QuestionCreate(QuestionBase):
    answer_options: List[AnswerOptionCreate] = []


class Question(QuestionBase):
    id: int
    test_id: int
    answer_options: List[AnswerOption] = []

    class Config:
        from_attributes = True


class TestBase(BaseModel):
    title: str
    description: Optional[str] = None
    passing_score: float
    time_limit_minutes: Optional[int] = None


class TestCreate(TestBase):
    lesson_id: int
    questions: List[QuestionCreate] = []


class TestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    passing_score: Optional[float] = None
    time_limit_minutes: Optional[int] = None


class Test(TestBase):
    id: int
    lesson_id: int
    created_at: datetime
    questions: List[Question] = []

    class Config:
        from_attributes = True


class TestAttemptCreate(BaseModel):
    test_id: int
    answers_data: Dict[str, Any]


class TestAttempt(BaseModel):
    id: int
    user_id: int
    test_id: int
    score: float
    passed: bool
    started_at: datetime
    completed_at: Optional[datetime] = None
    time_spent_minutes: Optional[int] = None
    answers_data: Dict[str, Any]

    class Config:
        from_attributes = True