from typing import Literal

from pydantic import AliasChoices
from pydantic import Field
from pydantic import model_validator
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
    DATABASE_BACKEND: Literal["local", "aws"] = "local"
    POSTGRESQL_DSN: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pdp"
    AWS_POSTGRES_REGION: str = "eu-north-1"
    AWS_POSTGRES_HOST: str = "database-1.cxgewygq0xq3.eu-north-1.rds.amazonaws.com"
    AWS_POSTGRES_PORT: int = 5432
    AWS_POSTGRES_DB: str = "postgres"
    AWS_POSTGRES_USER: str = "postgres"
    AWS_POSTGRES_SECRET_ARN: str = (
        "arn:aws:secretsmanager:eu-north-1:406881348631:"
        "secret:rds!db-2278daca-e94b-45f5-b0ed-08d8ce96fa9f-jDlVkq"
    )
    AWS_POSTGRES_SSL_MODE: str = "disable"
    AWS_POSTGRES_SSL_ROOT_CERT: str = ""

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
    STORAGE_BACKEND: Literal["minio", "aws"] = "minio"
    FILES_BUCKET_NAME: str = Field(
        default="pdp-files",
        validation_alias=AliasChoices("FILES_BUCKET_NAME", "MINIO_FILES_BUCKET_NAME"),
    )
    STORAGE_REGION: str = Field(
        default="us-east-1",
        validation_alias=AliasChoices("STORAGE_REGION", "AWS_REGION"),
    )
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ROOT_USER: str = "ROOTNAME"
    MINIO_ROOT_PASSWORD: str = "CHANGEME123"
    MINIO_SECURE: bool = False
    FILE_UPLOAD_MAX_BYTES: int = 10 * 1024 * 1024
    FILE_UPLOAD_ALLOWED_CONTENT_TYPES: tuple[str, ...] = (
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
        "text/plain",
        "application/octet-stream",
    )
    FILE_UPLOAD_URL_EXPIRY_SECONDS: int = 3600

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

    @model_validator(mode="after")
    def validate_storage_settings(self) -> "Settings":
        if self.DATABASE_BACKEND == "aws":
            if not self.AWS_POSTGRES_REGION.strip():
                raise ValueError(
                    "AWS_POSTGRES_REGION must not be empty for aws database backend"
                )

            if not self.AWS_POSTGRES_HOST.strip():
                raise ValueError(
                    "AWS_POSTGRES_HOST must not be empty for aws database backend"
                )

            if not self.AWS_POSTGRES_DB.strip():
                raise ValueError(
                    "AWS_POSTGRES_DB must not be empty for aws database backend"
                )

            if not self.AWS_POSTGRES_USER.strip():
                raise ValueError(
                    "AWS_POSTGRES_USER must not be empty for aws database backend"
                )

            if not self.AWS_POSTGRES_SECRET_ARN.strip():
                raise ValueError(
                    "AWS_POSTGRES_SECRET_ARN must not be empty for aws database backend"
                )

            if not self.AWS_POSTGRES_SSL_MODE.strip():
                raise ValueError(
                    "AWS_POSTGRES_SSL_MODE must not be empty for aws database backend"
                )

            if (
                self.AWS_POSTGRES_SSL_MODE.strip().lower()
                in {"verify-ca", "verify-full"}
                and not self.AWS_POSTGRES_SSL_ROOT_CERT.strip()
            ):
                raise ValueError(
                    "AWS_POSTGRES_SSL_ROOT_CERT must not be empty for verify-ca/verify-full"
                )

        if not self.FILES_BUCKET_NAME.strip():
            raise ValueError("FILES_BUCKET_NAME must not be empty")

        if not self.STORAGE_REGION.strip():
            raise ValueError("STORAGE_REGION must not be empty")

        if self.STORAGE_BACKEND != "minio":
            return self

        if not self.MINIO_ENDPOINT.strip():
            raise ValueError("MINIO_ENDPOINT must not be empty for minio backend")

        if not self.MINIO_ROOT_USER.strip():
            raise ValueError("MINIO_ROOT_USER must not be empty for minio backend")

        if not self.MINIO_ROOT_PASSWORD.strip():
            raise ValueError("MINIO_ROOT_PASSWORD must not be empty for minio backend")

        return self


CONFIG = Settings()

settings = authConfiguration(
    server_url=CONFIG.KEYCLOACK_HOST_URL,
    realm=CONFIG.KEYCLOACK_REALM,
    client_id=CONFIG.KEYCLOACK_CLIENT_ID,
    client_secret=CONFIG.KEYCLOACK_CLIENT_SECRET,
    authorization_url=f"{CONFIG.KEYCLOACK_PUBLIC_URL}/realms/{CONFIG.KEYCLOACK_REALM}/protocol/openid-connect/auth",
    token_url=f"{CONFIG.KEYCLOACK_PUBLIC_URL}/realms/{CONFIG.KEYCLOACK_REALM}/protocol/openid-connect/token",
)
