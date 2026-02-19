# Learning Platform API

#### Description:

This project is a REST API for an online learning platform built with FastAPI and fully asynchronous database access via SQLAlchemy. The goal was to create a complete backend that covers the entire learning lifecycle: from registration and browsing the course catalog to completing lessons, taking tests, and tracking progress. I deliberately chose an async stack with asyncpg so the API can handle concurrent load without blocking.

The system supports three roles: student, instructor, and admin. Each role has a clearly scoped set of permissions — for example, only an instructor can create courses and lessons, and only their own. Authorization is implemented via JWT tokens, and passwords are protected with double hashing (SHA-256 + bcrypt) for compatibility across different versions of the bcrypt library.

## Project Structure

**app/main.py** — the FastAPI application entry point. All routers are registered here, CORS middleware is configured, and the admin panel is connected. The lifespan manager handles table initialization on startup and graceful connection disposal on shutdown.

**app/config.py** — configuration via Pydantic Settings. All sensitive settings (DATABASE_URL, SECRET_KEY, token parameters) are loaded from a `.env` file, making it easy to deploy in different environments without changing any code.

**app/database.py** — async SQLAlchemy engine initialization with asyncpg. This file also defines the `Base` class for all models and the `get_db` function for session injection via FastAPI's `Depends`. If the DATABASE_URL is provided in the `postgresql://` format, it is automatically converted to `postgresql+asyncpg://`.

### API Endpoints (app/api/)

**api/deps.py** — FastAPI dependencies used throughout the project. `get_current_user` decodes the JWT and fetches the current user from the database. On top of it, `get_current_active_instructor` and `get_current_active_admin` check the user's role and raise a 403 if permissions are insufficient. I extracted these into a separate file to avoid duplication across every router and to have a single place to change authorization logic.

**api/v1/auth.py** — registration, login, and retrieving current user info. On registration, email uniqueness is checked; on login, the password is verified. A Bearer token is returned on successful login.

**api/v1/courses.py** — CRUD for courses. The public course list is available to all authenticated users, but each response also includes an `is_enrolled` flag indicating whether the current user is enrolled. Creating, editing, and deleting courses is restricted to the instructor who owns them. I explicitly check `instructor_id != current_user.id` on write operations so instructors cannot modify each other's courses.

**api/v1/lessons.py** — CRUD for lessons and completion tracking. Each lesson is returned with an `is_completed` flag for the current student. The `POST /{lesson_id}/complete` endpoint marks a lesson as done and automatically recalculates `progress_percentage` in the enrollment record. If progress reaches 100%, the `completed_at` field in the enrollment is populated with the current timestamp.

**api/v1/enrollments.py** — course enrollment and progress tracking. A student can only enroll in a published course and cannot enroll twice (enforced by a UniqueConstraint at the database level). The `GET /course/{course_id}/progress` endpoint returns detailed stats: number of completed lessons, percentage, and completion date.

**api/v1/tests.py** — test management and submission. An instructor can create a test for a lesson with questions of type `single_choice`, `multiple_choice`, or `text`. When a student submits an attempt, the system scores only questions with answer options (text questions are not graded automatically), determines whether the passing score was reached, and if so — automatically marks the lesson as completed and updates the course progress.

### Core (app/core/)

**core/security.py** — all security-related logic: password hashing, password verification, and JWT operations. Before bcrypt hashing, passwords are first run through SHA-256 — this resolves a compatibility issue between passlib and certain bcrypt versions where long passwords could be processed incorrectly.

### Database Models (app/models/)

**models/user.py** — user model with a `student / instructor / admin` role enum.

**models/course.py** — course model with difficulty levels (`beginner / intermediate / advanced`), category, duration, and a publication flag.

**models/enrollment.py** — student enrollment in a course. Stores progress percentage and completion date. A UniqueConstraint ensures a student cannot enroll in the same course twice.

**models/lesson.py** — a course lesson with an `order_index` field for controlling display order.

**models/lesson_completion.py** — a record of a specific lesson being completed by a specific student.

**models/test.py** — four interrelated models: `Test`, `Question`, `AnswerOption`, and `TestAttempt`. `TestAttempt` stores student answers as JSON, which allows saving answers of arbitrary structure without schema changes.

### Schemas (app/schemas/)

Pydantic schemas for input validation and response serialization. Split into `*Create`, `*Update`, and `*Read` variants for each entity, allowing precise control over which fields are accepted and which are returned.

### Admin Panel (app/admin/)

**admin/setup.py** and **admin/views.py** — SQLAdmin integration for convenient in-browser data viewing and editing. The panel is available at `/admin` and currently runs without authentication (Dev Mode), which is fine for development but needs to be secured before any production deployment.

### Migrations (alembic/)

Alembic for database schema management. The file `alembic/versions/59e48d6e4370_initial.py` contains the initial migration that creates all tables. `env.py` is configured to work with the async engine.

### Tests (tests/)

**tests/conftest.py** — fixtures for the test environment. All tables are created before the test session starts and dropped after it ends. Each test runs in an isolated state thanks to the `clean_tables` fixture, which clears all tables after every test. Pre-built `student_client` and `instructor_client` fixtures are available for authorized requests — they override the `get_current_user` dependency via `dependency_overrides`, so no real JWT token needs to be passed in tests.

**tests/test_auth.py**, **test_courses.py**, **test_enrollments.py**, **test_lessons.py** — integration tests for each API module, written with pytest-asyncio and HTTPX AsyncClient.

## Tech Stack

- **FastAPI** — web framework
- **SQLAlchemy (async)** + **asyncpg** — async ORM and PostgreSQL driver
- **Alembic** — database migrations
- **Pydantic v2** + **pydantic-settings** — data validation and configuration
- **python-jose** — JWT generation and verification
- **passlib** + **bcrypt** — password hashing
- **SQLAdmin** — admin panel
- **pytest** + **pytest-asyncio** + **HTTPX** — testing

## Design Choices

The most impactful architectural decision was going fully async. This made test setup more involved — the standard `TestClient` doesn't work with async code, so HTTPX with `ASGITransport` is used instead — but the tradeoff is worth it: the API can serve many concurrent requests without thread blocking.

The three-tier role model (student / instructor / admin) combined with resource ownership checks (instructors can only edit their own courses) makes the system easy to extend without rewriting authorization logic.

I chose to implement automatic progress updates triggered by test submissions at the business logic layer inside the endpoint, rather than through database triggers. This keeps the behavior explicit and straightforward to test.
