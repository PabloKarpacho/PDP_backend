from pydantic import BaseModel


class KeycloakUser(BaseModel):
    id: str
    username: str | None = None
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    role: str | None = None
    realm_roles: list

    def has_role(self, role_name: str) -> bool:
        return role_name in self.realm_roles


class authConfiguration(BaseModel):
    server_url: str
    realm: str
    client_id: str
    client_secret: str
    authorization_url: str
    token_url: str
