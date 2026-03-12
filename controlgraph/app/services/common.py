
from sqlalchemy.orm import Session
from app.models import AuditLog


def audit(
    db: Session,
    tenant_id: str,
    actor_type: str,
    actor_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None,
    metadata: dict | None = None,
):
    row = AuditLog(
        tenant_id=tenant_id,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata or {},
    )
    db.add(row)
    db.commit()
