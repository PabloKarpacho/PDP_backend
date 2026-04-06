import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import UserDAO
from src.database_control.postgres import get_db
from src.dependencies import get_user, get_teacher
from src.logger import logger
from src.routers.Lessons.schemas import (
    LessonGetSchema,
    LessonCreateSchema,
    LessonUpdateSchema,
)
from src.schemas import ResponseEnvelope, success_response
from src.services.exceptions import ForbiddenError, NotFoundError, ValidationError
from src.services.lessons import (
    create_lesson_for_teacher,
    delete_lesson_for_teacher,
    list_lessons_for_user,
    update_lesson_for_teacher,
)


PREFIX = "/lessons"

router = APIRouter(prefix=PREFIX, tags=["Lessons"])


@router.get(
    "",
    response_model=ResponseEnvelope[list[LessonGetSchema]],
    summary="List visible lessons",
    description=(
        "Returns lessons available to the current authenticated user. "
        "Teachers see their own lessons, students see lessons assigned to them. "
        "Optional `start_time` and `end_time` parameters can be used to narrow "
        "the result set to a time window."
    ),
    response_description="Lesson list visible to the current user.",
)
async def get_lessons(
    user: UserDAO = Depends(get_user),
    db: AsyncSession = Depends(get_db),
    start_time: datetime.datetime | None = None,
    end_time: datetime.datetime | None = None,
) -> ResponseEnvelope[list[LessonGetSchema]]:
    """
    List lessons visible to the current authenticated user.

    Parameters:
    user (UserDAO): The current authenticated application user.
    db (AsyncSession): Active database session.
    start_time (datetime.datetime | None): Optional lower bound for lesson start time.
    end_time (datetime.datetime | None): Optional upper bound for lesson end time.

    Returns:
    ResponseEnvelope[list[LessonGetSchema]]: Lessons available to the current
    teacher or student, optionally filtered by the requested time window.
    """
    logger.info(
        "Lessons list requested.",
        extra={
            "user_id": user.id,
            "role": user.role,
            "has_start_time_filter": start_time is not None,
            "has_end_time_filter": end_time is not None,
        },
    )
    lessons = await list_lessons_for_user(
        db=db,
        user=user,
        start_time=start_time,
        end_time=end_time,
    )
    return success_response(lessons)


@router.post(
    "/create",
    response_model=ResponseEnvelope[LessonGetSchema],
    summary="Create lesson",
    description=(
        "Creates a new lesson for the current teacher and the requested student. "
        "The endpoint validates the lesson payload, enforces the teacher role and "
        "requires an active teacher-student relation before the lesson can be scheduled."
    ),
    response_description="Created lesson record.",
)
async def create_lesson(
    lesson: LessonCreateSchema,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[LessonGetSchema]:
    """
    Create a lesson for the current authenticated teacher.

    Parameters:
    lesson (LessonCreateSchema): Input payload describing the lesson to schedule.
    user (UserDAO): The current authenticated teacher.
    db (AsyncSession): Active database session.

    Returns:
    ResponseEnvelope[LessonGetSchema]: The created lesson after validation and
    teacher-student relation checks succeed.
    """
    logger.info(
        "Lesson creation requested.",
        extra={
            "user_id": user.id,
            "student_id": lesson.student_id,
            "status": lesson.status,
        },
    )
    try:
        lesson_data = await create_lesson_for_teacher(db=db, user=user, lesson=lesson)
        logger.info(
            "Lesson created successfully.",
            extra={"user_id": user.id, "lesson_id": lesson_data.id},
        )
        return success_response(lesson_data)
    except ValidationError as error:
        logger.error(
            "Lesson creation rejected by validation.",
            extra={"user_id": user.id, "error_type": type(error).__name__},
        )
        raise HTTPException(400, str(error)) from error
    except ForbiddenError as error:
        logger.error(
            "Lesson creation forbidden by relation policy.",
            extra={"user_id": user.id, "student_id": lesson.student_id},
        )
        raise HTTPException(403, str(error)) from error


@router.put(
    "/update/{lesson_id}",
    response_model=ResponseEnvelope[LessonGetSchema],
    summary="Update lesson",
    description=(
        "Updates one lesson owned by the current teacher. "
        "The endpoint enforces lesson status transitions, validates the effective "
        "time range and, when the student is changed, checks that an active "
        "teacher-student relation exists for the new pair."
    ),
    response_description="Updated lesson record.",
)
async def update_lesson(
    lesson: LessonUpdateSchema,
    lesson_id: int,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[LessonGetSchema]:
    """
    Update one lesson owned by the current authenticated teacher.

    Parameters:
    lesson (LessonUpdateSchema): Partial lesson payload with fields to change.
    lesson_id (int): Identifier of the lesson to update.
    user (UserDAO): The current authenticated teacher.
    db (AsyncSession): Active database session.

    Returns:
    ResponseEnvelope[LessonGetSchema]: The updated lesson record after validation,
    ownership checks and status transition rules are applied.
    """
    logger.info(
        "Lesson update requested.",
        extra={
            "user_id": user.id,
            "lesson_id": lesson_id,
            "fields": sorted(lesson.model_dump(exclude_unset=True).keys()),
        },
    )
    try:
        lesson_data = await update_lesson_for_teacher(
            db=db,
            lesson_id=lesson_id,
            user=user,
            lesson=lesson,
        )
        logger.info(
            "Lesson updated successfully.",
            extra={"user_id": user.id, "lesson_id": lesson_data.id},
        )
        return success_response(lesson_data)
    except NotFoundError:
        logger.error(
            "Lesson update failed because lesson was not found.",
            extra={"user_id": user.id, "lesson_id": lesson_id},
        )
        raise HTTPException(404, "Lesson not found")
    except ValidationError as error:
        logger.error(
            "Lesson update rejected by validation.",
            extra={
                "user_id": user.id,
                "lesson_id": lesson_id,
                "error_type": type(error).__name__,
            },
        )
        raise HTTPException(400, str(error)) from error
    except ForbiddenError as error:
        logger.error(
            "Lesson update forbidden by relation policy.",
            extra={"user_id": user.id, "lesson_id": lesson_id},
        )
        raise HTTPException(403, str(error)) from error


@router.delete(
    "/delete/{lesson_id}",
    response_model=ResponseEnvelope[int],
    summary="Delete lesson",
    description=(
        "Soft-deletes a lesson owned by the current teacher. "
        "The operation removes the lesson from normal visibility while preserving "
        "the identifier for audit-friendly workflows and related domain cleanup."
    ),
    response_description="Identifier of the lesson that was deleted.",
)
async def delete_lesson(
    lesson_id: int,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[int]:
    """
    Soft-delete a lesson owned by the current authenticated teacher.

    Parameters:
    lesson_id (int): Identifier of the lesson to delete.
    user (UserDAO): The current authenticated teacher.
    db (AsyncSession): Active database session.

    Returns:
    ResponseEnvelope[int]: The identifier of the lesson that was deleted.
    """
    logger.info(
        "Lesson deletion requested.",
        extra={"user_id": user.id, "lesson_id": lesson_id},
    )
    try:
        lesson_id_result = await delete_lesson_for_teacher(
            db=db,
            lesson_id=lesson_id,
            user=user,
        )
        logger.info(
            "Lesson deleted successfully.",
            extra={"user_id": user.id, "lesson_id": lesson_id_result},
        )
        return success_response(lesson_id_result)
    except NotFoundError:
        logger.error(
            "Lesson deletion failed because lesson was not found.",
            extra={"user_id": user.id, "lesson_id": lesson_id},
        )
        raise HTTPException(404, "Lesson not found")
