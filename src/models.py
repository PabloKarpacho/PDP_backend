from typing import List
from datetime import datetime
import uuid

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum,
    ForeignKey,
    Text,
    Table,
    UniqueConstraint,
    DateTime,
    Boolean,
    text,
    func,
    JSON,
    TIMESTAMP,
)
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.selectable import TypedReturnsRows

Base = declarative_base()


class UserDAO(Base):
    __tablename__ = "users"

    id: Mapped[str] = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = Column(String, nullable=False)
    surname: Mapped[str] = Column(String, nullable=True)
    email: Mapped[str] = Column(String, unique=True, nullable=False)
    role: Mapped[str] = Column(String, nullable=False)

    updated_at: Mapped[datetime] = Column(
        DateTime, default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = Column(DateTime, default=func.now())


class TeachersStudentsDAO(Base):
    __tablename__ = "teachers_students"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = Column(Integer, nullable=False)
    student_id: Mapped[int] = Column(Integer, nullable=False)


class LessonDAO(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    start_time: Mapped[datetime] = Column(DateTime, nullable=False)
    end_time: Mapped[datetime] = Column(DateTime, nullable=False)
    theme: Mapped[str] = Column(String, nullable=True)
    lesson_description: Mapped[str] = Column(String, nullable=True)

    teacher_id: Mapped[str] = Column(String, nullable=False)
    student_id: Mapped[str] = Column(String, nullable=False)

    status: Mapped[str] = Column(String, nullable=False, default="active")

    homework_id : Mapped[int] = Column(
        Integer, ForeignKey("homeworks.id", ondelete="CASCADE"), nullable=True
    )

    is_deleted: Mapped[bool] = Column(Boolean, default=False)

    updated_at: Mapped[datetime] = Column(
        DateTime, default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = Column(DateTime, default=func.now())

    homework = relationship("HomeworkDAO", back_populates="lesson", uselist=False)


class HomeworkDAO(Base):
    __tablename__ = "homeworks"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = Column(String, nullable=True)
    description: Mapped[str] = Column(String, nullable=True)
    files_urls: Mapped[List] = Column(JSON, nullable=True)
    answer: Mapped[str] = Column(String, nullable=True)
    sent_files: Mapped[List] = Column(JSON, nullable=True)
    deadline: Mapped[datetime] = Column(DateTime, nullable=True)

    is_deleted: Mapped[bool] = Column(Boolean, default=False)

    updated_at: Mapped[datetime] = Column(
        DateTime, default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = Column(DateTime, default=func.now())

    lesson = relationship("LessonDAO", back_populates="homework", uselist=False)
