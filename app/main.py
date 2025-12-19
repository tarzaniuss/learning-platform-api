from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.api.v1 import auth, courses, lessons, enrollments, tests

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Learning Platform API",
    description="API для платформи онлайн-навчання",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(courses.router, prefix="/api/v1")
app.include_router(lessons.router, prefix="/api/v1")
app.include_router(enrollments.router, prefix="/api/v1")
app.include_router(tests.router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "message": "Learning Platform API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}