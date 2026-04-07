from typing import Literal

from dotenv import find_dotenv
from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from src.schemas import authConfiguration


_ENV_FILE = find_dotenv("/work/config/env.file") or find_dotenv() or None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    ENV: str = Field(default="production", alias="ENV")
    PROJECT_NAME: str = Field(default="fastapi-best-practices", alias="PROJECT_NAME")
    APP_PORT: int = Field(default=8080, alias="APP_PORT")
    APP_HOST: str = Field(default="0.0.0.0", alias="APP_HOST")
    APP_WORKERS: int = Field(default=1, alias="APP_WORKERS")
    SEND_LOGS_TO_GRAYLOG: bool = Field(default=False, alias="SEND_LOGS_TO_GRAYLOG")
    GRAYLOG_HOST: str = Field(default="localhost", alias="GRAYLOG_HOST")
    GRAYLOG_PORT: int = Field(default=12201, alias="GRAYLOG_PORT")

    # DATABASE
    DATABASE_BACKEND: Literal["local", "aws"] = Field(
        default="local",
        alias="DATABASE_BACKEND",
    )
    POSTGRESQL_DSN: str = Field(
        "postgresql+asyncpg://app:change-me@localhost:5432/pdp",
        alias="POSTGRESQL_DSN",
    )
    AWS_POSTGRES_REGION: str = Field(default="eu-north-1", alias="AWS_POSTGRES_REGION")
    AWS_POSTGRES_HOST: str = Field(default="localhost", alias="AWS_POSTGRES_HOST")
    AWS_POSTGRES_PORT: int = Field(default=5432, alias="AWS_POSTGRES_PORT")
    AWS_POSTGRES_DB: str = Field(default="pdp", alias="AWS_POSTGRES_DB")
    AWS_POSTGRES_USER: str = Field(default="app", alias="AWS_POSTGRES_USER")
    AWS_POSTGRES_SECRET_ARN: str = Field(default="", alias="AWS_POSTGRES_SECRET_ARN")
    AWS_POSTGRES_SSL_MODE: str = Field(default="disable", alias="AWS_POSTGRES_SSL_MODE")
    AWS_POSTGRES_SSL_ROOT_CERT: str = Field(
        default="",
        alias="AWS_POSTGRES_SSL_ROOT_CERT",
    )

    # AUTH
    SECRET_KEY: str = Field(default="change-me", alias="SECRET_KEY")
    ALGORITHM: str = Field(default="HS256", alias="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )

    # MAIL
    SMTP_SERVER: str = Field(default="localhost", alias="SMTP_SERVER")
    SMTP_PORT: int = Field(default=465, alias="SMTP_PORT")
    SMTP_USER: str = Field(default="noreply@example.com", alias="SMTP_USER")
    SMTP_PASSWORD: str = Field(default="change-me", alias="SMTP_PASSWORD")

    # USER
    ROLES_HASHMAP: dict[str, dict[str, bool]] = Field(
        default_factory=lambda: {
            "teacher": {"is_teacher": True},
            "student": {"is_student": True},
        }
    )

    # FILES
    STORAGE_BACKEND: Literal["minio", "aws"] = Field(
        default="minio",
        alias="STORAGE_BACKEND",
    )
    FILES_BUCKET_NAME: str = Field(default="pdp-files", alias="FILES_BUCKET_NAME")
    STORAGE_REGION: str = Field(default="us-east-1", alias="STORAGE_REGION")
    MINIO_ENDPOINT: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    MINIO_ROOT_USER: str = Field(default="minioadmin", alias="MINIO_ROOT_USER")
    MINIO_ROOT_PASSWORD: str = Field(
        default="change-me",
        alias="MINIO_ROOT_PASSWORD",
    )
    MINIO_SECURE: bool = Field(default=False, alias="MINIO_SECURE")
    FILE_UPLOAD_MAX_BYTES: int = Field(
        default=10 * 1024 * 1024,
        alias="FILE_UPLOAD_MAX_BYTES",
    )
    FILE_UPLOAD_ALLOWED_CONTENT_TYPES: tuple[str, ...] = (
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
        "text/plain",
    )
    FILE_UPLOAD_SNIFF_BYTES: int = Field(
        default=4096,
        alias="FILE_UPLOAD_SNIFF_BYTES",
    )
    FILE_UPLOAD_URL_EXPIRY_SECONDS: int = Field(
        default=3600,
        alias="FILE_UPLOAD_URL_EXPIRY_SECONDS",
    )

    # KEYCLOAK
    KEYCLOAK_HOST_URL: str = Field(
        default="http://localhost:8080",
        alias="KEYCLOAK_HOST_URL",
    )
    KEYCLOAK_PUBLIC_URL: str = Field(
        default="http://localhost:8080",
        alias="KEYCLOAK_PUBLIC_URL",
    )
    KEYCLOAK_REALM: str = Field(default="pdp", alias="KEYCLOAK_REALM")
    KEYCLOAK_CLIENT_ID: str = Field(
        default="fastapi-client",
        alias="KEYCLOAK_CLIENT_ID",
    )
    KEYCLOAK_CLIENT_SECRET: str = Field(
        default="",
        alias="KEYCLOAK_CLIENT_SECRET",
    )
    KEYCLOAK_CA_BUNDLE: str | None = Field(
        default=None,
        alias="KEYCLOAK_CA_BUNDLE",
    )
    KEYCLOAK_ENABLE: bool = Field(default=True, alias="KEYCLOAK_ENABLE")

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
