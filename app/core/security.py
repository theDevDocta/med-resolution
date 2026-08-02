"""Authentification inter-services : clé API partagée (header X-API-Key)."""

from fastapi import Header, HTTPException

from app.core import config


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Vérifie X-API-Key contre API_KEY si celle-ci est configurée."""
    if config.API_KEY and x_api_key != config.API_KEY:
        raise HTTPException(status_code=401, detail="Clé API invalide ou manquante.")
