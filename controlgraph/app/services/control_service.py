
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy.orm import Session

from app.models import (
    ControlDefinition,
    ControlRun,
    DataSource,
    Dataset,
    DatasetField,
    ExceptionCase,
    ExceptionEvent,
)
from app.services.connector_service import load_dataset_frame, dataset_freshness_value
from app.services.impact_service import impacted_reports_and_obligations
from app.services.alert_service import trigger_webhooks


def _dataset_dict(dataset: Dataset) -> dict:
    return {
        "id": dataset.id,
        "actual_path": dataset.actual_path,
        "actual_table": dataset.actual_table,
        "actual_query": dataset.actual_query,
        "freshness_column": dataset.freshness_column,
        "qualified_name": dataset.qualified_name,
    }


def _source_dict(source: DataSource) -> dict:
    return {
        "id": source.id,
        "source_type": source.source_type,
        "connection_metadata": source.connection_metadata or {},
    }


def _coerce_datetime(value):
    if value is None:
        return None
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


def execute_control_run(db: Session, run_id: str):
    run = db.get(ControlRun, run_id)
    if not run:
        return None

    control = db.get(ControlDefinition, run.control_definition_id)
    if not control:
        run.status = "error"
        run.summary = "Control definition not found"
        db.commit()
        return run

    run.status = "running"
    run.started_at = datetime.utcnow()
    db.add(run)
    db.commit()

    try:
        if control.target_entity_type != "dataset":
            raise ValueError("v1 only executes dataset-targeted controls")

        dataset = db.get(Dataset, control.target_entity_id)
        if not dataset:
            raise ValueError("Target dataset not found")

        source = db.get(DataSource, dataset.data_source_id)
        if not source:
            raise ValueError("Data source not found")

        frame = load_dataset_frame(source.source_type, source.connection_metadata or {}, _dataset_dict(dataset))
        metrics = {}
        failure_sample = None
        passed = True
        summary = "Control passed"

        ctype = control.control_type
        cfg = control.rule_config or {}

        if ctype == "schema_drift":
            actual_cols = list(frame.columns)
            expected_cols = [x.name for x in db.query(DatasetField).filter(DatasetField.dataset_id == dataset.id).all()]
            missing = sorted([c for c in expected_cols if c not in actual_cols])
            extra = sorted([c for c in actual_cols if c not in expected_cols])
            metrics = {"expected_columns": expected_cols, "actual_columns": actual_cols, "missing_columns": missing, "extra_columns": extra}
            passed = len(missing) == 0 and len(extra) == 0
            summary = "Schema matches registered fields" if passed else "Schema drift detected"

        elif ctype == "completeness":
            required_fields = cfg.get("required_fields", [])
            max_null_pct = float(cfg.get("max_null_pct", 0.0))
            issues = []
            for field in required_fields:
                if field not in frame.columns:
                    issues.append({"field": field, "error": "missing"})
                    continue
                null_pct = float(frame[field].isna().mean()) if len(frame) else 0.0
                if null_pct > max_null_pct:
                    issues.append({"field": field, "null_pct": null_pct})
            metrics = {
                "row_count": int(len(frame)),
                "required_fields": required_fields,
                "issues": issues,
            }
            passed = len(issues) == 0
            failure_sample = frame[required_fields].head(5).to_dict(orient="records") if required_fields else None
            summary = "Completeness check passed" if passed else "Completeness issues detected"

        elif ctype == "threshold":
            field = cfg.get("field")
            if field not in frame.columns:
                raise ValueError(f"Field {field} not found")
            min_v = cfg.get("min_value")
            max_v = cfg.get("max_value")
            series = pd.to_numeric(frame[field], errors="coerce")
            actual_min = None if series.dropna().empty else float(series.min())
            actual_max = None if series.dropna().empty else float(series.max())
            passed = True
            if min_v is not None and actual_min is not None and actual_min < float(min_v):
                passed = False
            if max_v is not None and actual_max is not None and actual_max > float(max_v):
                passed = False
            metrics = {"field": field, "min_value": actual_min, "max_value": actual_max}
            summary = "Threshold check passed" if passed else "Threshold breach detected"

        elif ctype == "duplicate":
            key_fields = cfg.get("key_fields", [])
            missing_keys = [x for x in key_fields if x not in frame.columns]
            if missing_keys:
                raise ValueError(f"Missing key fields: {missing_keys}")
            dup_mask = frame.duplicated(subset=key_fields, keep=False)
            dup_count = int(dup_mask.sum())
            max_dup = int(cfg.get("max_duplicate_rows", 0))
            passed = dup_count <= max_dup
            metrics = {"key_fields": key_fields, "duplicate_rows": dup_count}
            failure_sample = frame.loc[dup_mask, key_fields].head(10).to_dict(orient="records") if dup_count else None
            summary = "Duplicate check passed" if passed else "Duplicate rows found"

        elif ctype == "freshness":
            freshness_ts = dataset_freshness_value(source.source_type, source.connection_metadata or {}, _dataset_dict(dataset), frame)
            freshness_ts = _coerce_datetime(freshness_ts)
            if freshness_ts is None:
                raise ValueError("Could not determine dataset freshness timestamp")
            now = datetime.now(timezone.utc)
            delay_minutes = (now - freshness_ts).total_seconds() / 60
            max_delay = float(cfg.get("max_delay_minutes", 60))
            passed = delay_minutes <= max_delay
            metrics = {"freshness_ts": freshness_ts.isoformat(), "delay_minutes": delay_minutes, "max_allowed_delay_minutes": max_delay}
            summary = "Freshness check passed" if passed else "Dataset is stale"

        elif ctype == "reconciliation":
            comparison_dataset_id = cfg.get("comparison_dataset_id")
            left_field = cfg.get("left_field")
            right_field = cfg.get("right_field", left_field)
            tolerance_abs = float(cfg.get("tolerance_abs", 0.0))

            comparison_dataset = db.get(Dataset, comparison_dataset_id)
            if not comparison_dataset:
                raise ValueError("Comparison dataset not found")
            comparison_source = db.get(DataSource, comparison_dataset.data_source_id)
            if not comparison_source:
                raise ValueError("Comparison source not found")

            other = load_dataset_frame(comparison_source.source_type, comparison_source.connection_metadata or {}, _dataset_dict(comparison_dataset))

            if left_field not in frame.columns or right_field not in other.columns:
                raise ValueError("Reconciliation field not found in one of the datasets")

            left_total = float(pd.to_numeric(frame[left_field], errors="coerce").fillna(0).sum())
            right_total = float(pd.to_numeric(other[right_field], errors="coerce").fillna(0).sum())
            variance = left_total - right_total
            passed = abs(variance) <= tolerance_abs
            metrics = {
                "left_total": left_total,
                "right_total": right_total,
                "variance": variance,
                "tolerance_abs": tolerance_abs,
            }
            summary = "Reconciliation passed" if passed else "Reconciliation variance exceeded tolerance"

        else:
            raise ValueError(f"Unsupported control type for execution: {ctype}")

        run.result_metrics = metrics
        run.failure_sample = failure_sample
        run.status = "passed" if passed else "failed"
        run.summary = summary
        run.finished_at = datetime.utcnow()
        db.add(run)
        db.commit()
        db.refresh(run)

        if not passed:
            impact = impacted_reports_and_obligations(db, run.tenant_id, "dataset", dataset.id)
            exc = ExceptionCase(
                tenant_id=run.tenant_id,
                control_run_id=run.id,
                severity=control.severity,
                title=f"{control.name} failed",
                description=summary,
                owner_user_id=control.owner_user_id or dataset.owner_user_id,
                impacted_report_count=len(impact["report_ids"]),
                impacted_obligation_count=len(impact["obligation_ids"]),
            )
            db.add(exc)
            db.commit()
            db.refresh(exc)

            event = ExceptionEvent(
                tenant_id=run.tenant_id,
                exception_id=exc.id,
                event_type="created",
                actor_user_id=run.triggered_by_user_id,
                payload={"control_run_id": run.id, "summary": summary},
            )
            db.add(event)
            db.commit()

            trigger_webhooks(db, run.tenant_id, "control_run.failed", {
                "control_run_id": run.id,
                "exception_id": exc.id,
                "severity": control.severity,
                "summary": summary,
            })
        else:
            trigger_webhooks(db, run.tenant_id, "control_run.passed", {
                "control_run_id": run.id,
                "summary": summary,
            })

        return run
    except Exception as exc:
        run.status = "error"
        run.summary = str(exc)
        run.finished_at = datetime.utcnow()
        db.add(run)
        db.commit()
        db.refresh(run)
        trigger_webhooks(db, run.tenant_id, "control_run.error", {
            "control_run_id": run.id,
            "error": str(exc),
        })
        return run
