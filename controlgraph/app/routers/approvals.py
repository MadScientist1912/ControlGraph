
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_actor_context, require_roles
from app.models import Approval, ExceptionCase, ExceptionEvent
from app.schemas import ApprovalCreateIn, ApprovalDecisionIn
from app.services.alert_service import trigger_webhooks

router = APIRouter(prefix="/v1", tags=["approvals"])


@router.post("/approvals")
def create_approval(payload: ApprovalCreateIn, db: Session = Depends(get_db), ctx = Depends(require_roles("admin", "compliance_reviewer"))):
    row = Approval(
        tenant_id=ctx.tenant_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        approval_type=payload.approval_type,
        requested_by_user_id=ctx.user_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    trigger_webhooks(db, ctx.tenant_id, "approval.requested", {"approval_id": row.id, "entity_type": row.entity_type, "entity_id": row.entity_id})
    return {"data": {"id": row.id, "status": row.status}, "error": None}


@router.get("/approvals")
def list_approvals(db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    rows = db.query(Approval).filter(Approval.tenant_id == ctx.tenant_id).order_by(Approval.requested_at.desc()).all()
    return {"data": [
        {
            "id": r.id,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "approval_type": r.approval_type,
            "status": r.status,
        } for r in rows
    ], "error": None}


@router.post("/approvals/{approval_id}/approve")
def approve(approval_id: str, payload: ApprovalDecisionIn, db: Session = Depends(get_db), ctx = Depends(require_roles("admin", "compliance_reviewer"))):
    row = db.get(Approval, approval_id)
    if not row or row.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="Approval not found")
    row.status = "approved"
    row.decided_by_user_id = ctx.user_id
    row.decision_notes = payload.decision_notes
    row.decided_at = datetime.utcnow()
    db.add(row)
    db.commit()

    if row.entity_type == "exception":
        exc = db.get(ExceptionCase, row.entity_id)
        if exc:
            event = ExceptionEvent(
                tenant_id=ctx.tenant_id,
                exception_id=exc.id,
                event_type="override_approved",
                actor_user_id=ctx.user_id,
                payload={"approval_id": row.id, "decision_notes": payload.decision_notes},
            )
            db.add(event)
            db.commit()

    trigger_webhooks(db, ctx.tenant_id, "approval.approved", {"approval_id": row.id})
    return {"data": {"id": row.id, "status": row.status}, "error": None}


@router.post("/approvals/{approval_id}/reject")
def reject(approval_id: str, payload: ApprovalDecisionIn, db: Session = Depends(get_db), ctx = Depends(require_roles("admin", "compliance_reviewer"))):
    row = db.get(Approval, approval_id)
    if not row or row.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="Approval not found")
    row.status = "rejected"
    row.decided_by_user_id = ctx.user_id
    row.decision_notes = payload.decision_notes
    row.decided_at = datetime.utcnow()
    db.add(row)
    db.commit()
    trigger_webhooks(db, ctx.tenant_id, "approval.rejected", {"approval_id": row.id})
    return {"data": {"id": row.id, "status": row.status}, "error": None}
