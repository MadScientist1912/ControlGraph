
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_actor_context
from app.models import Dataset, ControlDefinition, ControlRun, ExceptionCase, Report, Obligation, EvidencePack

router = APIRouter(prefix="/v1", tags=["dashboard"])


@router.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    tenant_id = ctx.tenant_id
    runs = db.query(ControlRun).filter(ControlRun.tenant_id == tenant_id).all()
    exceptions = db.query(ExceptionCase).filter(ExceptionCase.tenant_id == tenant_id).all()
    return {"data": {
        "datasets": db.query(Dataset).filter(Dataset.tenant_id == tenant_id).count(),
        "controls": db.query(ControlDefinition).filter(ControlDefinition.tenant_id == tenant_id).count(),
        "control_runs": len(runs),
        "passed_runs": len([x for x in runs if x.status == "passed"]),
        "failed_runs": len([x for x in runs if x.status == "failed"]),
        "error_runs": len([x for x in runs if x.status == "error"]),
        "exceptions_open": len([x for x in exceptions if x.status not in {"resolved", "closed"}]),
        "exceptions_resolved": len([x for x in exceptions if x.status in {"resolved", "accepted_override", "closed"}]),
        "reports": db.query(Report).filter(Report.tenant_id == tenant_id).count(),
        "obligations": db.query(Obligation).filter(Obligation.tenant_id == tenant_id).count(),
        "evidence_packs": db.query(EvidencePack).filter(EvidencePack.tenant_id == tenant_id).count(),
    }, "error": None}
