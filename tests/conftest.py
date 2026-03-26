import sys
from pathlib import Path
from types import ModuleType


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


if "graypy" not in sys.modules:
    graypy_module = ModuleType("graypy")

    class GELFUDPHandler:
        def __init__(self, *args, **kwargs):
            pass

    graypy_module.GELFUDPHandler = GELFUDPHandler
    sys.modules["graypy"] = graypy_module


if "keycloak" not in sys.modules:
    keycloak_module = ModuleType("keycloak")

    class KeycloakOpenID:
        def __init__(self, *args, **kwargs):
            pass

        def public_key(self):
            return "test-public-key"

        def decode_token(self, token, validate=True):
            return {}

    keycloak_module.KeycloakOpenID = KeycloakOpenID
    sys.modules["keycloak"] = keycloak_module
