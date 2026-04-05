import importlib

from sqlalchemy.engine import make_url


postgres_db_module = importlib.import_module("src.database_control.postgres.db")


def test_build_database_runtime_config_uses_local_dsn_without_aws_dependencies() -> (
    None
):
    runtime_config = postgres_db_module._build_database_runtime_config(
        database_backend="local",
        local_dsn="postgresql://postgres:postgres@localhost:5432/pdp",
        aws_region="eu-north-1",
        aws_secret_arn="arn:aws:secretsmanager:example",
        aws_host="database-1.example.amazonaws.com",
        aws_port=5432,
        aws_database="postgres",
        aws_user="postgres",
        aws_ssl_mode="verify-full",
        aws_ssl_root_cert="./global-bundle.pem",
        secret_loader=lambda secret_arn, region_name: {"password": "unused"},
        ssl_context_builder=lambda cert_path: object(),
    )

    assert runtime_config.async_dsn == (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/pdp"
    )
    assert runtime_config.sync_dsn == (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/pdp"
    )
    assert runtime_config.async_connect_args == {}


def test_build_database_runtime_config_uses_aws_secret_and_rds_ssl() -> None:
    observed_secret_requests: list[tuple[str, str]] = []
    observed_cert_paths: list[str] = []
    fake_ssl_context = object()

    def fake_secret_loader(secret_arn: str, region_name: str) -> dict[str, str]:
        observed_secret_requests.append((secret_arn, region_name))
        return {"password": "rds-password"}

    def fake_ssl_context_builder(cert_path: str) -> object:
        observed_cert_paths.append(cert_path)
        return fake_ssl_context

    runtime_config = postgres_db_module._build_database_runtime_config(
        database_backend="aws",
        local_dsn="postgresql://postgres:postgres@localhost:5432/pdp",
        aws_region="eu-north-1",
        aws_secret_arn=(
            "arn:aws:secretsmanager:eu-north-1:406881348631:"
            "secret:rds!db-2278daca-e94b-45f5-b0ed-08d8ce96fa9f-jDlVkq"
        ),
        aws_host="database-1.cxgewygq0xq3.eu-north-1.rds.amazonaws.com",
        aws_port=5432,
        aws_database="postgres",
        aws_user="postgres",
        aws_ssl_mode="verify-full",
        aws_ssl_root_cert="./global-bundle.pem",
        secret_loader=fake_secret_loader,
        ssl_context_builder=fake_ssl_context_builder,
    )

    parsed_async_dsn = make_url(runtime_config.async_dsn)
    parsed_sync_dsn = make_url(runtime_config.sync_dsn)

    assert observed_secret_requests == [
        (
            "arn:aws:secretsmanager:eu-north-1:406881348631:"
            "secret:rds!db-2278daca-e94b-45f5-b0ed-08d8ce96fa9f-jDlVkq",
            "eu-north-1",
        )
    ]
    assert observed_cert_paths == ["./global-bundle.pem"]
    assert parsed_async_dsn.drivername == "postgresql+asyncpg"
    assert parsed_async_dsn.username == "postgres"
    assert parsed_async_dsn.password == "rds-password"
    assert (
        parsed_async_dsn.host == "database-1.cxgewygq0xq3.eu-north-1.rds.amazonaws.com"
    )
    assert parsed_async_dsn.port == 5432
    assert parsed_async_dsn.database == "postgres"
    assert parsed_sync_dsn.drivername == "postgresql+psycopg2"
    assert parsed_sync_dsn.query["sslmode"] == "verify-full"
    assert parsed_sync_dsn.query["sslrootcert"] == "./global-bundle.pem"
    assert runtime_config.async_connect_args == {"ssl": fake_ssl_context}


def test_build_database_runtime_config_allows_aws_without_ssl_certificate() -> None:
    observed_secret_requests: list[tuple[str, str]] = []

    def fake_secret_loader(secret_arn: str, region_name: str) -> dict[str, str]:
        observed_secret_requests.append((secret_arn, region_name))
        return {"password": "rds-password"}

    runtime_config = postgres_db_module._build_database_runtime_config(
        database_backend="aws",
        local_dsn="postgresql://postgres:postgres@localhost:5432/pdp",
        aws_region="eu-north-1",
        aws_secret_arn="arn:aws:secretsmanager:example",
        aws_host="database-1.cxgewygq0xq3.eu-north-1.rds.amazonaws.com",
        aws_port=5432,
        aws_database="postgres",
        aws_user="postgres",
        aws_ssl_mode="disable",
        aws_ssl_root_cert="",
        secret_loader=fake_secret_loader,
        ssl_context_builder=lambda cert_path: (_ for _ in ()).throw(
            AssertionError("SSL context must not be built for disable mode")
        ),
    )

    parsed_async_dsn = make_url(runtime_config.async_dsn)
    parsed_sync_dsn = make_url(runtime_config.sync_dsn)

    assert observed_secret_requests == [
        ("arn:aws:secretsmanager:example", "eu-north-1")
    ]
    assert parsed_async_dsn.drivername == "postgresql+asyncpg"
    assert parsed_async_dsn.password == "rds-password"
    assert parsed_sync_dsn.query["sslmode"] == "disable"
    assert "sslrootcert" not in parsed_sync_dsn.query
    assert runtime_config.async_connect_args == {"ssl": False}
