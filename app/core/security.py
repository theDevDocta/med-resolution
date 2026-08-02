"""Authentification inter-services : clé API partagée (header X-API-Key)."""

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.core import config

_api_key_header = APIKeyHeader(name="X-API-Key", scheme_name="ApiKeyAuth", auto_error=False)


def verify_api_key(x_api_key: str | None = Security(_api_key_header)) -> None:
    """Vérifie X-API-Key contre API_KEY si celle-ci est configurée."""
    if config.API_KEY and x_api_key != config.API_KEY:
        raise HTTPException(status_code=401, detail="Clé API invalide ou manquante.")
