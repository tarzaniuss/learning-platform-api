from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentInstructor, CurrentUser, DbSession
from app.models.course import Course as CourseModel
from app.models.enrollment import Enrollment as EnrollmentModel
from app.models.lesson import Lesson as LessonModel
from app.models.lesson_completion import LessonCompletion
from app.models.test import (
    AnswerOption as AnswerOptionModel,
)
from app.models.test import (
    Question as QuestionModel,
)
from app.models.test import (
    QuestionType,
)
from app.models.test import (
    Test as TestModel,
)
from app.models.test import (
    TestAttempt as TestAttemptModel,
)
from app.schemas.test import TestAttemptCreate, TestAttemptRead, TestCreate, TestRead

router = APIRouter(prefix="/tests", tags=["Tests"])


@router.get("/lesson/{lesson_id}", response_model=List[TestRead])
async def get_lesson_tests(
    lesson_id: int,
    current_user: CurrentUser = None,
    db: DbSession = None,
):
    """Retrieve all tests for a specific lesson"""
    stmt = select(TestModel).where(TestModel.lesson_id == lesson_id)
    result = await db.execute(stmt)
    tests = result.scalars().all()
    return tests


@router.get("/{test_id}", response_model=TestRead)
async def get_test(
    test_id: int,
    current_user: CurrentUser = None,
    db: DbSession = None,
):
    """Get detailed test information including questions and answer options"""

    stmt = (
        select(TestModel)
        .where(TestModel.id == test_id)
        .options(
            selectinload(TestModel.questions).selectinload(QuestionModel.answer_options)
        )
    )
    result = await db.execute(stmt)
    test = result.scalar_one_or_none()

    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Test not found"
        )
    return test


@router.post("/", response_model=TestRead, status_code=status.HTTP_201_CREATED)
async def create_test(
    test_data: TestCreate,
    current_user: CurrentInstructor = None,
    db: DbSession = None,
):
    """Create a new test with questions and options (instructors only)"""
    lesson_stmt = select(LessonModel).where(LessonModel.id == test_data.lesson_id)
    lesson_result = await db.execute(lesson_stmt)
    lesson = lesson_result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )

    course_stmt = select(CourseModel).where(CourseModel.id == lesson.course_id)
    course_result = await db.execute(course_stmt)
    course = course_result.scalar_one_or_none()

    if course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this course"
        )

    test_dict = test_data.model_dump(exclude={"questions"})
    db_test = TestModel(**test_dict)
    db.add(db_test)
    await db.flush()

    for question_data in test_data.questions:
        question_dict = question_data.model_dump(exclude={"answer_options"})
        db_question = QuestionModel(**question_dict, test_id=db_test.id)
        db.add(db_question)
        await db.flush()

        for answer_data in question_data.answer_options:
            db_answer = AnswerOptionModel(
                **answer_data.model_dump(), question_id=db_question.id
            )
            db.add(db_answer)

    await db.commit()
    await db.refresh(db_test)

    return db_test


@router.post("/{test_id}/attempt", response_model=TestAttemptRead)
async def submit_test_attempt(
    test_id: int,
    attempt_data: TestAttemptCreate,
    current_user: CurrentUser = None,
    db: DbSession = None,
):
    """Submit test answers, calculate score, and update progress if passed"""
    stmt = (
        select(TestModel)
        .where(TestModel.id == test_id)
        .options(selectinload(TestModel.lesson))
    )
    result = await db.execute(stmt)
    test = result.scalar_one_or_none()

    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Test not found"
        )

    questions_stmt = (
        select(QuestionModel)
        .where(QuestionModel.test_id == test_id)
        .options(selectinload(QuestionModel.answer_options))
    )
    questions_result = await db.execute(questions_stmt)
    questions = questions_result.scalars().all()

    gradable_questions = [q for q in questions if q.question_type != QuestionType.TEXT]
    total_points = sum(q.points for q in gradable_questions)
    earned_points = 0

    for question in gradable_questions:
        user_answer = attempt_data.answers_data.get(str(question.id))
        if user_answer is None:
            user_answer = attempt_data.answers_data.get(question.id)

        if user_answer is None:
            continue

        correct_answer_ids = {a.id for a in question.answer_options if a.is_correct}

        if question.question_type == QuestionType.SINGLE_CHOICE:
            ans = (
                user_answer[0]
                if isinstance(user_answer, list) and user_answer
                else user_answer
            )
            try:
                if int(ans) in correct_answer_ids:
                    earned_points += question.points
            except (ValueError, TypeError):
                continue

        elif question.question_type == QuestionType.MULTIPLE_CHOICE:
            user_answer_list = (
                user_answer if isinstance(user_answer, list) else [user_answer]
            )
            try:
                user_answer_ids = {int(v) for v in user_answer_list}
                if user_answer_ids == correct_answer_ids:
                    earned_points += question.points
            except (ValueError, TypeError):
                continue

    score = (earned_points / total_points * 100) if total_points > 0 else 0
    passed = score >= test.passing_score

    attempt = TestAttemptModel(
        user_id=current_user.id,
        test_id=test_id,
        score=score,
        passed=passed,
        completed_at=datetime.now(timezone.utc),
        answers_data=attempt_data.answers_data,
    )

    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)

    if passed:
        existing_completion_stmt = select(LessonCompletion).where(
            LessonCompletion.user_id == current_user.id,
            LessonCompletion.lesson_id == test.lesson_id,
        )
        existing_res = await db.execute(existing_completion_stmt)
        if not existing_res.scalar_one_or_none():
            completion = LessonCompletion(
                user_id=current_user.id,
                lesson_id=test.lesson_id,
            )
            db.add(completion)
            await db.commit()

            enroll_stmt = select(EnrollmentModel).where(
                EnrollmentModel.user_id == current_user.id,
                EnrollmentModel.course_id == test.lesson.course_id,
            )
            enroll_res = await db.execute(enroll_stmt)
            enrollment = enroll_res.scalar_one_or_none()

            if enrollment:
                total_stmt = (
                    select(func.count())
                    .select_from(LessonModel)
                    .where(LessonModel.course_id == test.lesson.course_id)
                )
                total_val = (await db.execute(total_stmt)).scalar() or 0

                comp_stmt = (
                    select(func.count())
                    .select_from(LessonCompletion)
                    .join(LessonModel)
                    .where(
                        LessonCompletion.user_id == current_user.id,
                        LessonModel.course_id == test.lesson.course_id,
                    )
                )
                comp_val = (await db.execute(comp_stmt)).scalar() or 0

                enrollment.progress_percentage = (
                    (comp_val / total_val * 100) if total_val > 0 else 0
                )
                if enrollment.progress_percentage >= 100:
                    enrollment.completed_at = datetime.now(timezone.utc)

                await db.commit()

    return attempt


@router.get("/{test_id}/attempts", response_model=List[TestAttemptRead])
async def get_my_test_attempts(
    test_id: int,
    current_user: CurrentUser = None,
    db: DbSession = None,
):
    """Retrieve the current user's attempts for a specific test"""
    stmt = (
        select(TestAttemptModel)
        .where(
            TestAttemptModel.test_id == test_id,
            TestAttemptModel.user_id == current_user.id,
        )
        .order_by(TestAttemptModel.completed_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()
