
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_actor_context, require_roles
from app.models import Report, Obligation, ReportObligationLink, ReportDatasetLink, ControlDefinition, ControlRun, ExceptionCase
from app.schemas import ReportIn, ObligationIn, LinkIn
from app.services.common import audit
from app.services.impact_service import impacted_reports_and_obligations

router = APIRouter(prefix="/v1", tags=["governance"])


@router.post("/reports")
def create_report(payload: ReportIn, db: Session = Depends(get_db), ctx = Depends(require_roles("admin", "control_owner", "compliance_reviewer"))):
    row = Report(tenant_id=ctx.tenant_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    audit(db, ctx.tenant_id, ctx.actor_type, ctx.actor_id, "create_report", "report", row.id, {"name": row.name})
    return {"data": {"id": row.id, "name": row.name}, "error": None}


@router.get("/reports")
def list_reports(db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    rows = db.query(Report).filter(Report.tenant_id == ctx.tenant_id).all()
    return {"data": [{"id": r.id, "name": r.name, "report_type": r.report_type, "frequency": r.frequency} for r in rows], "error": None}


@router.post("/obligations")
def create_obligation(payload: ObligationIn, db: Session = Depends(get_db), ctx = Depends(require_roles("admin", "compliance_reviewer"))):
    row = Obligation(tenant_id=ctx.tenant_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    audit(db, ctx.tenant_id, ctx.actor_type, ctx.actor_id, "create_obligation", "obligation", row.id, {"code": row.code})
    return {"data": {"id": row.id, "code": row.code, "name": row.name}, "error": None}


@router.get("/obligations")
def list_obligations(db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    rows = db.query(Obligation).filter(Obligation.tenant_id == ctx.tenant_id).all()
    return {"data": [{"id": r.id, "code": r.code, "name": r.name, "framework": r.framework} for r in rows], "error": None}


@router.post("/reports/{report_id}/obligations")
def link_obligation_to_report(report_id: str, payload: LinkIn, db: Session = Depends(get_db), ctx = Depends(require_roles("admin", "compliance_reviewer"))):
    row = ReportObligationLink(tenant_id=ctx.tenant_id, report_id=report_id, obligation_id=payload.id)
    db.add(row)
    db.commit()
    return {"data": {"report_id": report_id, "obligation_id": payload.id}, "error": None}


@router.get("/reports/{report_id}/impact")
def report_impact(report_id: str, db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    report = db.get(Report, report_id)
    if not report or report.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="Report not found")

    dataset_links = db.query(ReportDatasetLink).filter(
        ReportDatasetLink.tenant_id == ctx.tenant_id,
        ReportDatasetLink.report_id == report_id
    ).all()
    dataset_ids = [x.dataset_id for x in dataset_links]

    controls = db.query(ControlDefinition).filter(
        ControlDefinition.tenant_id == ctx.tenant_id,
        ControlDefinition.target_entity_type == "dataset",
        ControlDefinition.target_entity_id.in_(dataset_ids) if dataset_ids else False
    ).all() if dataset_ids else []

    control_ids = [x.id for x in controls]
    runs = db.query(ControlRun).filter(
        ControlRun.tenant_id == ctx.tenant_id,
        ControlRun.control_definition_id.in_(control_ids) if control_ids else False
    ).all() if control_ids else []

    run_ids = [x.id for x in runs]
    exceptions = db.query(ExceptionCase).filter(
        ExceptionCase.tenant_id == ctx.tenant_id,
        ExceptionCase.control_run_id.in_(run_ids) if run_ids else False
    ).all() if run_ids else []

    obligation_links = db.query(ReportObligationLink).filter(
        ReportObligationLink.tenant_id == ctx.tenant_id,
        ReportObligationLink.report_id == report_id
    ).all()

    return {"data": {
        "report": {"id": report.id, "name": report.name},
        "dataset_ids": dataset_ids,
        "control_ids": control_ids,
        "run_count": len(runs),
        "open_exception_count": len([e for e in exceptions if e.status not in {"resolved", "closed"}]),
        "obligation_ids": [x.obligation_id for x in obligation_links],
    }, "error": None}
