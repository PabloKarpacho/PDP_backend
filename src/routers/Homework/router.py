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
)
async def get_homeworks(
    user: UserDAO = Depends(get_user),
    db: AsyncSession = Depends(get_db),
    lesson_id: int | None = None,
) -> ResponseEnvelope[list[HomeworkGetSchema]]:
    """
    ### Purpose
    List homework items visible to the current authenticated user.

    ### Access
    Available to authenticated teachers and students.

    ### Parameters
    - **user** (UserDAO): The current authenticated application user.
    - **db** (AsyncSession): Active database session.
    - **lesson_id** (int | None): Optional lesson identifier used to narrow the
    result set.

    ### Returns
    - **ResponseEnvelope[list[HomeworkGetSchema]]**: Homework records that the
    current teacher or student is allowed to access.
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
)
async def get_homework(
    homework_id: int,
    user: UserDAO = Depends(get_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[HomeworkGetSchema]:
    """
    ### Purpose
    Retrieve one homework item when the current user has access to it.

    ### Access
    Available to authenticated teachers and students when the homework belongs to
    an accessible lesson.

    ### Parameters
    - **homework_id** (int): Identifier of the homework item to load.
    - **user** (UserDAO): The current authenticated application user.
    - **db** (AsyncSession): Active database session.

    ### Returns
    - **ResponseEnvelope[HomeworkGetSchema]**: The requested homework item when it
    belongs to a lesson visible to the current user.
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
)
async def create_homework(
    homework: HomeworkCreateSchema,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[HomeworkGetSchema]:
    """
    ### Purpose
    Create homework for a lesson owned by the current teacher.

    ### Access
    Available only to authenticated teachers.

    ### Parameters
    - **homework** (HomeworkCreateSchema): Input payload describing the homework
    to create.
    - **user** (UserDAO): The current authenticated teacher.
    - **db** (AsyncSession): Active database session.

    ### Returns
    - **ResponseEnvelope[HomeworkGetSchema]**: The created homework item linked to
    the requested lesson.
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
)
async def update_homework(
    homework: HomeworkUpdateSchema,
    homework_id: int,
    user: UserDAO = Depends(get_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[HomeworkGetSchema]:
    """
    ### Purpose
    Update homework fields allowed for the current user role.

    ### Access
    Available to authenticated teachers and students, with role-based field
    restrictions.

    ### Parameters
    - **homework** (HomeworkUpdateSchema): Partial payload with fields to update.
    - **homework_id** (int): Identifier of the homework item to update.
    - **user** (UserDAO): The current authenticated application user.
    - **db** (AsyncSession): Active database session.

    ### Returns
    - **ResponseEnvelope[HomeworkGetSchema]**: The updated homework item after
    ownership checks and role-based field restrictions are applied.
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
)
async def delete_homework(
    homework_id: int,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[int]:
    """
    ### Purpose
    Soft-delete a homework item owned by the current teacher.

    ### Access
    Available only to authenticated teachers.

    ### Parameters
    - **homework_id** (int): Identifier of the homework item to delete.
    - **user** (UserDAO): The current authenticated teacher.
    - **db** (AsyncSession): Active database session.

    ### Returns
    - **ResponseEnvelope[int]**: The identifier of the homework item that was
    deleted.
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
