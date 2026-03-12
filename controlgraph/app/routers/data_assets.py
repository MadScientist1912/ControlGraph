
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_actor_context, require_roles
from app.models import DataSource, Dataset, DatasetField, ReportDatasetLink
from app.schemas import DataSourceIn, DatasetIn, DatasetFieldsIn, LinkIn
from app.services.common import audit

router = APIRouter(prefix="/v1", tags=["data-assets"])


@router.post("/data-sources")
def create_data_source(payload: DataSourceIn, db: Session = Depends(get_db), ctx = Depends(require_roles("admin", "data_owner", "control_owner"))):
    row = DataSource(tenant_id=ctx.tenant_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    audit(db, ctx.tenant_id, ctx.actor_type, ctx.actor_id, "create_data_source", "data_source", row.id, {"name": row.name})
    return {"data": {"id": row.id, "name": row.name, "source_type": row.source_type}, "error": None}


@router.get("/data-sources")
def list_data_sources(db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    rows = db.query(DataSource).filter(DataSource.tenant_id == ctx.tenant_id).all()
    return {"data": [{"id": r.id, "name": r.name, "source_type": r.source_type, "environment": r.environment, "connection_metadata": r.connection_metadata} for r in rows], "error": None}


@router.post("/datasets")
def create_dataset(payload: DatasetIn, db: Session = Depends(get_db), ctx = Depends(require_roles("admin", "data_owner", "control_owner"))):
    source = db.get(DataSource, payload.data_source_id)
    if not source or source.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="Data source not found")
    row = Dataset(tenant_id=ctx.tenant_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    audit(db, ctx.tenant_id, ctx.actor_type, ctx.actor_id, "create_dataset", "dataset", row.id, {"qualified_name": row.qualified_name})
    return {"data": {"id": row.id, "name": row.name, "qualified_name": row.qualified_name}, "error": None}


@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    rows = db.query(Dataset).filter(Dataset.tenant_id == ctx.tenant_id).all()
    return {"data": [
        {
            "id": r.id,
            "name": r.name,
            "qualified_name": r.qualified_name,
            "domain": r.domain,
            "criticality": r.criticality,
            "actual_path": r.actual_path,
            "actual_table": r.actual_table,
            "freshness_column": r.freshness_column,
        } for r in rows
    ], "error": None}


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: str, db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    row = db.get(Dataset, dataset_id)
    if not row or row.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"data": {
        "id": row.id,
        "data_source_id": row.data_source_id,
        "name": row.name,
        "qualified_name": row.qualified_name,
        "domain": row.domain,
        "criticality": row.criticality,
        "classification": row.classification,
        "jurisdiction": row.jurisdiction,
        "refresh_schedule": row.refresh_schedule,
        "owner_user_id": row.owner_user_id,
        "tags": row.tags,
        "description": row.description,
        "actual_path": row.actual_path,
        "actual_table": row.actual_table,
        "actual_query": row.actual_query,
        "freshness_column": row.freshness_column,
    }, "error": None}


@router.post("/datasets/{dataset_id}/fields")
def add_fields(dataset_id: str, payload: DatasetFieldsIn, db: Session = Depends(get_db), ctx = Depends(require_roles("admin", "data_owner", "control_owner"))):
    ds = db.get(Dataset, dataset_id)
    if not ds or ds.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="Dataset not found")
    rows = []
    for field in payload.fields:
        row = DatasetField(tenant_id=ctx.tenant_id, dataset_id=dataset_id, **field.model_dump())
        db.add(row)
        rows.append(row)
    db.commit()
    return {"data": [{"id": r.id, "name": r.name, "data_type": r.data_type} for r in rows], "error": None}


@router.get("/datasets/{dataset_id}/fields")
def list_fields(dataset_id: str, db: Session = Depends(get_db), ctx = Depends(get_actor_context)):
    ds = db.get(Dataset, dataset_id)
    if not ds or ds.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="Dataset not found")
    rows = db.query(DatasetField).filter(DatasetField.dataset_id == dataset_id).all()
    return {"data": [{"id": r.id, "name": r.name, "data_type": r.data_type, "semantic_type": r.semantic_type} for r in rows], "error": None}


@router.post("/reports/{report_id}/datasets")
def link_dataset_to_report(report_id: str, payload: LinkIn, db: Session = Depends(get_db), ctx = Depends(require_roles("admin", "control_owner", "compliance_reviewer"))):
    row = ReportDatasetLink(tenant_id=ctx.tenant_id, report_id=report_id, dataset_id=payload.id)
    db.add(row)
    db.commit()
    return {"data": {"report_id": report_id, "dataset_id": payload.id}, "error": None}
