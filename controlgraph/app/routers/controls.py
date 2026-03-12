
import time
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.deps import get_actor_context, require_roles
from app.models import ControlDefinition, ControlRun, ExceptionCase
from app.schemas import ControlDefinitionIn, ControlRunIn
from app.services.common import audit
from app.services.control_service import execute_control_run

router = APIRouter(prefix="/v1", tags=["controls"])


def _run_in_background(run_id: str):
    db = SessionLocal()
    try:
        execute_control_run(db, run_id)
    finally:
        db.close()


@router.post("/controls")
def create_control(payload: ControlDefinitionIn, db: Session = Depends(get_db), ctx = Depends(require_roles("admin", "control_owner"))):
    row = ControlDefinition(tenant_id=ctx.tenant_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    audit(db, ctx.tenant_id, ctx.actor_type, ctx.actor_id, "create_control", "control_definition", row.id, {"name": row.name})
    return {"data": {"id": row.id, "name": row.name, "control_type": row.control_type}, "error": None}


@router.get("/controls")
def list_controls(db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    rows = db.query(ControlDefinition).filter(ControlDefinition.tenant_id == ctx.tenant_id).all()
    return {"data": [
        {
            "id": r.id,
            "name": r.name,
            "control_type": r.control_type,
            "severity": r.severity,
            "target_entity_id": r.target_entity_id,
        } for r in rows
    ], "error": None}


@router.post("/control-runs")
def create_control_run(payload: ControlRunIn, background_tasks: BackgroundTasks, db: Session = Depends(get_db), ctx = Depends(require_roles("admin", "control_owner", "data_owner"))):
    control = db.get(ControlDefinition, payload.control_definition_id)
    if not control or control.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="Control not found")
    row = ControlRun(
        tenant_id=ctx.tenant_id,
        control_definition_id=control.id,
        target_entity_type=control.target_entity_type,
        target_entity_id=control.target_entity_id,
        status="queued",
        triggered_by_type=ctx.actor_type,
        triggered_by_user_id=ctx.user_id,
        execution_context=payload.execution_context,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    background_tasks.add_task(_run_in_background, row.id)
    audit(db, ctx.tenant_id, ctx.actor_type, ctx.actor_id, "create_control_run", "control_run", row.id, {"control_definition_id": control.id})
    return {"data": {"id": row.id, "status": row.status}, "error": None}


@router.get("/control-runs")
def list_control_runs(db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    rows = db.query(ControlRun).filter(ControlRun.tenant_id == ctx.tenant_id).order_by(ControlRun.created_at.desc()).all()
    return {"data": [
        {
            "id": r.id,
            "control_definition_id": r.control_definition_id,
            "status": r.status,
            "summary": r.summary,
            "result_metrics": r.result_metrics,
            "created_at": str(r.created_at),
        } for r in rows
    ], "error": None}


@router.get("/control-runs/{run_id}")
def get_control_run(run_id: str, db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    row = db.get(ControlRun, run_id)
    if not row or row.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="Control run not found")
    exc = db.query(ExceptionCase).filter(ExceptionCase.control_run_id == row.id).first()
    return {"data": {
        "id": row.id,
        "status": row.status,
        "summary": row.summary,
        "result_metrics": row.result_metrics,
        "failure_sample": row.failure_sample,
        "linked_exception_id": exc.id if exc else None,
    }, "error": None}
