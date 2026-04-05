class Roles:
    TEACHER = "Teacher"
    STUDENT = "Student"


class LessonStatuses:
    ACTIVE = "active"
    PASSED = "passed"
    CANCELLED = "cancelled"


LESSON_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    LessonStatuses.ACTIVE: frozenset(
        {
            LessonStatuses.ACTIVE,
            LessonStatuses.PASSED,
            LessonStatuses.CANCELLED,
        }
    ),
    LessonStatuses.PASSED: frozenset({LessonStatuses.PASSED}),
    LessonStatuses.CANCELLED: frozenset({LessonStatuses.CANCELLED}),
}


def normalize_role_name(role: str | None) -> str | None:
    if role is None:
        return None

    normalized = role.strip().casefold()
    role_map = {
        Roles.TEACHER.casefold(): Roles.TEACHER,
        Roles.STUDENT.casefold(): Roles.STUDENT,
    }
    return role_map.get(normalized)


def normalize_realm_roles(roles: list[str] | None) -> list[str]:
    if not roles:
        return []

    normalized_roles = {
        normalized_role
        for role in roles
        if (normalized_role := normalize_role_name(role)) is not None
    }

    ordered_roles = []
    for role in (Roles.TEACHER, Roles.STUDENT):
        if role in normalized_roles:
            ordered_roles.append(role)
    return ordered_roles


def resolve_authoritative_role(realm_roles: list[str] | None) -> str | None:
    normalized_roles = normalize_realm_roles(realm_roles)
    return normalized_roles[0] if normalized_roles else None


def role_matches(role: str | None, target_role: str) -> bool:
    return normalize_role_name(role) == normalize_role_name(target_role)


def is_allowed_lesson_status_transition(
    current_status: str,
    new_status: str,
) -> bool:
    return new_status in LESSON_STATUS_TRANSITIONS.get(
        current_status,
        frozenset(),
    )
