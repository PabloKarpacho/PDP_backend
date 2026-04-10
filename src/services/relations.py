from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import RelationStatuses, Roles, role_matches
from src.logger import logger
from src.models import UserDAO
from src.routers.Relations.crud import archive_relation as archive_relation_record
from src.routers.Relations.crud import create_relation as create_relation_record
from src.routers.Relations.crud import get_relation_by_id as get_relation_by_id_record
from src.routers.Relations.crud import (
    get_relation_by_pair as get_relation_by_pair_record,
)
from src.routers.Relations.crud import list_relations as list_relations_records
from src.routers.Relations.schemas import RelationGetSchema
from src.routers.Relations.utils import serialize_relation
from src.routers.Users.crud import get_user as get_user_record
from src.services.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)


async def ensure_active_relation(
    *,
    db: AsyncSession,
    teacher_id: str,
    student_id: str,
) -> RelationGetSchema:
    relation = await get_relation_by_pair_record(
        db,
        teacher_id=teacher_id,
        student_id=student_id,
    )

    if relation is None or relation.status != RelationStatuses.ACTIVE:
        logger.error(
            "Active teacher-student relation is missing.",
            extra={"teacher_id": teacher_id, "student_id": student_id},
        )
        raise ForbiddenError("Active teacher-student relation is required")

    return serialize_relation(relation)


async def create_relation_for_teacher(
    *,
    db: AsyncSession,
    user: UserDAO,
    student_id: str,
) -> RelationGetSchema:
    if user.id == student_id:
        raise ValidationError("teacher and student must be different users")

    existing_relation = await get_relation_by_pair_record(
        db,
        teacher_id=user.id,
        student_id=student_id,
    )
    if existing_relation is not None:
        raise ConflictError("Teacher-student relation already exists")

    student = await get_user_record(db, user_id=student_id)
    if student is None:
        raise NotFoundError("Student not found")
    if not role_matches(student.role, Roles.STUDENT):
        raise ValidationError("Relation target must be a student")

    relation = await create_relation_record(
        db,
        teacher_id=user.id,
        student_id=student_id,
        status=RelationStatuses.ACTIVE,
    )
    return serialize_relation(relation)


async def list_students_for_teacher(
    *,
    db: AsyncSession,
    user: UserDAO,
    include_archived: bool = False,
) -> list[RelationGetSchema]:
    relations = await list_relations_records(
        db,
        teacher_id=user.id,
        status=None if include_archived else RelationStatuses.ACTIVE,
    )
    return [serialize_relation(relation) for relation in relations]


async def list_teachers_for_student(
    *,
    db: AsyncSession,
    user: UserDAO,
    include_archived: bool = False,
) -> list[RelationGetSchema]:
    relations = await list_relations_records(
        db,
        student_id=user.id,
        status=None if include_archived else RelationStatuses.ACTIVE,
    )
    return [serialize_relation(relation) for relation in relations]


async def archive_relation_for_user(
    *,
    db: AsyncSession,
    relation_id: int,
    user: UserDAO,
) -> RelationGetSchema:
    relation = await get_relation_by_id_record(db, relation_id=relation_id)
    if relation is None:
        raise NotFoundError("Relation not found")

    if user.id not in {relation.teacher_id, relation.student_id}:
        raise ForbiddenError("Forbidden")

    archived_relation = await archive_relation_record(db, relation_id=relation_id)
    if archived_relation is None:
        raise NotFoundError("Relation not found")

    return serialize_relation(archived_relation)
