from src.constants import Roles
from src.logger import logger
from src.models import HomeworkDAO, UserDAO
from src.routers.Homework.schemas import HomeworkGetSchema, HomeworkUpdateSchema


def serialize_homework(homework: HomeworkDAO) -> HomeworkGetSchema:
    """Convert a homework ORM object to API response schema."""
    lesson_id = homework.lesson.id if homework.lesson is not None else None
    return HomeworkGetSchema(
        id=homework.id,
        name=homework.name,
        description=homework.description,
        files_urls=homework.files_urls,
        answer=homework.answer,
        sent_files=homework.sent_files,
        deadline=homework.deadline,
        lesson_id=lesson_id,
        is_deleted=homework.is_deleted,
        updated_at=homework.updated_at,
        created_at=homework.created_at,
    )


def get_homework_filters(user: UserDAO) -> dict[str, str] | None:
    """Build homework visibility filters based on the current user's role."""
    if user.role == Roles.STUDENT:
        return {"student_id": user.id}

    if user.role == Roles.TEACHER:
        return {"teacher_id": user.id}

    return None


def get_homework_update_data(
    homework: HomeworkUpdateSchema,
    user: UserDAO,
) -> dict:
    """Prepare safe homework update payload from the request body."""
    if user.role == Roles.STUDENT:
        payload = homework.model_dump(
            exclude_unset=True,
            include={"answer", "sent_files"},
        )
    else:
        payload = homework.model_dump(
            exclude_unset=True,
            exclude={
                "lesson_id",
                "answer",
                "sent_files",
                "is_deleted",
                "updated_at",
                "created_at",
            },
        )

    logger.info(f"Prepared homework update payload: {payload}")
    return payload
