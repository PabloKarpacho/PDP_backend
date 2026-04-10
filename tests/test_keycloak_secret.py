import importlib

import pytest


keycloak_secret_module = importlib.import_module("src.services.keycloak_secret")


def test_resolve_keycloak_db_password_prefers_explicit_password() -> None:
    password = keycloak_secret_module.resolve_keycloak_db_password(
        explicit_password="local-password",
        secret_id="ignored",
        region_name="eu-north-1",
    )

    assert password == "local-password"


def test_resolve_keycloak_db_password_loads_password_from_aws_secret() -> None:
    observed_requests: list[tuple[str, str]] = []

    def fake_secret_loader(secret_id: str, region_name: str) -> dict[str, str]:
        observed_requests.append((secret_id, region_name))
        return {"password": "aws-password"}

    password = keycloak_secret_module.resolve_keycloak_db_password(
        explicit_password="",
        secret_id="arn:aws:secretsmanager:eu-north-1:123456789012:secret:keycloak",
        region_name="eu-north-1",
        secret_loader=fake_secret_loader,
    )

    assert password == "aws-password"
    assert observed_requests == [
        (
            "arn:aws:secretsmanager:eu-north-1:123456789012:secret:keycloak",
            "eu-north-1",
        )
    ]


def test_resolve_keycloak_db_password_requires_secret_id_for_aws_resolution() -> None:
    with pytest.raises(
        ValueError,
        match="KC_DB_PASSWORD is empty and KC_DB_AWS_SECRET_ID is not configured",
    ):
        keycloak_secret_module.resolve_keycloak_db_password(
            explicit_password="",
            secret_id="",
            region_name="eu-north-1",
        )


def test_resolve_keycloak_db_password_requires_password_in_secret_payload() -> None:
    def fake_secret_loader(secret_id: str, region_name: str) -> dict[str, str]:
        return {"username": "postgres"}

    with pytest.raises(
        ValueError,
        match="Secrets Manager secret payload must contain a non-empty password",
    ):
        keycloak_secret_module.resolve_keycloak_db_password(
            explicit_password="",
            secret_id="secret-id",
            region_name="eu-north-1",
            secret_loader=fake_secret_loader,
        )
