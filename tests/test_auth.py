import pytest

from src.auth import get_user_info
from src.constants import Roles


@pytest.mark.asyncio
async def test_get_user_info_uses_realm_roles_as_role_authority():
    user = await get_user_info(
        payload={
            "sub": "user-1",
            "name": "John",
            "email": "john@example.com",
            "role": Roles.TEACHER,
            "realm_access": {"roles": [Roles.STUDENT.lower()]},
        }
    )

    assert user.role == Roles.STUDENT
    assert user.realm_roles == [Roles.STUDENT]
    assert user.has_role(Roles.STUDENT) is True
    assert user.has_role(Roles.TEACHER) is False


@pytest.mark.asyncio
async def test_get_user_info_prefers_teacher_when_both_supported_roles_present():
    user = await get_user_info(
        payload={
            "sub": "user-1",
            "name": "John",
            "email": "john@example.com",
            "realm_access": {"roles": [Roles.STUDENT.lower(), Roles.TEACHER.lower()]},
        }
    )

    assert user.role == Roles.TEACHER
    assert user.realm_roles == [Roles.TEACHER, Roles.STUDENT]


@pytest.mark.asyncio
async def test_get_user_info_sets_role_to_none_when_realm_roles_have_no_supported_roles():
    user = await get_user_info(
        payload={
            "sub": "user-1",
            "name": "John",
            "email": "john@example.com",
            "role": Roles.TEACHER,
            "realm_access": {"roles": ["admin"]},
        }
    )

    assert user.role is None
    assert user.realm_roles == []


@pytest.mark.asyncio
async def test_get_user_info_uses_top_level_role_when_realm_roles_are_missing():
    user = await get_user_info(
        payload={
            "sub": "user-1",
            "name": "Pavel Karpov",
            "preferred_username": "karpoffpasha@yandex.ru",
            "given_name": "Pavel",
            "family_name": "Karpov",
            "email": "karpoffpasha@yandex.ru",
            "role": Roles.TEACHER,
        }
    )

    assert user.username == "karpoffpasha@yandex.ru"
    assert user.first_name == "Pavel"
    assert user.last_name == "Karpov"
    assert user.role == Roles.TEACHER
    assert user.realm_roles == [Roles.TEACHER]
