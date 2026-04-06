from src.config import Settings


def test_settings_use_safe_placeholder_defaults(monkeypatch):
    for env_name in (
        "POSTGRESQL_DSN",
        "SECRET_KEY",
        "SMTP_SERVER",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "MINIO_ROOT_USER",
        "MINIO_ROOT_PASSWORD",
        "AWS_POSTGRES_SECRET_ARN",
        "KEYCLOAK_CLIENT_SECRET",
        "KEYCLOAK_CA_BUNDLE",
    ):
        monkeypatch.delenv(env_name, raising=False)

    settings = Settings(_env_file=None)

    assert (
        settings.POSTGRESQL_DSN
        == "postgresql+asyncpg://app:change-me@localhost:5432/pdp"
    )
    assert settings.SECRET_KEY == "change-me"
    assert settings.SMTP_SERVER == "localhost"
    assert settings.SMTP_USER == "noreply@example.com"
    assert settings.SMTP_PASSWORD == "change-me"
    assert settings.MINIO_ROOT_USER == "minioadmin"
    assert settings.MINIO_ROOT_PASSWORD == "change-me"
    assert settings.AWS_POSTGRES_SECRET_ARN == ""
    assert settings.KEYCLOAK_CLIENT_SECRET == ""
    assert settings.KEYCLOAK_CA_BUNDLE is None


def test_settings_read_canonical_environment_variables(monkeypatch):
    monkeypatch.setenv("ENV", "staging")
    monkeypatch.setenv("APP_PORT", "9001")
    monkeypatch.setenv("POSTGRESQL_DSN", "postgresql+asyncpg://user:pass@db:5432/app")
    monkeypatch.setenv("SMTP_SERVER", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "robot@example.com")
    monkeypatch.setenv("STORAGE_BACKEND", "aws")
    monkeypatch.setenv("STORAGE_REGION", "eu-central-1")
    monkeypatch.setenv("MINIO_ROOT_USER", "ignored-for-aws")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "ignored-for-aws")
    monkeypatch.setenv("KEYCLOAK_HOST_URL", "https://idp.example.com")
    monkeypatch.setenv("KEYCLOAK_REALM", "example")
    monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "backend-client")
    monkeypatch.setenv("KEYCLOAK_CA_BUNDLE", "./certs/keycloak/cert.pem")
    monkeypatch.setenv("KEYCLOAK_ENABLE", "false")

    settings = Settings(_env_file=None)

    assert settings.ENV == "staging"
    assert settings.APP_PORT == 9001
    assert settings.POSTGRESQL_DSN == "postgresql+asyncpg://user:pass@db:5432/app"
    assert settings.SMTP_SERVER == "smtp.example.com"
    assert settings.SMTP_USER == "robot@example.com"
    assert settings.STORAGE_BACKEND == "aws"
    assert settings.STORAGE_REGION == "eu-central-1"
    assert settings.KEYCLOAK_HOST_URL == "https://idp.example.com"
    assert settings.KEYCLOAK_REALM == "example"
    assert settings.KEYCLOAK_CLIENT_ID == "backend-client"
    assert settings.KEYCLOAK_CA_BUNDLE == "./certs/keycloak/cert.pem"
    assert settings.KEYCLOAK_ENABLE is False
