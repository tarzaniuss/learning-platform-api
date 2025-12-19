from sqlalchemy import Column, Integer, DateTime, ForeignKey, Float, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint('user_id', 'course_id', name='unique_user_course'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    progress_percentage = Column(Float, default=0.0)

    user = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
