import importlib


alembic_config_module = importlib.import_module(
    "src.database_control.postgres.alembic_config"
)


def test_get_database_url_prefers_explicit_alembic_database_url(monkeypatch) -> None:
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", "postgresql://override")
    monkeypatch.setenv("POSTGRESQL_DSN", "postgresql+asyncpg://ignored")
    monkeypatch.setattr(
        alembic_config_module,
        "get_runtime_sync_dsn",
        lambda: "postgresql://runtime",
    )

    assert (
        alembic_config_module.resolve_alembic_database_url("postgresql://default")
        == "postgresql://override"
    )


def test_get_database_url_uses_runtime_database_config_when_no_override(
    monkeypatch,
) -> None:
    monkeypatch.delenv("ALEMBIC_DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRESQL_DSN", raising=False)
    monkeypatch.setattr(
        alembic_config_module,
        "get_runtime_sync_dsn",
        lambda: "postgresql://runtime",
    )

    assert (
        alembic_config_module.resolve_alembic_database_url("postgresql://default")
        == "postgresql://runtime"
    )


def test_get_database_url_keeps_local_postgresql_dsn_compatibility(monkeypatch) -> None:
    monkeypatch.delenv("ALEMBIC_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_BACKEND", raising=False)
    monkeypatch.setenv(
        "POSTGRESQL_DSN",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/pdp",
    )
    monkeypatch.setattr(
        alembic_config_module,
        "get_runtime_sync_dsn",
        lambda: "postgresql://runtime",
    )

    assert (
        alembic_config_module.resolve_alembic_database_url("postgresql://default")
        == "postgresql+psycopg2://postgres:postgres@localhost:5432/pdp"
    )


def test_get_database_url_prefers_runtime_config_for_aws_backend(monkeypatch) -> None:
    monkeypatch.delenv("ALEMBIC_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_BACKEND", "aws")
    monkeypatch.setenv(
        "POSTGRESQL_DSN",
        "postgresql+asyncpg://postgres:postgres@pdp-db:5432/pdp",
    )
    monkeypatch.setattr(
        alembic_config_module,
        "get_runtime_sync_dsn",
        lambda: "postgresql://aws-runtime",
    )

    assert (
        alembic_config_module.resolve_alembic_database_url("postgresql://default")
        == "postgresql://aws-runtime"
    )


def test_escape_alembic_config_value_escapes_percent_for_configparser() -> None:
    raw_value = (
        "postgresql+psycopg2://postgres:secret@database-1.example.amazonaws.com:5432/"
        "postgres?sslmode=verify-full&sslrootcert=%2Fwork%2Fglobal-bundle.pem"
    )

    assert alembic_config_module.escape_alembic_config_value(raw_value) == (
        "postgresql+psycopg2://postgres:secret@database-1.example.amazonaws.com:5432/"
        "postgres?sslmode=verify-full&sslrootcert=%%2Fwork%%2Fglobal-bundle.pem"
    )
