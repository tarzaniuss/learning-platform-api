from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text)
    video_url = Column(String, nullable=True)
    order_index = Column(Integer, nullable=False)
    duration_minutes = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    course = relationship("Course", back_populates="lessons")
    completions = relationship(
        "LessonCompletion", back_populates="lesson", cascade="all, delete-orphan"
    )
    tests = relationship("Test", back_populates="lesson", cascade="all, delete-orphan")
