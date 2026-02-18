from sqladmin import Admin

from app.admin.setup import setup_admin_no_auth
from app.admin.views import (
    AnswerOptionAdmin,
    CourseAdmin,
    EnrollmentAdmin,
    LessonAdmin,
    LessonCompletionAdmin,
    QuestionAdmin,
    TestAdmin,
    TestAttemptAdmin,
    UserAdmin,
)

__all__ = [
    "Admin",
    "setup_admin_no_auth",
    "UserAdmin",
    "CourseAdmin",
    "LessonAdmin",
    "EnrollmentAdmin",
    "TestAdmin",
    "QuestionAdmin",
    "AnswerOptionAdmin",
    "TestAttemptAdmin",
    "LessonCompletionAdmin",
]
