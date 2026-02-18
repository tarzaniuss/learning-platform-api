from sqladmin import ModelView

from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.lesson import Lesson
from app.models.lesson_completion import LessonCompletion
from app.models.test import AnswerOption, Question, Test, TestAttempt
from app.models.user import User


class UserAdmin(ModelView, model=User):
    """Адмін панель для користувачів"""

    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"

    column_list = [
        User.id,
        User.email,
        User.full_name,
        User.role,
        User.created_at,
    ]

    column_searchable_list = [User.email, User.full_name]
    column_sortable_list = [User.id, User.email, User.created_at]
    column_default_sort = [(User.id, False)]

    column_details_exclude_list = [User.hashed_password]
    form_excluded_columns = [User.hashed_password, User.created_at]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class CourseAdmin(ModelView, model=Course):
    """Адмін панель для курсів"""

    name = "Course"
    name_plural = "Courses"
    icon = "fa-solid fa-book"

    column_list = [
        Course.id,
        Course.title,
        Course.instructor_id,
        Course.category,
        Course.difficulty_level,
        Course.is_published,
        Course.created_at,
    ]

    column_searchable_list = [Course.title, Course.category]
    column_sortable_list = [Course.id, Course.title, Course.created_at]
    column_default_sort = [(Course.id, False)]

    form_excluded_columns = [Course.created_at]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class LessonAdmin(ModelView, model=Lesson):
    """Адмін панель для уроків"""

    name = "Lesson"
    name_plural = "Lessons"
    icon = "fa-solid fa-graduation-cap"

    column_list = [
        Lesson.id,
        Lesson.course_id,
        Lesson.title,
        Lesson.order_index,
        Lesson.duration_minutes,
        Lesson.created_at,
    ]

    column_searchable_list = [Lesson.title]
    column_sortable_list = [Lesson.id, Lesson.title, Lesson.order_index]
    column_default_sort = [(Lesson.order_index, True)]

    form_excluded_columns = [Lesson.created_at]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class EnrollmentAdmin(ModelView, model=Enrollment):
    """Адмін панель для записів на курси"""

    name = "Enrollment"
    name_plural = "Enrollments"
    icon = "fa-solid fa-user-check"

    column_list = [
        Enrollment.id,
        Enrollment.user_id,
        Enrollment.course_id,
        Enrollment.enrolled_at,
        Enrollment.progress_percentage,
        Enrollment.completed_at,
    ]

    column_sortable_list = [
        Enrollment.id,
        Enrollment.enrolled_at,
        Enrollment.progress_percentage,
    ]
    column_default_sort = [(Enrollment.enrolled_at, False)]

    form_excluded_columns = [Enrollment.enrolled_at]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class TestAdmin(ModelView, model=Test):
    """Адмін панель для тестів"""

    name = "Test"
    name_plural = "Tests"
    icon = "fa-solid fa-clipboard-question"

    column_list = [
        Test.id,
        Test.lesson_id,
        Test.title,
        Test.passing_score,
        Test.time_limit_minutes,
        Test.created_at,
    ]

    column_searchable_list = [Test.title]
    column_sortable_list = [Test.id, Test.title, Test.created_at]
    column_default_sort = [(Test.id, False)]

    form_excluded_columns = [Test.created_at]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class QuestionAdmin(ModelView, model=Question):
    """Адмін панель для питань"""

    name = "Question"
    name_plural = "Questions"
    icon = "fa-solid fa-question"

    column_list = [
        Question.id,
        Question.test_id,
        Question.question_text,
        Question.question_type,
        Question.points,
        Question.order_index,
    ]

    column_searchable_list = [Question.question_text]
    column_sortable_list = [Question.id, Question.order_index]
    column_default_sort = [(Question.order_index, True)]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class AnswerOptionAdmin(ModelView, model=AnswerOption):
    """Адмін панель для варіантів відповідей"""

    name = "Answer Option"
    name_plural = "Answer Options"
    icon = "fa-solid fa-list-check"

    column_list = [
        AnswerOption.id,
        AnswerOption.question_id,
        AnswerOption.option_text,
        AnswerOption.is_correct,
        AnswerOption.order_index,
    ]

    column_searchable_list = [AnswerOption.option_text]
    column_sortable_list = [AnswerOption.id, AnswerOption.order_index]
    column_default_sort = [(AnswerOption.order_index, True)]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class TestAttemptAdmin(ModelView, model=TestAttempt):
    """Адмін панель для спроб тестів"""

    name = "Test Attempt"
    name_plural = "Test Attempts"
    icon = "fa-solid fa-pen-to-square"

    column_list = [
        TestAttempt.id,
        TestAttempt.user_id,
        TestAttempt.test_id,
        TestAttempt.score,
        TestAttempt.passed,
        TestAttempt.started_at,
        TestAttempt.completed_at,
    ]

    column_sortable_list = [TestAttempt.id, TestAttempt.score, TestAttempt.started_at]
    column_default_sort = [(TestAttempt.started_at, False)]

    form_excluded_columns = [TestAttempt.started_at]

    can_create = False  # Створювати спроби не має сенсу вручну
    can_edit = True
    can_delete = True
    can_view_details = True


class LessonCompletionAdmin(ModelView, model=LessonCompletion):
    """Адмін панель для виконання уроків"""

    name = "Lesson Completion"
    name_plural = "Lesson Completions"
    icon = "fa-solid fa-check-double"

    column_list = [
        LessonCompletion.id,
        LessonCompletion.user_id,
        LessonCompletion.lesson_id,
        LessonCompletion.completed_at,
        LessonCompletion.time_spent_minutes,
    ]

    column_sortable_list = [LessonCompletion.id, LessonCompletion.completed_at]
    column_default_sort = [(LessonCompletion.completed_at, False)]

    form_excluded_columns = [LessonCompletion.completed_at]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
