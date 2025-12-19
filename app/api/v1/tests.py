from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from app.database import get_db
from app.schemas.test import Test, TestCreate, TestAttempt, TestAttemptCreate
from app.models.test import (
    Test as TestModel,
    Question,
    AnswerOption,
    TestAttempt as TestAttemptModel,
    QuestionType,
)
from app.models.course import Course as CourseModel
from app.models.lesson_completion import LessonCompletion
from app.models.lesson import Lesson as LessonModel
from app.models.enrollment import Enrollment as EnrollmentModel
from app.models.user import User
from app.api.deps import get_current_user, get_current_active_instructor

router = APIRouter(prefix="/tests", tags=["Tests"])


@router.get("/lesson/{lesson_id}", response_model=List[Test])
def get_lesson_tests(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Отримати всі тести уроку"""
    tests = db.query(TestModel).filter(TestModel.lesson_id == lesson_id).all()
    return tests


@router.get("/{test_id}", response_model=Test)
def get_test(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Отримати деталі тесту з питаннями"""
    test = db.query(TestModel).filter(TestModel.id == test_id).first()
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Test not found"
        )
    return test


@router.post("/", response_model=Test, status_code=status.HTTP_201_CREATED)
def create_test(
    test_data: TestCreate,
    current_user: User = Depends(get_current_active_instructor),
    db: Session = Depends(get_db),
):
    """Створити новий тест з питаннями (тільки для інструкторів)"""
    lesson = db.query(LessonModel).filter(LessonModel.id == test_data.lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    course = db.query(CourseModel).filter(CourseModel.id == lesson.course_id).first()

    if course.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this course")

    test_dict = test_data.model_dump(exclude={"questions"})
    db_test = TestModel(**test_dict)
    db.add(db_test)
    db.flush()

    for question_data in test_data.questions:
        question_dict = question_data.model_dump(exclude={"answer_options"})
        db_question = Question(**question_dict, test_id=db_test.id)
        db.add(db_question)
        db.flush()

        for answer_data in question_data.answer_options:
            db_answer = AnswerOption(
                **answer_data.model_dump(), question_id=db_question.id
            )
            db.add(db_answer)

    db.commit()
    db.refresh(db_test)

    return db_test


@router.post("/{test_id}/attempt", response_model=TestAttempt)
def submit_test_attempt(
    test_id: int,
    attempt_data: TestAttemptCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Відправити відповіді на тест і отримати результат"""
    test = db.query(TestModel).filter(TestModel.id == test_id).first()
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Test not found"
        )

    questions = db.query(Question).filter(Question.test_id == test_id).all()

    gradable_questions = [q for q in questions if q.question_type != QuestionType.TEXT]
    total_points = sum(q.points for q in gradable_questions)
    earned_points = 0

    for question in gradable_questions:
        user_answer = attempt_data.answers_data.get(str(question.id))
        if user_answer is None:
            user_answer = attempt_data.answers_data.get(question.id)

        if user_answer is None:
            continue

        correct_answers = (
            db.query(AnswerOption)
            .filter(AnswerOption.question_id == question.id, AnswerOption.is_correct)
            .all()
        )

        correct_answer_ids = {a.id for a in correct_answers}

        if question.question_type == QuestionType.SINGLE_CHOICE:
            ans = user_answer
            if isinstance(ans, list) and ans:
                ans = ans[0]
            try:
                ans_id = int(ans)
            except Exception:
                continue
            if ans_id in correct_answer_ids:
                earned_points += question.points

        elif question.question_type == QuestionType.MULTIPLE_CHOICE:
            if not isinstance(user_answer, (list, tuple, set)):
                user_answer_list = [user_answer]
            else:
                user_answer_list = list(user_answer)

            user_answer_ids = set()
            for v in user_answer_list:
                try:
                    user_answer_ids.add(int(v))
                except Exception:
                    continue

            if user_answer_ids == correct_answer_ids:
                earned_points += question.points

    score = (earned_points / total_points * 100) if total_points > 0 else 0
    passed = score >= test.passing_score

    attempt = TestAttemptModel(
        user_id=current_user.id,
        test_id=test_id,
        score=score,
        passed=passed,
        completed_at=datetime.utcnow(),
        answers_data=attempt_data.answers_data,
    )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    if passed:
        existing_completion = (
            db.query(LessonCompletion)
            .filter(
                LessonCompletion.user_id == current_user.id,
                LessonCompletion.lesson_id == test.lesson_id,
            )
            .first()
        )
        if not existing_completion:
            completion = LessonCompletion(
                user_id=current_user.id,
                lesson_id=test.lesson_id,
            )
            db.add(completion)
            db.commit()

            enrollment = (
                db.query(EnrollmentModel)
                .filter(
                    EnrollmentModel.user_id == current_user.id,
                    EnrollmentModel.course_id == test.lesson.course_id,
                )
                .first()
            )

            if enrollment:
                total_lessons = (
                    db.query(LessonModel)
                    .filter(LessonModel.course_id == test.lesson.course_id)
                    .count()
                )

                completed_lessons = (
                    db.query(LessonCompletion)
                    .join(LessonModel)
                    .filter(
                        LessonCompletion.user_id == current_user.id,
                        LessonModel.course_id == test.lesson.course_id,
                    )
                    .count()
                )

                enrollment.progress_percentage = (
                    (completed_lessons / total_lessons * 100)
                    if total_lessons > 0
                    else 0
                )

                if enrollment.progress_percentage >= 100:
                    enrollment.completed_at = datetime.now(timezone.utc)

                db.commit()

    return attempt


@router.get("/{test_id}/attempts", response_model=List[TestAttempt])
def get_my_test_attempts(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Отримати мої спроби проходження тесту"""
    attempts = (
        db.query(TestAttemptModel)
        .filter(
            TestAttemptModel.test_id == test_id,
            TestAttemptModel.user_id == current_user.id,
        )
        .order_by(TestAttemptModel.started_at.desc())
        .all()
    )

    return attempts
