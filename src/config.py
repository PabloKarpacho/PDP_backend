from pydantic import AliasChoices
from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict
from dotenv import find_dotenv

from src.schemas import authConfiguration


_ENV_FILE = find_dotenv("/work/config/env.file") or find_dotenv() or None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    ENV: str = "production"
    PROJECT_NAME: str = "fastapi-best-practices"
    APP_PORT: int = 8080
    APP_HOST: str = "0.0.0.0"
    APP_WORKERS: int = 1
    SEND_LOGS_TO_GRAYLOG: bool = False
    GRAYLOG_HOST: str = "ml-dev1.dohod.local"
    GRAYLOG_PORT: int = 12201

    # DATABASE
    POSTGRESQL_DSN: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pdp"

    # AUTH
    SECRET_KEY: str = "gV64m9aIzFG4qpgVphvQbPQrtAO0nM-7YwwOvu0XPt5KJOjAy4AfgLkqJXYEt"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # MAIL
    SMTP_SERVER: str = Field(
        default="smtp.yandex.ru",
        validation_alias=AliasChoices("SMTP_HOST", "SMTP_SERVER"),
    )
    SMTP_PORT: int = 465
    SMTP_USER: str = "karpoffpasha@yandex.ru"
    SMTP_PASSWORD: str = "wjjuemuicfnpwxsj"

    # USER
    ROLES_HASHMAP: dict[str, dict[str, bool]] = {
        "teacher": {"is_teacher": True},
        "student": {"is_student": True},
    }

    # FILES
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ROOT_USER: str = "ROOTNAME"
    MINIO_ROOT_PASSWORD: str = "CHANGEME123"
    MINIO_FILES_BUCKET_NAME: str = "pdp-files"
    MINIO_SECURE: bool = False

    # KEYCLOACK
    KEYCLOACK_HOST_URL: str = Field(
        default="http://localhost:8080",
        validation_alias=AliasChoices("KEYCLOACK_HOST_URL", "KEYCLOAK_HOST_URL"),
    )
    KEYCLOACK_PUBLIC_URL: str = Field(
        default="http://localhost:8080",
        validation_alias=AliasChoices("KEYCLOACK_PUBLIC_URL", "KEYCLOAK_PUBLIC_URL"),
    )
    KEYCLOACK_REALM: str = Field(
        default="pdp",
        validation_alias=AliasChoices("KEYCLOACK_REALM", "KEYCLOAK_REALM"),
    )
    KEYCLOACK_CLIENT_ID: str = Field(
        default="fastapi-client",
        validation_alias=AliasChoices("KEYCLOACK_CLIENT_ID", "KEYCLOAK_CLIENT_ID"),
    )
    KEYCLOACK_CLIENT_SECRET: str = Field(
        default="",
        validation_alias=AliasChoices(
            "KEYCLOACK_CLIENT_SECRET",
            "KEYCLOAK_CLIENT_SECRET",
        ),
    )
    KEYCLOAK_ENABLE: bool = True


CONFIG = Settings()

settings = authConfiguration(
    server_url=CONFIG.KEYCLOACK_HOST_URL,
    realm=CONFIG.KEYCLOACK_REALM,
    client_id=CONFIG.KEYCLOACK_CLIENT_ID,
    client_secret=CONFIG.KEYCLOACK_CLIENT_SECRET,
    authorization_url=f"{CONFIG.KEYCLOACK_PUBLIC_URL}/realms/{CONFIG.KEYCLOACK_REALM}/protocol/openid-connect/auth",
    token_url=f"{CONFIG.KEYCLOACK_PUBLIC_URL}/realms/{CONFIG.KEYCLOACK_REALM}/protocol/openid-connect/token",
)
