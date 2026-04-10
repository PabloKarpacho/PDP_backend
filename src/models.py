from typing import List
from datetime import datetime
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class UserDAO(Base):
    __tablename__ = "users"

    id: Mapped[str] = Column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = Column(String, nullable=False)
    surname: Mapped[str] = Column(String, nullable=True)
    email: Mapped[str] = Column(String, unique=True, nullable=False)
    role: Mapped[str] = Column(String, nullable=False)

    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), default=func.now())


class TeachersStudentsDAO(Base):
    __tablename__ = "teachers_students"
    __table_args__ = (
        UniqueConstraint(
            "teacher_id",
            "student_id",
            name="uq_teachers_students_teacher_student",
        ),
        CheckConstraint(
            "teacher_id <> student_id",
            name="ck_teachers_students_not_self",
        ),
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_teachers_students_status",
        ),
        CheckConstraint(
            "(status = 'active' AND archived_at IS NULL) OR "
            "(status = 'archived' AND archived_at IS NOT NULL)",
            name="ck_teachers_students_archived_at_matches_status",
        ),
        Index("ix_teachers_students_teacher_id_status", "teacher_id", "status"),
        Index("ix_teachers_students_student_id_status", "student_id", "status"),
    )

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[str] = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[str] = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = Column(String, nullable=False, default="active")
    archived_at: Mapped[datetime | None] = Column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), default=func.now())


class LessonDAO(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        UniqueConstraint("homework_id", name="uq_lessons_homework_id"),
        Index("ix_lessons_teacher_id_start_time", "teacher_id", "start_time"),
        Index("ix_lessons_student_id_start_time", "student_id", "start_time"),
    )

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    start_time: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False)
    theme: Mapped[str] = Column(String, nullable=True)
    lesson_description: Mapped[str] = Column(String, nullable=True)

    teacher_id: Mapped[str] = Column(
        String,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    student_id: Mapped[str] = Column(
        String,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    status: Mapped[str] = Column(String, nullable=False, default="active")

    homework_id: Mapped[int] = Column(
        Integer,
        ForeignKey("homeworks.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_deleted: Mapped[bool] = Column(Boolean, default=False)

    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), default=func.now())

    homework = relationship(
        "HomeworkDAO",
        back_populates="lesson",
        foreign_keys=[homework_id],
        uselist=False,
    )


class HomeworkDAO(Base):
    __tablename__ = "homeworks"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = Column(String, nullable=True)
    description: Mapped[str] = Column(String, nullable=True)
    files_urls: Mapped[List] = Column(JSON, nullable=True)
    answer: Mapped[str] = Column(String, nullable=True)
    sent_files: Mapped[List] = Column(JSON, nullable=True)
    deadline: Mapped[datetime] = Column(DateTime(timezone=True), nullable=True)

    is_deleted: Mapped[bool] = Column(Boolean, default=False)

    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), default=func.now())

    lesson = relationship(
        "LessonDAO",
        back_populates="homework",
        foreign_keys="LessonDAO.homework_id",
        uselist=False,
    )
