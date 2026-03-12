
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token, hash_api_key
from app.models import APIKey, Membership, User, Tenant


@dataclass
class ActorContext:
    actor_type: str
    actor_id: str
    user_id: Optional[str]
    tenant_id: str
    role: str


def _unauthorized(message: str = "Not authenticated"):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)


def get_actor_context(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> ActorContext:
    if not authorization or not authorization.lower().startswith("bearer "):
        _unauthorized()

    token = authorization.split(" ", 1)[1].strip()

    # Try JWT first.
    try:
        payload = decode_access_token(token)
        tenant_id = payload.get("tenant_id")
        user_id = payload.get("user_id")
        role = payload.get("role")
        if not (tenant_id and user_id and role):
            _unauthorized("Invalid token payload")
        user = db.get(User, user_id)
        if not user:
            _unauthorized("User not found")
        return ActorContext(
            actor_type="user",
            actor_id=user_id,
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
        )
    except Exception:
        pass

    # Try API key.
    hashed = hash_api_key(token)
    key = db.query(APIKey).filter(APIKey.key_hash == hashed, APIKey.is_active.is_(True)).first()
    if not key:
        _unauthorized("Invalid token or API key")
    return ActorContext(
        actor_type="api_key",
        actor_id=key.id,
        user_id=None,
        tenant_id=key.tenant_id,
        role=key.role,
    )


def require_roles(*roles: str):
    def _checker(ctx: ActorContext = Depends(get_actor_context)) -> ActorContext:
        if ctx.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return ctx
    return _checker


def get_current_user(ctx: ActorContext = Depends(get_actor_context), db: Session = Depends(get_db)):
    if not ctx.user_id:
        raise HTTPException(status_code=403, detail="User token required")
    user = db.get(User, ctx.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
