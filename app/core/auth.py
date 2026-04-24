from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from app.core.config import get_settings

ROLE_RANK = {"viewer": 1, "editor": 2, "admin": 3}


@dataclass(frozen=True, slots=True)
class AuthContext:
    api_key: str
    role: str


def _parse_api_keys(raw_value: str) -> dict[str, str]:
    """
    API_KEYS format:
      - "tokenA:admin,tokenB:editor"
      - "tokenA,tokenB" (fallback role = api_default_role)
    """
    out: dict[str, str] = {}
    for chunk in (raw_value or "").split(","):
        value = chunk.strip()
        if not value:
            continue
        if ":" in value:
            token, role = value.split(":", 1)
            role = role.strip().lower()
            if role not in ROLE_RANK:
                role = "viewer"
            out[token.strip()] = role
        else:
            out[value] = get_settings().api_default_role
    return out


def require_role(min_role: str = "viewer"):
    if min_role not in ROLE_RANK:
        raise ValueError(f"Unsupported role: {min_role}")

    def _dependency(x_api_key: str | None = Header(default=None)) -> AuthContext:
        settings = get_settings()
        configured = _parse_api_keys(settings.api_keys)
        # Local/dev convenience: if no API keys configured, auth is disabled.
        if not configured:
            return AuthContext(api_key="anonymous", role="admin")
        if not x_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API key",
            )
        role = configured.get(x_api_key)
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
        if ROLE_RANK[role] < ROLE_RANK[min_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )
        return AuthContext(api_key=x_api_key, role=role)

    return Depends(_dependency)
