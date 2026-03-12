
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_actor_context
from app.schemas import TenantRegisterIn, LoginIn, APIKeyCreateIn
from app.services.auth_service import register_tenant, login, create_api_key
from app.services.common import audit

router = APIRouter(prefix="/v1", tags=["auth"])


@router.post("/tenants/register")
def register(payload: TenantRegisterIn, db: Session = Depends(get_db)):
    result = register_tenant(
        db,
        tenant_name=payload.tenant_name,
        tenant_slug=payload.tenant_slug,
        admin_email=payload.admin_email,
        admin_full_name=payload.admin_full_name,
        admin_password=payload.admin_password,
    )
    return {"data": result, "error": None}


@router.post("/auth/login")
def login_route(payload: LoginIn, db: Session = Depends(get_db)):
    result = login(db, payload.email, payload.password, payload.tenant_slug)
    return {"data": result, "error": None}


@router.get("/auth/me")
def me(ctx = Depends(get_actor_context)):
    return {"data": {"actor_type": ctx.actor_type, "actor_id": ctx.actor_id, "user_id": ctx.user_id, "tenant_id": ctx.tenant_id, "role": ctx.role}, "error": None}


@router.post("/auth/api-keys")
def create_key(payload: APIKeyCreateIn, db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    result = create_api_key(db, tenant_id=ctx.tenant_id, name=payload.name, scopes=payload.scopes, role=payload.role)
    audit(db, ctx.tenant_id, ctx.actor_type, ctx.actor_id, "create_api_key", "api_key", result["id"], {"name": payload.name})
    return {"data": result, "error": None}
