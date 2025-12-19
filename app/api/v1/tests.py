from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.schemas.test import Test, TestCreate, TestAttempt, TestAttemptCreate
from app.models.test import Test as TestModel, Question, AnswerOption, TestAttempt as TestAttemptModel
from app.models.course import Course as CourseModel
from app.models.user import User
from app.api.deps import get_current_user, get_current_active_instructor

router = APIRouter(prefix="/tests", tags=["Tests"])


@router.get("/lesson/{lesson_id}", response_model=List[Test])
def get_lesson_tests(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отримати всі тести уроку"""
    tests = db.query(TestModel).filter(
        TestModel.lesson_id == lesson_id
    ).all()
    return tests


@router.get("/{test_id}", response_model=Test)
def get_test(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отримати деталі тесту з питаннями"""
    test = db.query(TestModel).filter(TestModel.id == test_id).first()
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    return test


@router.post("/", response_model=Test, status_code=status.HTTP_201_CREATED)
def create_test(
    test_data: TestCreate,
    current_user: User = Depends(get_current_active_instructor),
    db: Session = Depends(get_db)
):
    """Створити новий тест з питаннями (тільки для інструкторів)"""
    course = db.query(CourseModel).filter(CourseModel.id == test_data.lesson_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    if course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    test_dict = test_data.model_dump(exclude={'questions'})
    db_test = TestModel(**test_dict)
    db.add(db_test)
    db.flush()
    
    for question_data in test_data.questions:
        question_dict = question_data.model_dump(exclude={'answer_options'})
        db_question = Question(**question_dict, test_id=db_test.id)
        db.add(db_question)
        db.flush()
        
        for answer_data in question_data.answer_options:
            db_answer = AnswerOption(
                **answer_data.model_dump(),
                question_id=db_question.id
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
    db: Session = Depends(get_db)
):
    """Відправити відповіді на тест і отримати результат"""
    test = db.query(TestModel).filter(TestModel.id == test_id).first()
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    questions = db.query(Question).filter(Question.test_id == test_id).all()
    
    total_points = sum(q.points for q in questions)
    earned_points = 0
    
    for question in questions:
        question_id_str = str(question.id)
        user_answer = attempt_data.answers_data.get(question_id_str)
        
        if not user_answer:
            continue
        
        correct_answers = db.query(AnswerOption).filter(
            AnswerOption.question_id == question.id,
            AnswerOption.is_correct == True
        ).all()
        
        correct_answer_ids = {a.id for a in correct_answers}
        
        if isinstance(user_answer, list):
            user_answer_ids = set(user_answer)
            if user_answer_ids == correct_answer_ids:
                earned_points += question.points
        else:
            pass
    
    score = (earned_points / total_points * 100) if total_points > 0 else 0
    passed = score >= test.passing_score
    
    attempt = TestAttemptModel(
        user_id=current_user.id,
        test_id=test_id,
        score=score,
        passed=passed,
        completed_at=datetime.utcnow(),
        answers_data=attempt_data.answers_data
    )
    
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    
    return attempt


@router.get("/{test_id}/attempts", response_model=List[TestAttempt])
def get_my_test_attempts(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отримати мої спроби проходження тесту"""
    attempts = db.query(TestAttemptModel).filter(
        TestAttemptModel.test_id == test_id,
        TestAttemptModel.user_id == current_user.id
    ).order_by(TestAttemptModel.started_at.desc()).all()
    
    return attempts