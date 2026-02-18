from typing import List

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentInstructor, CurrentUser, DbSession
from app.models.course import Course as CourseModel
from app.models.enrollment import Enrollment as EnrollmentModel
from app.schemas.course import CourseCreate, CourseRead, CourseUpdate

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get("/", response_model=List[CourseRead])
async def get_courses(
    skip: int = 0,
    limit: int = 100,
    is_published: bool = True,
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    """Get a list of courses (catalog)"""

    stmt = select(CourseModel)
    if is_published:
        stmt = stmt.where(CourseModel.is_published)

    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    courses = result.scalars().all()

    enrolled_course_ids = set()
    if current_user:
        enrollment_stmt = select(EnrollmentModel.course_id).where(
            EnrollmentModel.user_id == current_user.id
        )
        enrollment_result = await db.execute(enrollment_stmt)
        enrolled_course_ids = {
            course_id for course_id in enrollment_result.scalars().all()
        }

    for course in courses:
        course.is_enrolled = course.id in enrolled_course_ids

    return courses


@router.get("/{course_id}", response_model=CourseRead)
async def get_course(
    course_id: int,
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    """Get course details by ID"""

    stmt = select(CourseModel).where(CourseModel.id == course_id)
    result = await db.execute(stmt)
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    is_enrolled = False
    if current_user:
        enrollment_stmt = select(EnrollmentModel).where(
            EnrollmentModel.user_id == current_user.id,
            EnrollmentModel.course_id == course_id,
        )
        enrollment_result = await db.execute(enrollment_stmt)
        is_enrolled = enrollment_result.scalar_one_or_none() is not None

    course.is_enrolled = is_enrolled

    return course


@router.post("/", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(
    course_data: CourseCreate,
    current_user: CurrentInstructor = None,
    db: DbSession = None,
):
    """Create a new course (instructors only)"""

    db_course = CourseModel(**course_data.model_dump(), instructor_id=current_user.id)

    db.add(db_course)
    await db.commit()
    await db.refresh(db_course)

    return db_course


@router.put("/{course_id}", response_model=CourseRead)
async def update_course(
    course_id: int,
    course_data: CourseUpdate,
    current_user: CurrentInstructor = None,
    db: DbSession = None,
):
    """Update an existing course"""

    stmt = select(CourseModel).where(CourseModel.id == course_id)
    result = await db.execute(stmt)
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    if course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    update_data = course_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(course, field, value)

    await db.commit()
    await db.refresh(course)

    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: int,
    current_user: CurrentInstructor = None,
    db: DbSession = None,
):
    """Delete a course"""

    stmt = select(CourseModel).where(CourseModel.id == course_id)
    result = await db.execute(stmt)
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    if course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    await db.delete(course)
    await db.commit()

    return None
