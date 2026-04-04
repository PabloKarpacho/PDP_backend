from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import Roles, role_matches
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
        return {"student_id": user.id}

    if role_matches(user.role, Roles.TEACHER):
        return {"teacher_id": user.id}

    return None


def _get_homework_update_data(homework: HomeworkUpdateSchema, user: UserDAO) -> dict:
    payload = homework.model_dump(exclude_unset=True)

    if role_matches(user.role, Roles.STUDENT):
        return {key: payload[key] for key in ("answer", "sent_files") if key in payload}

    payload.pop("lesson_id", None)
    payload.pop("answer", None)
    payload.pop("sent_files", None)
    payload.pop("is_deleted", None)
    payload.pop("updated_at", None)
    payload.pop("created_at", None)
    return payload


async def list_homeworks_for_user(
    *,
    db: AsyncSession,
    user: UserDAO,
    lesson_id: int | None = None,
) -> list[HomeworkGetSchema]:
    homework_filters = _get_homework_filters(user)

    if homework_filters is None:
        return []

    homeworks = await list_homeworks_records(
        db,
        lesson_id=lesson_id,
        **homework_filters,
    )
    return [serialize_homework(homework) for homework in homeworks]


async def get_homework_for_user(
    *,
    db: AsyncSession,
    homework_id: int,
    user: UserDAO,
) -> HomeworkGetSchema:
    homework_filters = _get_homework_filters(user)

    if homework_filters is None:
        raise ForbiddenError("Forbidden")

    homework = await get_homework_record(
        db,
        homework_id=homework_id,
        load_lesson=True,
        **homework_filters,
    )

    if homework is None:
        raise NotFoundError("Homework not found")

    return serialize_homework(homework)


async def create_homework_for_teacher(
    *,
    db: AsyncSession,
    user: UserDAO,
    homework: HomeworkCreateSchema,
) -> HomeworkGetSchema:
    if homework.lesson_id is None:
        raise ValidationError("lesson_id is required")

    try:
        homework_dao = await create_homework_record(
            db,
            lesson_id=homework.lesson_id,
            teacher_id=user.id,
            name=homework.name,
            description=homework.description,
            files_urls=homework.files_urls,
            answer=homework.answer,
            sent_files=homework.sent_files,
            deadline=homework.deadline,
        )
    except ValueError as error:
        raise ConflictError(str(error)) from error

    if homework_dao is None:
        raise NotFoundError("Lesson not found")

    return serialize_homework(homework_dao)


async def update_homework_for_user(
    *,
    db: AsyncSession,
    homework_id: int,
    user: UserDAO,
    homework: HomeworkUpdateSchema,
) -> HomeworkGetSchema:
    homework_filters = _get_homework_filters(user)

    if homework_filters is None:
        raise ForbiddenError("Forbidden")

    homework_dao = await update_homework_record(
        db,
        homework_id=homework_id,
        **homework_filters,
        **_get_homework_update_data(homework, user),
    )

    if homework_dao is None:
        raise NotFoundError("Homework not found")

    return serialize_homework(homework_dao)


async def delete_homework_for_teacher(
    *,
    db: AsyncSession,
    homework_id: int,
    user: UserDAO,
) -> int:
    homework_dao = await soft_delete_homework_record(
        db,
        homework_id=homework_id,
        teacher_id=user.id,
    )

    if homework_dao is None:
        raise NotFoundError("Homework not found")

    return homework_dao.id
