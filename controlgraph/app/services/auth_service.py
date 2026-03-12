
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.security import hash_password, verify_password, create_access_token, generate_api_key
from app.models import Tenant, User, Membership, APIKey


def register_tenant(db: Session, tenant_name: str, tenant_slug: str, admin_email: str, admin_full_name: str, admin_password: str):
    if db.query(Tenant).filter(Tenant.slug == tenant_slug).first():
        raise HTTPException(status_code=400, detail="Tenant slug already exists")
    if db.query(User).filter(User.email == admin_email).first():
        raise HTTPException(status_code=400, detail="Admin email already exists")

    tenant = Tenant(name=tenant_name, slug=tenant_slug)
    user = User(email=admin_email, full_name=admin_full_name, password_hash=hash_password(admin_password))
    db.add_all([tenant, user])
    db.commit()
    db.refresh(tenant)
    db.refresh(user)

    membership = Membership(tenant_id=tenant.id, user_id=user.id, role="admin")
    db.add(membership)
    db.commit()

    token = create_access_token({"tenant_id": tenant.id, "user_id": user.id, "role": "admin"})
    return {"tenant": {"id": tenant.id, "name": tenant.name, "slug": tenant.slug}, "user": {"id": user.id, "email": user.email}, "access_token": token}


def login(db: Session, email: str, password: str, tenant_slug: str):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    membership = db.query(Membership).filter(Membership.user_id == user.id, Membership.tenant_id == tenant.id, Membership.status == "active").first()
    if not membership:
        raise HTTPException(status_code=403, detail="No access to tenant")

    token = create_access_token({"tenant_id": tenant.id, "user_id": user.id, "role": membership.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "tenant": {"id": tenant.id, "name": tenant.name, "slug": tenant.slug},
        "user": {"id": user.id, "email": user.email, "full_name": user.full_name},
        "role": membership.role,
    }


def create_api_key(db: Session, tenant_id: str, name: str, scopes: list[str], role: str):
    raw, prefix, digest = generate_api_key()
    record = APIKey(tenant_id=tenant_id, name=name, scopes=scopes, role=role, key_prefix=prefix, key_hash=digest)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "name": record.name, "key": raw, "prefix": record.key_prefix, "scopes": record.scopes, "role": record.role}
