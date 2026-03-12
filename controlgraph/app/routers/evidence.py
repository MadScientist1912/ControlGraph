
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_actor_context, require_roles
from app.models import EvidencePack
from app.schemas import EvidencePackIn
from app.services.evidence_service import generate_evidence
from app.services.alert_service import trigger_webhooks

router = APIRouter(prefix="/v1", tags=["evidence"])


@router.post("/evidence-packs")
def create_pack(payload: EvidencePackIn, db: Session = Depends(get_db), ctx = Depends(require_roles("admin", "compliance_reviewer", "control_owner"))):
    row = EvidencePack(
        tenant_id=ctx.tenant_id,
        name=payload.name,
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
        generated_by_user_id=ctx.user_id,
        status="generating",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    row = generate_evidence(db, row)
    trigger_webhooks(db, ctx.tenant_id, "evidence_pack.ready", {"evidence_pack_id": row.id, "scope_type": row.scope_type, "scope_id": row.scope_id})
    return {"data": {"id": row.id, "status": row.status, "storage_uri": row.storage_uri}, "error": None}


@router.get("/evidence-packs")
def list_packs(db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    rows = db.query(EvidencePack).filter(EvidencePack.tenant_id == ctx.tenant_id).all()
    return {"data": [
        {
            "id": r.id,
            "name": r.name,
            "scope_type": r.scope_type,
            "scope_id": r.scope_id,
            "status": r.status,
            "storage_uri": r.storage_uri,
        } for r in rows
    ], "error": None}


@router.get("/evidence-packs/{pack_id}")
def get_pack(pack_id: str, db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    row = db.get(EvidencePack, pack_id)
    if not row or row.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="Evidence pack not found")
    return {"data": {
        "id": row.id,
        "name": row.name,
        "scope_type": row.scope_type,
        "scope_id": row.scope_id,
        "status": row.status,
        "storage_uri": row.storage_uri,
        "summary": row.summary,
    }, "error": None}
