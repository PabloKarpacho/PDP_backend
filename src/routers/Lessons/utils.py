from src.constants import Roles
from src.logger import logger
from src.models import LessonDAO, UserDAO
from src.routers.Lessons.schemas import LessonGetSchema, LessonUpdateSchema


def serialize_lesson(lesson: LessonDAO) -> LessonGetSchema:
    """Convert a lesson ORM object to API response schema.

    Args:
        lesson: Lesson ORM object from the database.

    Returns:
        Serialized lesson response schema.
    """
    return LessonGetSchema(
        id=lesson.id,
        start_time=lesson.start_time,
        end_time=lesson.end_time,
        theme=lesson.theme,
        lesson_description=lesson.lesson_description,
        teacher_id=lesson.teacher_id,
        student_id=lesson.student_id,
        status=lesson.status,
        homework_id=lesson.homework_id,
        is_deleted=lesson.is_deleted,
        updated_at=lesson.updated_at,
        created_at=lesson.created_at,
    )


def get_lesson_filters(user: UserDAO) -> dict[str, str] | None:
    """Build lesson visibility filters based on the current user's role.

    Args:
        user: Current authenticated application user.

    Returns:
        Dictionary with ownership filters for teacher or student,
        or None when the role has no access to lessons.
    """
    if user.role == Roles.STUDENT:
        return {"student_id": user.id}

    if user.role == Roles.TEACHER:
        return {"teacher_id": user.id}

    return None


def get_lesson_update_data(lesson: LessonUpdateSchema) -> dict:
    """Prepare safe lesson update payload from the request body.

    Args:
        lesson: Incoming lesson update schema.

    Returns:
        Dictionary with mutable lesson fields only.
    """
    payload = lesson.model_dump(
        exclude_unset=True,
        exclude={"teacher_id", "is_deleted", "updated_at", "created_at"},
    )
    logger.info(f"Prepared lesson update payload: {payload}")
    return payload
