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


@router.post("/create", response_model=ResponseEnvelope[RelationGetSchema])
async def create_relation(
    relation: RelationCreateSchema,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[RelationGetSchema]:
    """
    ### Purpose
    Create a teacher-student relation for the current authenticated teacher.

    ### Access
    Available only to authenticated teachers.

    ### Parameters
    - **relation** (RelationCreateSchema): Payload with the target student identifier.
    - **user** (UserDAO): The current authenticated teacher.
    - **db** (AsyncSession): Active database session.

    ### Returns
    - **ResponseEnvelope[RelationGetSchema]**: The created teacher-student relation after
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
)
async def get_students(
    include_archived: bool = False,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[list[RelationGetSchema]]:
    """
    ### Purpose
    List students linked to the current authenticated teacher.

    ### Access
    Available only to authenticated teachers.

    ### Parameters
    - **include_archived** (bool): Whether archived relations should be included.
    - **user** (UserDAO): The current authenticated teacher.
    - **db** (AsyncSession): Active database session.

    ### Returns
    - **ResponseEnvelope[list[RelationGetSchema]]**: Relation records visible to
    the current teacher.
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
)
async def get_teachers(
    include_archived: bool = False,
    user: UserDAO = Depends(get_student),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[list[RelationGetSchema]]:
    """
    ### Purpose
    List teachers linked to the current authenticated student.

    ### Access
    Available only to authenticated students.

    ### Parameters
    - **include_archived** (bool): Whether archived relations should be included.
    - **user** (UserDAO): The current authenticated student.
    - **db** (AsyncSession): Active database session.

    ### Returns
    - **ResponseEnvelope[list[RelationGetSchema]]**: Relation records visible to
    the current student.
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
)
async def archive_relation(
    relation_id: int,
    user: UserDAO = Depends(get_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[RelationGetSchema]:
    """
    ### Purpose
    Archive a teacher-student relation when the current user is a participant.

    ### Access
    Available to authenticated users who participate in the relation.

    ### Parameters
    - **relation_id** (int): Identifier of the relation to archive.
    - **user** (UserDAO): The current authenticated application user.
    - **db** (AsyncSession): Active database session.

    ### Returns
    - **ResponseEnvelope[RelationGetSchema]**: The archived relation record.
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
