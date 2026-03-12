
import hashlib
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_actor_context, require_roles
from app.models import Webhook, WebhookDelivery
from app.schemas import WebhookIn

router = APIRouter(prefix="/v1", tags=["webhooks"])


@router.post("/webhooks")
def create_webhook(payload: WebhookIn, db: Session = Depends(get_db), ctx = Depends(require_roles("admin", "compliance_reviewer"))):
    secret_hash = hashlib.sha256(payload.target_url.encode()).hexdigest()[:32]
    row = Webhook(
        tenant_id=ctx.tenant_id,
        name=payload.name,
        target_url=payload.target_url,
        secret_hash=secret_hash,
        event_types=payload.event_types,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"data": {"id": row.id, "name": row.name, "event_types": row.event_types}, "error": None}


@router.get("/webhooks")
def list_webhooks(db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    rows = db.query(Webhook).filter(Webhook.tenant_id == ctx.tenant_id).all()
    return {"data": [{"id": r.id, "name": r.name, "target_url": r.target_url, "event_types": r.event_types} for r in rows], "error": None}


@router.get("/webhook-deliveries")
def list_deliveries(db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    rows = db.query(WebhookDelivery).filter(WebhookDelivery.tenant_id == ctx.tenant_id).order_by(WebhookDelivery.created_at.desc()).all()
    return {"data": [
        {
            "id": r.id,
            "webhook_id": r.webhook_id,
            "event_type": r.event_type,
            "success": r.success,
            "status_code": r.status_code,
            "response_text": r.response_text,
        } for r in rows
    ], "error": None}
