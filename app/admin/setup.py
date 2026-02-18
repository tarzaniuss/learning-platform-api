from fastapi import FastAPI
from sqladmin import Admin
from sqlalchemy.ext.asyncio import AsyncEngine

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


def setup_admin_no_auth(app: FastAPI, engine: AsyncEngine) -> Admin:
    admin = Admin(app, engine, title="Learning Platform Admin (Dev Mode)")

    admin.add_view(UserAdmin)
    admin.add_view(CourseAdmin)
    admin.add_view(LessonAdmin)
    admin.add_view(EnrollmentAdmin)
    admin.add_view(TestAdmin)
    admin.add_view(QuestionAdmin)
    admin.add_view(AnswerOptionAdmin)
    admin.add_view(TestAttemptAdmin)
    admin.add_view(LessonCompletionAdmin)

    return admin
