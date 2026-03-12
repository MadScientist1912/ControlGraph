
from collections import deque
from sqlalchemy.orm import Session
from app.models import (
    LineageEdge,
    ReportDatasetLink,
    ReportObligationLink,
    Report,
    Obligation,
)


def impacted_reports_and_obligations(db: Session, tenant_id: str, entity_type: str, entity_id: str) -> dict:
    queue = deque([(entity_type, entity_id)])
    seen = set()
    reports = set()
    obligations = set()

    while queue:
        current_type, current_id = queue.popleft()
        if (current_type, current_id) in seen:
            continue
        seen.add((current_type, current_id))

        if current_type == "dataset":
            direct = db.query(ReportDatasetLink).filter(
                ReportDatasetLink.tenant_id == tenant_id,
                ReportDatasetLink.dataset_id == current_id
            ).all()
            for row in direct:
                reports.add(row.report_id)

        edges = db.query(LineageEdge).filter(
            LineageEdge.tenant_id == tenant_id,
            LineageEdge.from_entity_type == current_type,
            LineageEdge.from_entity_id == current_id
        ).all()
        for edge in edges:
            queue.append((edge.to_entity_type, edge.to_entity_id))

    if reports:
        links = db.query(ReportObligationLink).filter(
            ReportObligationLink.tenant_id == tenant_id,
            ReportObligationLink.report_id.in_(list(reports))
        ).all()
        obligations = {x.obligation_id for x in links}

    report_rows = db.query(Report).filter(Report.id.in_(list(reports))).all() if reports else []
    obligation_rows = db.query(Obligation).filter(Obligation.id.in_(list(obligations))).all() if obligations else []

    return {
        "report_ids": list(reports),
        "obligation_ids": list(obligations),
        "reports": [{"id": r.id, "name": r.name, "report_type": r.report_type} for r in report_rows],
        "obligations": [{"id": o.id, "code": o.code, "name": o.name, "framework": o.framework} for o in obligation_rows],
    }
