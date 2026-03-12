
from collections import deque
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_actor_context, require_roles
from app.models import LineageEdge
from app.schemas import LineageEdgesIn

router = APIRouter(prefix="/v1", tags=["lineage"])


@router.post("/lineage/edges")
def create_edges(payload: LineageEdgesIn, db: Session = Depends(get_db), ctx = Depends(require_roles("admin", "control_owner", "data_owner"))):
    rows = []
    for edge in payload.edges:
        row = LineageEdge(tenant_id=ctx.tenant_id, **edge)
        db.add(row)
        rows.append(row)
    db.commit()
    return {"data": [{"id": r.id, "from": r.from_entity_id, "to": r.to_entity_id, "relationship_type": r.relationship_type} for r in rows], "error": None}


@router.get("/lineage/graph")
def graph(entity_type: str, entity_id: str, depth: int = 2, db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    queue = deque([(entity_type, entity_id, 0)])
    seen = set()
    nodes = set()
    edges_out = []

    while queue:
        e_type, e_id, level = queue.popleft()
        if (e_type, e_id) in seen or level > depth:
            continue
        seen.add((e_type, e_id))
        nodes.add((e_type, e_id))
        rows = db.query(LineageEdge).filter(
            LineageEdge.tenant_id == ctx.tenant_id,
            LineageEdge.from_entity_type == e_type,
            LineageEdge.from_entity_id == e_id
        ).all()
        for row in rows:
            edges_out.append({
                "id": row.id,
                "from_entity_type": row.from_entity_type,
                "from_entity_id": row.from_entity_id,
                "to_entity_type": row.to_entity_type,
                "to_entity_id": row.to_entity_id,
                "relationship_type": row.relationship_type,
            })
            queue.append((row.to_entity_type, row.to_entity_id, level + 1))
            nodes.add((row.to_entity_type, row.to_entity_id))

    return {"data": {
        "nodes": [{"entity_type": x[0], "entity_id": x[1]} for x in sorted(nodes)],
        "edges": edges_out,
    }, "error": None}
