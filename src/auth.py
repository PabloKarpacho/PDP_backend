from fastapi import Depends
from fastapi import status
from fastapi.security import OAuth2AuthorizationCodeBearer
from keycloak import KeycloakOpenID
from starlette.exceptions import HTTPException

from src.config import CONFIG
from src.config import settings
from src.logger import logger
from src.schemas import KeycloakUser


def no_oauth2_scheme():
    return None


if CONFIG.KEYCLOAK_ENABLE:
    oauth2_scheme = OAuth2AuthorizationCodeBearer(
        authorizationUrl=settings.authorization_url,
        tokenUrl=settings.token_url,
    )
else:
    oauth2_scheme = no_oauth2_scheme

keycloak_openid = KeycloakOpenID(
    server_url=settings.server_url,
    client_id=settings.client_id,
    realm_name=settings.realm,
    client_secret_key=settings.client_secret,
    verify=False,
)


async def get_idp_public_key():
    return (
        "-----BEGIN PUBLIC KEY-----\n"
        f"{keycloak_openid.public_key()}"
        "\n-----END PUBLIC KEY-----"
    )


async def get_payload(token: str = Depends(oauth2_scheme)) -> dict:
    if not CONFIG.KEYCLOAK_ENABLE:
        return {}
    try:
        decode = keycloak_openid.decode_token(token, validate=True)
        return decode
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),  # "Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_user_info(payload: dict = Depends(get_payload)) -> KeycloakUser:
    try:
        logger.info(f"Payload: {payload}")
        realm_roles = payload.get("realm_access", {}).get("roles", [])
        return KeycloakUser(
            id=payload.get("sub"),
            username=payload.get("preferred_username") or payload.get("name"),
            email=payload.get("email"),
            first_name=payload.get("given_name"),
            last_name=payload.get("family_name") or payload.get("last_name"),
            phone=payload.get("phone"),
            realm_roles=realm_roles,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),  # "Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
