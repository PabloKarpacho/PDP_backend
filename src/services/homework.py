from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import Roles, role_matches
from src.logger import logger
from src.models import UserDAO
from src.routers.Homework.crud import create_homework as create_homework_record
from src.routers.Homework.crud import get_homework as get_homework_record
from src.routers.Homework.crud import list_homeworks as list_homeworks_records
from src.routers.Homework.crud import (
    soft_delete_homework as soft_delete_homework_record,
)
from src.routers.Homework.crud import update_homework as update_homework_record
from src.routers.Homework.schemas import (
    HomeworkCreateSchema,
    HomeworkGetSchema,
    HomeworkUpdateSchema,
)
from src.routers.Homework.utils import serialize_homework
from src.services.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)


def _get_homework_filters(user: UserDAO) -> dict[str, str] | None:
    if role_matches(user.role, Roles.STUDENT):
        logger.info(
            "Homework visibility resolved for student.",
            extra={"user_id": user.id},
        )
        return {"student_id": user.id}

    if role_matches(user.role, Roles.TEACHER):
        logger.info(
            "Homework visibility resolved for teacher.",
            extra={"user_id": user.id},
        )
        return {"teacher_id": user.id}

    logger.info(
        "Homework visibility could not be resolved for role.",
        extra={"user_id": user.id, "role": user.role},
    )
    return None


def _get_homework_update_data(homework: HomeworkUpdateSchema, user: UserDAO) -> dict:
    payload = homework.model_dump(exclude_unset=True)

    if role_matches(user.role, Roles.STUDENT):
        student_payload = {
            key: payload[key] for key in ("answer", "sent_files") if key in payload
        }
        logger.info(
            "Prepared homework update payload for student.",
            extra={
                "user_id": user.id,
                "fields": sorted(student_payload.keys()),
                "field_count": len(student_payload),
            },
        )
        return student_payload

    payload.pop("lesson_id", None)
    payload.pop("answer", None)
    payload.pop("sent_files", None)
    payload.pop("is_deleted", None)
    payload.pop("updated_at", None)
    payload.pop("created_at", None)
    logger.info(
        "Prepared homework update payload for teacher.",
        extra={
            "user_id": user.id,
            "fields": sorted(payload.keys()),
            "field_count": len(payload),
        },
    )
    return payload


async def list_homeworks_for_user(
    *,
    db: AsyncSession,
    user: UserDAO,
    lesson_id: int | None = None,
) -> list[HomeworkGetSchema]:
    logger.info(
        "Listing homeworks for user.",
        extra={"user_id": user.id, "role": user.role, "lesson_id": lesson_id},
    )
    homework_filters = _get_homework_filters(user)

    if homework_filters is None:
        logger.info(
            "No homework visibility filters available; returning empty result.",
            extra={"user_id": user.id},
        )
        return []

    homeworks = await list_homeworks_records(
        db,
        lesson_id=lesson_id,
        **homework_filters,
    )
    logger.info(
        "Homeworks listed successfully.",
        extra={"user_id": user.id, "homework_count": len(homeworks)},
    )
    return [serialize_homework(homework) for homework in homeworks]


async def get_homework_for_user(
    *,
    db: AsyncSession,
    homework_id: int,
    user: UserDAO,
) -> HomeworkGetSchema:
    logger.info(
        "Loading homework for user.",
        extra={"user_id": user.id, "homework_id": homework_id},
    )
    homework_filters = _get_homework_filters(user)

    if homework_filters is None:
        logger.error(
            "Homework access denied because visibility filters are unavailable.",
            extra={"user_id": user.id, "homework_id": homework_id},
        )
        raise ForbiddenError("Forbidden")

    homework = await get_homework_record(
        db,
        homework_id=homework_id,
        load_lesson=True,
        **homework_filters,
    )

    if homework is None:
        logger.error(
            "Homework not found for user.",
            extra={"user_id": user.id, "homework_id": homework_id},
        )
        raise NotFoundError("Homework not found")

    logger.info(
        "Homework loaded successfully.",
        extra={"user_id": user.id, "homework_id": homework_id},
    )
    return serialize_homework(homework)


async def create_homework_for_teacher(
    *,
    db: AsyncSession,
    user: UserDAO,
    homework: HomeworkCreateSchema,
) -> HomeworkGetSchema:
    if homework.lesson_id is None:
        logger.error(
            "Homework creation rejected because lesson_id is missing.",
            extra={"user_id": user.id},
        )
        raise ValidationError("lesson_id is required")

    logger.info(
        "Creating homework for teacher.",
        extra={"user_id": user.id, "lesson_id": homework.lesson_id},
    )
    try:
        homework_dao = await create_homework_record(
            db,
            lesson_id=homework.lesson_id,
            teacher_id=user.id,
            name=homework.name,
            description=homework.description,
            files_urls=homework.files_urls,
            answer=None,
            sent_files=None,
            deadline=homework.deadline,
        )
    except ValueError as error:
        logger.error(
            "Homework creation rejected by conflict.",
            extra={
                "user_id": user.id,
                "lesson_id": homework.lesson_id,
                "error_type": type(error).__name__,
            },
        )
        raise ConflictError(str(error)) from error

    if homework_dao is None:
        logger.error(
            "Homework creation failed because lesson was not found.",
            extra={"user_id": user.id, "lesson_id": homework.lesson_id},
        )
        raise NotFoundError("Lesson not found")

    logger.info(
        "Homework created for teacher.",
        extra={"user_id": user.id, "homework_id": homework_dao.id},
    )
    return serialize_homework(homework_dao)


async def update_homework_for_user(
    *,
    db: AsyncSession,
    homework_id: int,
    user: UserDAO,
    homework: HomeworkUpdateSchema,
) -> HomeworkGetSchema:
    logger.info(
        "Updating homework for user.",
        extra={"user_id": user.id, "homework_id": homework_id, "role": user.role},
    )
    homework_filters = _get_homework_filters(user)

    if homework_filters is None:
        logger.error(
            "Homework update forbidden because visibility filters are unavailable.",
            extra={"user_id": user.id, "homework_id": homework_id},
        )
        raise ForbiddenError("Forbidden")

    homework_dao = await update_homework_record(
        db,
        homework_id=homework_id,
        **homework_filters,
        **_get_homework_update_data(homework, user),
    )

    if homework_dao is None:
        logger.error(
            "Homework update target not found.",
            extra={"user_id": user.id, "homework_id": homework_id},
        )
        raise NotFoundError("Homework not found")

    logger.info(
        "Homework updated successfully.",
        extra={"user_id": user.id, "homework_id": homework_dao.id},
    )
    return serialize_homework(homework_dao)


async def delete_homework_for_teacher(
    *,
    db: AsyncSession,
    homework_id: int,
    user: UserDAO,
) -> int:
    logger.info(
        "Deleting homework for teacher.",
        extra={"user_id": user.id, "homework_id": homework_id},
    )
    homework_dao = await soft_delete_homework_record(
        db,
        homework_id=homework_id,
        teacher_id=user.id,
    )

    if homework_dao is None:
        logger.error(
            "Homework deletion target not found.",
            extra={"user_id": user.id, "homework_id": homework_id},
        )
        raise NotFoundError("Homework not found")

    logger.info(
        "Homework deleted successfully.",
        extra={"user_id": user.id, "homework_id": homework_dao.id},
    )
    return homework_dao.id
