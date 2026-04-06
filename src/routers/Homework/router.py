from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database_control.postgres import get_db
from src.dependencies import get_teacher, get_user
from src.logger import logger
from src.models import UserDAO
from src.routers.Homework.schemas import (
    HomeworkCreateSchema,
    HomeworkGetSchema,
    HomeworkUpdateSchema,
)
from src.schemas import ResponseEnvelope, success_response
from src.services.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from src.services.homework import (
    create_homework_for_teacher,
    delete_homework_for_teacher,
    get_homework_for_user,
    list_homeworks_for_user,
    update_homework_for_user,
)


PREFIX = "/homeworks"

router = APIRouter(prefix=PREFIX, tags=["Homeworks"])


@router.get(
    "",
    response_model=ResponseEnvelope[list[HomeworkGetSchema]],
    summary="List visible homework items",
    description=(
        "Returns homework visible to the current authenticated user. "
        "Teachers see homework for their own lessons, students see homework "
        "assigned to them. The optional `lesson_id` filter narrows the list to "
        "one lesson when the user already has access to it."
    ),
    response_description="Homework list available to the current user.",
)
async def get_homeworks(
    user: UserDAO = Depends(get_user),
    db: AsyncSession = Depends(get_db),
    lesson_id: int | None = None,
) -> ResponseEnvelope[list[HomeworkGetSchema]]:
    """
    List homework items visible to the current authenticated user.

    Parameters:
    user (UserDAO): The current authenticated application user.
    db (AsyncSession): Active database session.
    lesson_id (int | None): Optional lesson identifier used to narrow the result set.

    Returns:
    ResponseEnvelope[list[HomeworkGetSchema]]: Homework records that the current
    teacher or student is allowed to access.
    """
    logger.info(
        "Homework list requested.",
        extra={
            "user_id": user.id,
            "role": user.role,
            "lesson_id": lesson_id,
        },
    )
    homeworks = await list_homeworks_for_user(
        db=db,
        user=user,
        lesson_id=lesson_id,
    )
    return success_response(homeworks)


@router.get(
    "/{homework_id}",
    response_model=ResponseEnvelope[HomeworkGetSchema],
    summary="Get homework details",
    description=(
        "Loads one homework item by identifier with ownership checks. "
        "The endpoint is available to authenticated teachers and students, but "
        "only if the homework belongs to a lesson they are allowed to access."
    ),
    response_description="One homework item visible to the current user.",
)
async def get_homework(
    homework_id: int,
    user: UserDAO = Depends(get_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[HomeworkGetSchema]:
    """
    Retrieve one homework item when the current user has access to it.

    Parameters:
    homework_id (int): Identifier of the homework item to load.
    user (UserDAO): The current authenticated application user.
    db (AsyncSession): Active database session.

    Returns:
    ResponseEnvelope[HomeworkGetSchema]: The requested homework item when it belongs
    to a lesson visible to the current user.
    """
    logger.info(
        "Homework detail requested.",
        extra={"user_id": user.id, "homework_id": homework_id},
    )
    try:
        homework_data = await get_homework_for_user(
            db=db,
            homework_id=homework_id,
            user=user,
        )
        logger.info(
            "Homework detail loaded successfully.",
            extra={"user_id": user.id, "homework_id": homework_id},
        )
        return success_response(homework_data)
    except ForbiddenError:
        logger.error(
            "Homework access forbidden.",
            extra={"user_id": user.id, "homework_id": homework_id},
        )
        raise HTTPException(403, "Forbidden")
    except NotFoundError:
        logger.error(
            "Homework detail not found.",
            extra={"user_id": user.id, "homework_id": homework_id},
        )
        raise HTTPException(404, "Homework not found")


@router.post(
    "/create",
    response_model=ResponseEnvelope[HomeworkGetSchema],
    summary="Create homework for lesson",
    description=(
        "Creates a new homework item for a teacher-owned lesson. "
        "The caller must be a teacher, the lesson must exist, and the "
        "teacher-student relation behind that lesson must still be active. "
        "The endpoint rejects duplicate homework for the same lesson."
    ),
    response_description="Created homework item bound to the requested lesson.",
)
async def create_homework(
    homework: HomeworkCreateSchema,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[HomeworkGetSchema]:
    """
    Create homework for a lesson owned by the current teacher.

    Parameters:
    homework (HomeworkCreateSchema): Input payload describing the homework to create.
    user (UserDAO): The current authenticated teacher.
    db (AsyncSession): Active database session.

    Returns:
    ResponseEnvelope[HomeworkGetSchema]: The created homework item linked to the
    requested lesson.
    """
    logger.info(
        "Homework creation requested.",
        extra={
            "user_id": user.id,
            "lesson_id": homework.lesson_id,
        },
    )
    try:
        homework_data = await create_homework_for_teacher(
            db=db,
            user=user,
            homework=homework,
        )
        logger.info(
            "Homework created successfully.",
            extra={
                "user_id": user.id,
                "homework_id": getattr(homework_data, "id", None),
            },
        )
        return success_response(homework_data)
    except ValidationError as error:
        logger.error(
            "Homework creation rejected by validation.",
            extra={"user_id": user.id, "error_type": type(error).__name__},
        )
        raise HTTPException(400, str(error)) from error
    except ForbiddenError as error:
        logger.error(
            "Homework creation forbidden by relation policy.",
            extra={"user_id": user.id, "lesson_id": homework.lesson_id},
        )
        raise HTTPException(403, str(error)) from error
    except ConflictError as error:
        logger.error(
            "Homework creation rejected by conflict.",
            extra={"user_id": user.id, "error_type": type(error).__name__},
        )
        raise HTTPException(409, str(error)) from error
    except NotFoundError as error:
        logger.error(
            "Homework creation failed because lesson was not found.",
            extra={"user_id": user.id, "lesson_id": homework.lesson_id},
        )
        raise HTTPException(404, "Lesson not found") from error


@router.put(
    "/update/{homework_id}",
    response_model=ResponseEnvelope[HomeworkGetSchema],
    summary="Update homework",
    description=(
        "Updates one homework item with role-aware rules. "
        "Teachers can edit teacher-managed fields such as description, files and "
        "deadline for homework linked to their lessons. Students can update only "
        "their answer and submitted files for homework visible to them."
    ),
    response_description="Updated homework item after ownership and validation checks.",
)
async def update_homework(
    homework: HomeworkUpdateSchema,
    homework_id: int,
    user: UserDAO = Depends(get_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[HomeworkGetSchema]:
    """
    Update homework fields allowed for the current user role.

    Parameters:
    homework (HomeworkUpdateSchema): Partial payload with fields to update.
    homework_id (int): Identifier of the homework item to update.
    user (UserDAO): The current authenticated application user.
    db (AsyncSession): Active database session.

    Returns:
    ResponseEnvelope[HomeworkGetSchema]: The updated homework item after ownership
    checks and role-based field restrictions are applied.
    """
    logger.info(
        "Homework update requested.",
        extra={
            "user_id": user.id,
            "homework_id": homework_id,
            "fields": sorted(homework.model_dump(exclude_unset=True).keys()),
        },
    )
    try:
        homework_data = await update_homework_for_user(
            db=db,
            homework_id=homework_id,
            user=user,
            homework=homework,
        )
        logger.info(
            "Homework updated successfully.",
            extra={
                "user_id": user.id,
                "homework_id": getattr(homework_data, "id", homework_id),
            },
        )
        return success_response(homework_data)
    except ForbiddenError as error:
        logger.error(
            "Homework update forbidden.",
            extra={"user_id": user.id, "homework_id": homework_id},
        )
        raise HTTPException(403, "Forbidden") from error
    except NotFoundError as error:
        logger.error(
            "Homework update failed because homework was not found.",
            extra={"user_id": user.id, "homework_id": homework_id},
        )
        raise HTTPException(404, "Homework not found") from error


@router.delete(
    "/delete/{homework_id}",
    response_model=ResponseEnvelope[int],
    summary="Delete homework",
    description=(
        "Soft-deletes a homework item owned by the current teacher. "
        "This endpoint is intentionally teacher-only because homework lifecycle "
        "and assignment rules are controlled from the teaching side."
    ),
    response_description="Identifier of the homework item that was deleted.",
)
async def delete_homework(
    homework_id: int,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[int]:
    """
    Soft-delete a homework item owned by the current teacher.

    Parameters:
    homework_id (int): Identifier of the homework item to delete.
    user (UserDAO): The current authenticated teacher.
    db (AsyncSession): Active database session.

    Returns:
    ResponseEnvelope[int]: The identifier of the homework item that was deleted.
    """
    logger.info(
        "Homework deletion requested.",
        extra={"user_id": user.id, "homework_id": homework_id},
    )
    try:
        homework_id_result = await delete_homework_for_teacher(
            db=db,
            homework_id=homework_id,
            user=user,
        )
        logger.info(
            "Homework deleted successfully.",
            extra={"user_id": user.id, "homework_id": homework_id_result},
        )
        return success_response(homework_id_result)
    except NotFoundError as error:
        logger.error(
            "Homework deletion failed because homework was not found.",
            extra={"user_id": user.id, "homework_id": homework_id},
        )
        raise HTTPException(404, "Homework not found") from error
