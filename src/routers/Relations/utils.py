from src.models import TeachersStudentsDAO
from src.routers.Relations.schemas import RelationGetSchema


def serialize_relation(relation: TeachersStudentsDAO) -> RelationGetSchema:
    return RelationGetSchema(
        id=relation.id,
        teacher_id=relation.teacher_id,
        student_id=relation.student_id,
        status=relation.status,
        archived_at=relation.archived_at,
        updated_at=relation.updated_at,
        created_at=relation.created_at,
    )
