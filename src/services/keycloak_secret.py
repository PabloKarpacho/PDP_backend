import json
import os
from collections.abc import Callable
from typing import Any

import boto3


def _load_aws_secret(secret_id: str, region_name: str) -> dict[str, Any]:
    client = boto3.client("secretsmanager", region_name=region_name)
    response = client.get_secret_value(SecretId=secret_id)
    secret_string = response.get("SecretString")
    if not secret_string:
        raise ValueError("Secrets Manager response did not contain SecretString")

    secret_payload = json.loads(secret_string)
    if not isinstance(secret_payload, dict):
        raise ValueError("Secrets Manager secret payload must be a JSON object")

    return secret_payload


def resolve_keycloak_db_password(
    *,
    explicit_password: str,
    secret_id: str,
    region_name: str,
    secret_key: str = "password",
    secret_loader: Callable[[str, str], dict[str, Any]] = _load_aws_secret,
) -> str:
    normalized_password = explicit_password.strip()
    if normalized_password:
        return normalized_password

    normalized_secret_id = secret_id.strip()
    if not normalized_secret_id:
        raise ValueError(
            "KC_DB_PASSWORD is empty and KC_DB_AWS_SECRET_ID is not configured"
        )

    normalized_region_name = region_name.strip()
    if not normalized_region_name:
        raise ValueError(
            "KC_DB_AWS_REGION is empty and no AWS region fallback is available"
        )

    secret_payload = secret_loader(normalized_secret_id, normalized_region_name)
    password = secret_payload.get(secret_key)
    if not isinstance(password, str) or not password.strip():
        raise ValueError(
            "Secrets Manager secret payload must contain a non-empty password"
        )

    return password


def main() -> None:
    secret_id = os.getenv("KC_DB_AWS_SECRET_ID", "")
    region_name = os.getenv("KC_DB_AWS_REGION", "")
    explicit_password = os.getenv("KC_DB_PASSWORD", "")
    password = resolve_keycloak_db_password(
        explicit_password=explicit_password,
        secret_id=secret_id,
        region_name=region_name,
    )
    print(password, end="")


if __name__ == "__main__":
    main()
