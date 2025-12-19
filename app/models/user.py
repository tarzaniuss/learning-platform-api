from sqlalchemy import Column, Enum, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class UserRole(str, enum.Enum):
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.STUDENT, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    created_courses = relationship("Course", back_populates="instructor", foreign_keys="Course.instructor_id")
    enrollments = relationship("Enrollment", back_populates="user")
    lesson_completions = relationship("LessonCompletion", back_populates="user")
    test_attempts = relationship("TestAttempt", back_populates="user")