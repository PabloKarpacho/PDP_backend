import importlib


s3_db_module = importlib.import_module("src.database_control.s3.db")


def test_get_s3_client_uses_iam_role_chain_for_aws_backend(monkeypatch) -> None:
    observed_session_kwargs: list[dict] = []

    class FakeSession:
        def __init__(self, **kwargs) -> None:
            observed_session_kwargs.append(kwargs)

    monkeypatch.setattr(s3_db_module.aioboto3, "Session", FakeSession)
    monkeypatch.setattr(s3_db_module.CONFIG, "STORAGE_BACKEND", "aws")
    monkeypatch.setattr(s3_db_module.CONFIG, "STORAGE_REGION", "eu-central-1")

    client = s3_db_module.get_s3_client()

    assert client.endpoint_url is None
    assert observed_session_kwargs == [{"region_name": "eu-central-1"}]


def test_get_s3_client_uses_minio_credentials_and_endpoint(monkeypatch) -> None:
    observed_session_kwargs: list[dict] = []

    class FakeSession:
        def __init__(self, **kwargs) -> None:
            observed_session_kwargs.append(kwargs)

    monkeypatch.setattr(s3_db_module.aioboto3, "Session", FakeSession)
    monkeypatch.setattr(s3_db_module.CONFIG, "STORAGE_BACKEND", "minio")
    monkeypatch.setattr(s3_db_module.CONFIG, "STORAGE_REGION", "us-east-1")
    monkeypatch.setattr(s3_db_module.CONFIG, "MINIO_ENDPOINT", "minio:9000")
    monkeypatch.setattr(s3_db_module.CONFIG, "MINIO_SECURE", True)
    monkeypatch.setattr(s3_db_module.CONFIG, "MINIO_ROOT_USER", "minio-user")
    monkeypatch.setattr(s3_db_module.CONFIG, "MINIO_ROOT_PASSWORD", "minio-pass")

    client = s3_db_module.get_s3_client()

    assert client.endpoint_url == "https://minio:9000"
    assert observed_session_kwargs == [
        {
            "aws_access_key_id": "minio-user",
            "aws_secret_access_key": "minio-pass",
            "region_name": "us-east-1",
        }
    ]
