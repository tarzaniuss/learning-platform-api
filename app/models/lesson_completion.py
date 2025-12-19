from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class LessonCompletion(Base):
    __tablename__ = "lesson_completions"
    __table_args__ = (
        UniqueConstraint('user_id', 'lesson_id', name='unique_user_lesson'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())
    time_spent_minutes = Column(Integer, nullable=True)

    user = relationship("User", back_populates="lesson_completions")
    lesson = relationship("Lesson", back_populates="completions")