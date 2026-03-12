
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_actor_context, require_roles
from app.models import ExceptionCase, ExceptionEvent, Approval, ControlRun
from app.schemas import ExceptionUpdateIn, ExceptionCommentIn, OverrideRequestIn, ResolveIn
from app.services.common import audit
from app.services.alert_service import trigger_webhooks

router = APIRouter(prefix="/v1", tags=["exceptions"])


@router.get("/exceptions")
def list_exceptions(db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    rows = db.query(ExceptionCase).filter(ExceptionCase.tenant_id == ctx.tenant_id).order_by(ExceptionCase.created_at.desc()).all()
    return {"data": [
        {
            "id": r.id,
            "status": r.status,
            "severity": r.severity,
            "title": r.title,
            "description": r.description,
            "owner_user_id": r.owner_user_id,
            "impacted_report_count": r.impacted_report_count,
            "impacted_obligation_count": r.impacted_obligation_count,
        } for r in rows
    ], "error": None}


@router.get("/exceptions/{exception_id}")
def get_exception(exception_id: str, db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    row = db.get(ExceptionCase, exception_id)
    if not row or row.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="Exception not found")
    return {"data": {
        "id": row.id,
        "status": row.status,
        "severity": row.severity,
        "title": row.title,
        "description": row.description,
        "owner_user_id": row.owner_user_id,
        "created_at": str(row.created_at),
    }, "error": None}


@router.patch("/exceptions/{exception_id}")
def update_exception(exception_id: str, payload: ExceptionUpdateIn, db: Session = Depends(get_db), ctx = Depends(require_roles("admin", "control_owner", "compliance_reviewer"))):
    row = db.get(ExceptionCase, exception_id)
    if not row or row.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="Exception not found")
    updates = payload.model_dump(exclude_none=True)
    for k, v in updates.items():
        setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.add(row)
    db.commit()
    event = ExceptionEvent(
        tenant_id=ctx.tenant_id,
        exception_id=row.id,
        event_type="status_changed",
        actor_user_id=ctx.user_id,
        payload=updates,
    )
    db.add(event)
    db.commit()
    audit(db, ctx.tenant_id, ctx.actor_type, ctx.actor_id, "update_exception", "exception", row.id, updates)
    return {"data": {"id": row.id, "status": row.status}, "error": None}


@router.post("/exceptions/{exception_id}/comment")
def comment_exception(exception_id: str, payload: ExceptionCommentIn, db: Session = Depends(get_db), ctx = Depends(require_roles("admin", "control_owner", "data_owner", "compliance_reviewer", "auditor"))):
    row = db.get(ExceptionCase, exception_id)
    if not row or row.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="Exception not found")
    event = ExceptionEvent(
        tenant_id=ctx.tenant_id,
        exception_id=row.id,
        event_type="commented",
        actor_user_id=ctx.user_id,
        payload={"comment": payload.comment},
    )
    db.add(event)
    db.commit()
    return {"data": {"exception_id": row.id, "event_type": "commented"}, "error": None}


@router.get("/exceptions/{exception_id}/events")
def get_exception_events(exception_id: str, db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    row = db.get(ExceptionCase, exception_id)
    if not row or row.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="Exception not found")
    events = db.query(ExceptionEvent).filter(ExceptionEvent.exception_id == exception_id).order_by(ExceptionEvent.created_at.asc()).all()
    return {"data": [
        {
            "id": e.id,
            "event_type": e.event_type,
            "actor_user_id": e.actor_user_id,
            "payload": e.payload,
            "created_at": str(e.created_at),
        } for e in events
    ], "error": None}


@router.post("/exceptions/{exception_id}/request-override")
def request_override(exception_id: str, payload: OverrideRequestIn, db: Session = Depends(get_db), ctx = Depends(require_roles("admin", "control_owner", "compliance_reviewer"))):
    row = db.get(ExceptionCase, exception_id)
    if not row or row.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="Exception not found")
    approval = Approval(
        tenant_id=ctx.tenant_id,
        entity_type="exception",
        entity_id=row.id,
        approval_type="override",
        requested_by_user_id=ctx.user_id,
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)

    event = ExceptionEvent(
        tenant_id=ctx.tenant_id,
        exception_id=row.id,
        event_type="override_requested",
        actor_user_id=ctx.user_id,
        payload={"reason": payload.reason, "approval_id": approval.id},
    )
    db.add(event)
    db.commit()
    trigger_webhooks(db, ctx.tenant_id, "approval.requested", {"approval_id": approval.id, "entity_type": "exception", "entity_id": row.id})
    return {"data": {"approval_id": approval.id, "status": approval.status}, "error": None}


@router.post("/exceptions/{exception_id}/resolve")
def resolve_exception(exception_id: str, payload: ResolveIn, db: Session = Depends(get_db), ctx = Depends(require_roles("admin", "control_owner", "compliance_reviewer"))):
    row = db.get(ExceptionCase, exception_id)
    if not row or row.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="Exception not found")
    control_run = db.get(ControlRun, row.control_run_id)
    approved_override = db.query(Approval).filter(
        Approval.tenant_id == ctx.tenant_id,
        Approval.entity_type == "exception",
        Approval.entity_id == row.id,
        Approval.approval_type == "override",
        Approval.status == "approved",
    ).first()

    if control_run and control_run.status != "passed" and not approved_override:
        raise HTTPException(status_code=400, detail="Exception cannot be resolved until control passes or override is approved")

    row.status = "resolved" if control_run and control_run.status == "passed" else "accepted_override"
    row.resolved_at = datetime.utcnow()
    row.updated_at = datetime.utcnow()
    db.add(row)
    db.commit()

    event = ExceptionEvent(
        tenant_id=ctx.tenant_id,
        exception_id=row.id,
        event_type="resolved",
        actor_user_id=ctx.user_id,
        payload={"resolution_note": payload.resolution_note},
    )
    db.add(event)
    db.commit()
    trigger_webhooks(db, ctx.tenant_id, "exception.status_changed", {"exception_id": row.id, "status": row.status})
    audit(db, ctx.tenant_id, ctx.actor_type, ctx.actor_id, "resolve_exception", "exception", row.id, {"status": row.status})
    return {"data": {"id": row.id, "status": row.status}, "error": None}
