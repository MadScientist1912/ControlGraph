
import json
import os
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import EvidencePack, ControlRun, ExceptionCase, Approval
from app.services.impact_service import impacted_reports_and_obligations


def generate_evidence(db: Session, pack: EvidencePack):
    settings = get_settings()
    os.makedirs(settings.EVIDENCE_DIR, exist_ok=True)

    payload = {
        "pack_id": pack.id,
        "name": pack.name,
        "scope_type": pack.scope_type,
        "scope_id": pack.scope_id,
        "generated_at": datetime.utcnow().isoformat(),
    }

    if pack.scope_type == "exception":
        exc = db.get(ExceptionCase, pack.scope_id)
        runs = []
        if exc:
            run = db.get(ControlRun, exc.control_run_id)
            if run:
                runs.append({
                    "id": run.id,
                    "status": run.status,
                    "summary": run.summary,
                    "result_metrics": run.result_metrics,
                    "created_at": str(run.created_at),
                })
        approvals = db.query(Approval).filter(
            Approval.tenant_id == pack.tenant_id,
            Approval.entity_type == "exception",
            Approval.entity_id == pack.scope_id
        ).all()
        payload["exception"] = None if not exc else {
            "id": exc.id,
            "status": exc.status,
            "severity": exc.severity,
            "title": exc.title,
            "description": exc.description,
            "impacted_report_count": exc.impacted_report_count,
            "impacted_obligation_count": exc.impacted_obligation_count,
        }
        payload["control_runs"] = runs
        payload["approvals"] = [
            {
                "id": a.id,
                "approval_type": a.approval_type,
                "status": a.status,
                "decision_notes": a.decision_notes,
            }
            for a in approvals
        ]
    elif pack.scope_type == "dataset":
        payload["impact"] = impacted_reports_and_obligations(db, pack.tenant_id, "dataset", pack.scope_id)

    filename = f"{pack.id}.json"
    path = os.path.join(settings.EVIDENCE_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    pack.storage_uri = path
    pack.status = "ready"
    pack.generated_at = datetime.utcnow()
    pack.summary = {
        "scope_type": pack.scope_type,
        "scope_id": pack.scope_id,
        "path": path,
    }
    db.add(pack)
    db.commit()
    db.refresh(pack)
    return pack
