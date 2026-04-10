from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.logger import logger
from src.models import TeachersStudentsDAO


async def create_relation(
    db: AsyncSession,
    *,
    teacher_id: str,
    student_id: str,
    status: str,
) -> TeachersStudentsDAO:
    logger.info(
        "Creating teacher-student relation in database.",
        extra={
            "teacher_id": teacher_id,
            "student_id": student_id,
            "status": status,
        },
    )
    relation = TeachersStudentsDAO(
        teacher_id=teacher_id,
        student_id=student_id,
        status=status,
        archived_at=None,
    )
    db.add(relation)
    await db.commit()
    await db.refresh(relation)
    logger.info(
        "Teacher-student relation created in database.",
        extra={"relation_id": relation.id},
    )
    return relation


async def list_relations(
    db: AsyncSession,
    *,
    teacher_id: str | None = None,
    student_id: str | None = None,
    status: str | None = None,
) -> list[TeachersStudentsDAO]:
    logger.info(
        "Listing teacher-student relations from database.",
        extra={
            "teacher_id": teacher_id,
            "student_id": student_id,
            "status": status,
        },
    )
    statement = select(TeachersStudentsDAO)

    if teacher_id is not None:
        statement = statement.where(TeachersStudentsDAO.teacher_id == teacher_id)

    if student_id is not None:
        statement = statement.where(TeachersStudentsDAO.student_id == student_id)

    if status is not None:
        statement = statement.where(TeachersStudentsDAO.status == status)

    statement = statement.order_by(TeachersStudentsDAO.created_at.desc())
    result = await db.execute(statement)
    relations = list(result.scalars().all())
    logger.info(
        "Teacher-student relation list query completed.",
        extra={"result_count": len(relations)},
    )
    return relations


async def get_relation_by_id(
    db: AsyncSession,
    *,
    relation_id: int,
) -> TeachersStudentsDAO | None:
    logger.info(
        "Loading teacher-student relation by id.",
        extra={"relation_id": relation_id},
    )
    result = await db.execute(
        select(TeachersStudentsDAO).where(TeachersStudentsDAO.id == relation_id)
    )
    relation = result.scalar_one_or_none()
    logger.info(
        "Teacher-student relation lookup by id completed.",
        extra={"relation_id": relation_id, "relation_found": relation is not None},
    )
    return relation


async def get_relation_by_pair(
    db: AsyncSession,
    *,
    teacher_id: str,
    student_id: str,
) -> TeachersStudentsDAO | None:
    logger.info(
        "Loading teacher-student relation by pair.",
        extra={"teacher_id": teacher_id, "student_id": student_id},
    )
    result = await db.execute(
        select(TeachersStudentsDAO).where(
            TeachersStudentsDAO.teacher_id == teacher_id,
            TeachersStudentsDAO.student_id == student_id,
        )
    )
    relation = result.scalar_one_or_none()
    logger.info(
        "Teacher-student relation lookup by pair completed.",
        extra={
            "teacher_id": teacher_id,
            "student_id": student_id,
            "relation_found": relation is not None,
        },
    )
    return relation


async def archive_relation(
    db: AsyncSession,
    *,
    relation_id: int,
) -> TeachersStudentsDAO | None:
    logger.info(
        "Archiving teacher-student relation in database.",
        extra={"relation_id": relation_id},
    )
    relation = await get_relation_by_id(db, relation_id=relation_id)
    if relation is None:
        return None

    if relation.status != "archived":
        relation.status = "archived"
        relation.archived_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(relation)

    logger.info(
        "Teacher-student relation archived in database.",
        extra={"relation_id": relation.id},
    )
    return relation
