from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database_control.postgres import get_db
from src.dependencies import get_student, get_teacher, get_user
from src.logger import logger
from src.models import UserDAO
from src.routers.Relations.schemas import RelationCreateSchema, RelationGetSchema
from src.schemas import ResponseEnvelope, success_response
from src.services.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from src.services.relations import (
    archive_relation_for_user,
    create_relation_for_teacher,
    list_students_for_teacher,
    list_teachers_for_student,
)


PREFIX = "/relations"

router = APIRouter(prefix=PREFIX, tags=["Relations"])


@router.post(
    "/create",
    response_model=ResponseEnvelope[RelationGetSchema],
    summary="Create teacher-student relation",
    description=(
        "Creates a relation between the current authenticated teacher and the "
        "requested student. The endpoint rejects self-links, duplicate pairs and "
        "invalid targets, and is the main entry point for establishing ownership "
        "between both sides before lessons and homework are created."
    ),
    response_description="Created teacher-student relation.",
)
async def create_relation(
    relation: RelationCreateSchema,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[RelationGetSchema]:
    """
    Create a teacher-student relation for the current authenticated teacher.

    Parameters:
    relation (RelationCreateSchema): Payload with the target student identifier.
    user (UserDAO): The current authenticated teacher.
    db (AsyncSession): Active database session.

    Returns:
    ResponseEnvelope[RelationGetSchema]: The created teacher-student relation after
    validation and duplicate checks succeed.
    """
    try:
        relation_data = await create_relation_for_teacher(
            db=db,
            user=user,
            student_id=relation.student_id,
        )
        return success_response(relation_data)
    except ValidationError as error:
        logger.error(
            "Relation creation rejected by validation.",
            extra={"user_id": user.id, "error_type": type(error).__name__},
        )
        raise HTTPException(400, str(error)) from error
    except ConflictError as error:
        logger.error(
            "Relation creation rejected by conflict.",
            extra={"user_id": user.id, "error_type": type(error).__name__},
        )
        raise HTTPException(409, str(error)) from error
    except NotFoundError as error:
        logger.error(
            "Relation creation failed because student was not found.",
            extra={"user_id": user.id, "student_id": relation.student_id},
        )
        raise HTTPException(404, "Student not found") from error


@router.get(
    "/students",
    response_model=ResponseEnvelope[list[RelationGetSchema]],
    summary="List students of current teacher",
    description=(
        "Returns relation records for the current authenticated teacher. "
        "By default only active relations are returned; `include_archived=true` "
        "also includes archived pairs for history and diagnostics."
    ),
    response_description="Teacher-student relations visible to the current teacher.",
)
async def get_students(
    include_archived: bool = False,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[list[RelationGetSchema]]:
    """
    List students linked to the current authenticated teacher.

    Parameters:
    include_archived (bool): Whether archived relations should be included.
    user (UserDAO): The current authenticated teacher.
    db (AsyncSession): Active database session.

    Returns:
    ResponseEnvelope[list[RelationGetSchema]]: Relation records visible to the
    current teacher.
    """
    relations = await list_students_for_teacher(
        db=db,
        user=user,
        include_archived=include_archived,
    )
    return success_response(relations)


@router.get(
    "/teachers",
    response_model=ResponseEnvelope[list[RelationGetSchema]],
    summary="List teachers of current student",
    description=(
        "Returns relation records for the current authenticated student. "
        "By default only active relations are returned; `include_archived=true` "
        "includes archived pairs as well."
    ),
    response_description="Teacher-student relations visible to the current student.",
)
async def get_teachers(
    include_archived: bool = False,
    user: UserDAO = Depends(get_student),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[list[RelationGetSchema]]:
    """
    List teachers linked to the current authenticated student.

    Parameters:
    include_archived (bool): Whether archived relations should be included.
    user (UserDAO): The current authenticated student.
    db (AsyncSession): Active database session.

    Returns:
    ResponseEnvelope[list[RelationGetSchema]]: Relation records visible to the
    current student.
    """
    relations = await list_teachers_for_student(
        db=db,
        user=user,
        include_archived=include_archived,
    )
    return success_response(relations)


@router.post(
    "/archive/{relation_id}",
    response_model=ResponseEnvelope[RelationGetSchema],
    summary="Archive relation",
    description=(
        "Archives an existing teacher-student relation. "
        "The operation is available to participants of the relation and marks "
        "the pair as inactive without deleting the record, so history remains "
        "available for authorization-aware workflows."
    ),
    response_description="Archived teacher-student relation.",
)
async def archive_relation(
    relation_id: int,
    user: UserDAO = Depends(get_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[RelationGetSchema]:
    """
    Archive a teacher-student relation when the current user is a participant.

    Parameters:
    relation_id (int): Identifier of the relation to archive.
    user (UserDAO): The current authenticated application user.
    db (AsyncSession): Active database session.

    Returns:
    ResponseEnvelope[RelationGetSchema]: The archived relation record.
    """
    try:
        relation = await archive_relation_for_user(
            db=db,
            relation_id=relation_id,
            user=user,
        )
        return success_response(relation)
    except ForbiddenError as error:
        raise HTTPException(403, "Forbidden") from error
    except NotFoundError as error:
        raise HTTPException(404, "Relation not found") from error
