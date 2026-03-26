import json
import os

from dotenv import find_dotenv
from dotenv import load_dotenv
from src.schemas import authConfiguration

if not load_dotenv(find_dotenv("/work/config/env.file")):
    load_dotenv(find_dotenv())


class Config:
    ENV = "production"
    PROJECT_NAME = "fastapi-best-practices"
    APP_PORT = int(os.getenv("APP_PORT", 8080))
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_WORKERS = int(os.getenv("APP_WORKERS", 1))
    SEND_LOGS_TO_GRAYLOG: bool = os.getenv("SEND_LOGS_TO_GRAYLOG", "False").lower() in (
        "true",
        "1",
    )
    GRAYLOG_HOST = os.getenv("GRAYLOG_HOST", "ml-dev1.dohod.local")
    GRAYLOG_PORT = int(os.getenv("GRAYLOG_PORT", 12201))

    #DATABASE

    POSTGRESQL_DSN = os.getenv("POSTGRESQL_DSN", "postgresql+asyncpg://postgres:postgres@localhost:5432/pdp")

    #AUTH

    SECRET_KEY=os.getenv("SECRET_KEY", "gV64m9aIzFG4qpgVphvQbPQrtAO0nM-7YwwOvu0XPt5KJOjAy4AfgLkqJXYEt")
    ALGORITHM=os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = 30

    #MAIL

    SMTP_SERVER = os.getenv("SMTP_HOST",  "smtp.yandex.ru")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
    SMTP_USER = os.getenv("SMTP_USER", "karpoffpasha@yandex.ru")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "wjjuemuicfnpwxsj")
    
    #USER

    ROLES_HASHMAP = {"teacher" : {"is_teacher" : True},
                     "student" : {"is_student" : True}}
    
    #FILES

    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT",  "localhost:9000")
    MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER",  "ROOTNAME")
    MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD",  "CHANGEME123")
    MINIO_FILES_BUCKET_NAME = os.getenv("MINIO_FILES_BUCKET_NAME",  "pdp-files")
    MINIO_SECURE = os.getenv("MINIO_SECURE",  False)

    #KEYCLOACK
    
    KEYCLOACK_HOST_URL = os.getenv("KEYCLOACK_HOST_URL", "http://localhost:8080")
    KEYCLOACK_PUBLIC_URL = os.getenv("KEYCLOACK_PUBLIC_URL", "http://localhost:8080")
    KEYCLOACK_REALM = os.getenv("KEYCLOACK_REALM", "pdp")
    KEYCLOACK_CLIENT_ID = os.getenv("KEYCLOACK_CLIENT_ID", "fastapi-client")
    KEYCLOACK_CLIENT_SECRET = os.getenv("KEYCLOACK_CLIENT_SECRET", "")
    KEYCLOAK_ENABLE = os.getenv("KEYCLOAK_ENABLE", True)


CONFIG = Config()

settings = authConfiguration(
    server_url=CONFIG.KEYCLOACK_HOST_URL,
    realm=CONFIG.KEYCLOACK_REALM,
    client_id=CONFIG.KEYCLOACK_CLIENT_ID,
    client_secret=CONFIG.KEYCLOACK_CLIENT_SECRET,
    authorization_url=f"{CONFIG.KEYCLOACK_PUBLIC_URL}/realms/{CONFIG.KEYCLOACK_REALM}/protocol/openid-connect/auth",
    token_url=f"{CONFIG.KEYCLOACK_PUBLIC_URL}/realms/{CONFIG.KEYCLOACK_REALM}/protocol/openid-connect/token",
)
