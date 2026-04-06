from typing import Any, Literal

from dotenv import find_dotenv
from pydantic import AliasChoices
from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from src.schemas import authConfiguration


_ENV_FILE = find_dotenv("/work/config/env.file") or find_dotenv() or None


def env_field(default: Any, *env_names: str) -> Any:
    return Field(
        default=default,
        validation_alias=AliasChoices(*env_names),
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    ENV: str = env_field("production", "ENV", "APP_ENV", "ENVIRONMENT")
    PROJECT_NAME: str = env_field(
        "fastapi-best-practices",
        "PROJECT_NAME",
        "APP_NAME",
        "SERVICE_NAME",
    )
    APP_PORT: int = env_field(8080, "APP_PORT", "PORT")
    APP_HOST: str = env_field("0.0.0.0", "APP_HOST", "HOST")
    APP_WORKERS: int = env_field(1, "APP_WORKERS", "WEB_CONCURRENCY")
    SEND_LOGS_TO_GRAYLOG: bool = env_field(
        False,
        "SEND_LOGS_TO_GRAYLOG",
        "GRAYLOG_ENABLED",
    )
    GRAYLOG_HOST: str = env_field("localhost", "GRAYLOG_HOST")
    GRAYLOG_PORT: int = env_field(12201, "GRAYLOG_PORT")

    # DATABASE
    DATABASE_BACKEND: Literal["local", "aws"] = env_field(
        "local",
        "DATABASE_BACKEND",
        "DB_BACKEND",
    )
    POSTGRESQL_DSN: str = env_field(
        "postgresql+asyncpg://app:change-me@localhost:5432/pdp",
        "POSTGRESQL_DSN",
        "DATABASE_URL",
    )
    AWS_POSTGRES_REGION: str = env_field("eu-north-1", "AWS_POSTGRES_REGION")
    AWS_POSTGRES_HOST: str = env_field("localhost", "AWS_POSTGRES_HOST")
    AWS_POSTGRES_PORT: int = env_field(5432, "AWS_POSTGRES_PORT")
    AWS_POSTGRES_DB: str = env_field("pdp", "AWS_POSTGRES_DB")
    AWS_POSTGRES_USER: str = env_field("app", "AWS_POSTGRES_USER")
    AWS_POSTGRES_SECRET_ARN: str = env_field("", "AWS_POSTGRES_SECRET_ARN")
    AWS_POSTGRES_SSL_MODE: str = env_field("disable", "AWS_POSTGRES_SSL_MODE")
    AWS_POSTGRES_SSL_ROOT_CERT: str = env_field("", "AWS_POSTGRES_SSL_ROOT_CERT")

    # AUTH
    SECRET_KEY: str = env_field("change-me", "SECRET_KEY", "APP_SECRET_KEY")
    ALGORITHM: str = env_field("HS256", "ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = env_field(
        30,
        "ACCESS_TOKEN_EXPIRE_MINUTES",
    )

    # MAIL
    SMTP_SERVER: str = Field(
        default="localhost",
        validation_alias=AliasChoices("SMTP_SERVER", "SMTP_HOST"),
    )
    SMTP_PORT: int = env_field(465, "SMTP_PORT")
    SMTP_USER: str = env_field("noreply@example.com", "SMTP_USER", "SMTP_USERNAME")
    SMTP_PASSWORD: str = env_field("change-me", "SMTP_PASSWORD")

    # USER
    ROLES_HASHMAP: dict[str, dict[str, bool]] = Field(
        default_factory=lambda: {
            "teacher": {"is_teacher": True},
            "student": {"is_student": True},
        }
    )

    # FILES
    STORAGE_BACKEND: Literal["minio", "aws"] = env_field(
        "minio",
        "STORAGE_BACKEND",
        "FILES_STORAGE_BACKEND",
    )
    FILES_BUCKET_NAME: str = Field(
        default="pdp-files",
        validation_alias=AliasChoices("FILES_BUCKET_NAME", "MINIO_FILES_BUCKET_NAME"),
    )
    STORAGE_REGION: str = Field(
        default="us-east-1",
        validation_alias=AliasChoices("STORAGE_REGION", "AWS_REGION"),
    )
    MINIO_ENDPOINT: str = Field(
        default="localhost:9000",
        validation_alias=AliasChoices(
            "MINIO_ENDPOINT",
            "MINIO_ENDPOINT_URL",
            "S3_ENDPOINT_URL",
        ),
    )
    MINIO_ROOT_USER: str = Field(
        default="minioadmin",
        validation_alias=AliasChoices(
            "MINIO_ROOT_USER",
            "MINIO_ACCESS_KEY",
        ),
    )
    MINIO_ROOT_PASSWORD: str = Field(
        default="change-me",
        validation_alias=AliasChoices(
            "MINIO_ROOT_PASSWORD",
            "MINIO_SECRET_KEY",
        ),
    )
    MINIO_SECURE: bool = env_field(False, "MINIO_SECURE")
    FILE_UPLOAD_MAX_BYTES: int = env_field(
        10 * 1024 * 1024,
        "FILE_UPLOAD_MAX_BYTES",
    )
    FILE_UPLOAD_ALLOWED_CONTENT_TYPES: tuple[str, ...] = (
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
        "text/plain",
        "application/octet-stream",
    )
    FILE_UPLOAD_URL_EXPIRY_SECONDS: int = env_field(
        3600,
        "FILE_UPLOAD_URL_EXPIRY_SECONDS",
    )

    # KEYCLOAK
    KEYCLOAK_HOST_URL: str = Field(
        default="http://localhost:8080",
        validation_alias=AliasChoices("KEYCLOAK_HOST_URL", "KEYCLOACK_HOST_URL"),
    )
    KEYCLOAK_PUBLIC_URL: str = Field(
        default="http://localhost:8080",
        validation_alias=AliasChoices("KEYCLOAK_PUBLIC_URL", "KEYCLOACK_PUBLIC_URL"),
    )
    KEYCLOAK_REALM: str = Field(
        default="pdp",
        validation_alias=AliasChoices("KEYCLOAK_REALM", "KEYCLOACK_REALM"),
    )
    KEYCLOAK_CLIENT_ID: str = Field(
        default="fastapi-client",
        validation_alias=AliasChoices("KEYCLOAK_CLIENT_ID", "KEYCLOACK_CLIENT_ID"),
    )
    KEYCLOAK_CLIENT_SECRET: str = Field(
        default="",
        validation_alias=AliasChoices(
            "KEYCLOAK_CLIENT_SECRET",
            "KEYCLOACK_CLIENT_SECRET",
        ),
    )
    KEYCLOAK_ENABLE: bool = Field(
        default=True,
        validation_alias=AliasChoices("KEYCLOAK_ENABLE", "KEYCLOACK_ENABLE"),
    )

    @property
    def KEYCLOACK_HOST_URL(self) -> str:
        return self.KEYCLOAK_HOST_URL

    @property
    def KEYCLOACK_PUBLIC_URL(self) -> str:
        return self.KEYCLOAK_PUBLIC_URL

    @property
    def KEYCLOACK_REALM(self) -> str:
        return self.KEYCLOAK_REALM

    @property
    def KEYCLOACK_CLIENT_ID(self) -> str:
        return self.KEYCLOAK_CLIENT_ID

    @property
    def KEYCLOACK_CLIENT_SECRET(self) -> str:
        return self.KEYCLOAK_CLIENT_SECRET

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
    server_url=CONFIG.KEYCLOAK_HOST_URL,
    realm=CONFIG.KEYCLOAK_REALM,
    client_id=CONFIG.KEYCLOAK_CLIENT_ID,
    client_secret=CONFIG.KEYCLOAK_CLIENT_SECRET,
    authorization_url=f"{CONFIG.KEYCLOAK_PUBLIC_URL}/realms/{CONFIG.KEYCLOAK_REALM}/protocol/openid-connect/auth",
    token_url=f"{CONFIG.KEYCLOAK_PUBLIC_URL}/realms/{CONFIG.KEYCLOAK_REALM}/protocol/openid-connect/token",
)
