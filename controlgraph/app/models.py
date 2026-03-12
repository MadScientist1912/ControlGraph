
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Float,
    String,
    Text,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def uid():
    return str(uuid.uuid4())


class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(String, primary_key=True, default=uid)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True)
    plan_type = Column(String, nullable=False, default="starter")
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    memberships = relationship("Membership", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=uid)
    email = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Membership(Base):
    __tablename__ = "memberships"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False, default="admin")
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", back_populates="memberships")
    user = relationship("User")

    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_membership_tenant_user"),)


class APIKey(Base):
    __tablename__ = "api_keys"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    key_prefix = Column(String, nullable=False)
    key_hash = Column(String, nullable=False)
    scopes = Column(JSON, nullable=False, default=list)
    role = Column(String, nullable=False, default="control_owner")
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DataSource(Base):
    __tablename__ = "data_sources"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)
    environment = Column(String, nullable=False, default="production")
    connection_metadata = Column(JSON, nullable=False, default=dict)
    owner_user_id = Column(String, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    data_source_id = Column(String, ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    qualified_name = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    criticality = Column(String, nullable=False, default="medium")
    classification = Column(String, nullable=False, default="internal")
    jurisdiction = Column(JSON, nullable=False, default=list)
    refresh_schedule = Column(String)
    owner_user_id = Column(String, ForeignKey("users.id"))
    steward_user_id = Column(String, ForeignKey("users.id"))
    tags = Column(JSON, nullable=False, default=list)
    description = Column(Text)
    actual_path = Column(String)
    actual_table = Column(String)
    actual_query = Column(Text)
    freshness_column = Column(String)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "qualified_name", name="uq_dataset_qualified_name"),)


class DatasetField(Base):
    __tablename__ = "dataset_fields"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    dataset_id = Column(String, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    data_type = Column(String, nullable=False)
    is_nullable = Column(Boolean, default=True, nullable=False)
    semantic_type = Column(String)
    description = Column(Text)
    ordinal_position = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("dataset_id", "name", name="uq_dataset_field_name"),)


class Pipeline(Base):
    __tablename__ = "pipelines"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    pipeline_type = Column(String, nullable=False)
    owner_user_id = Column(String, ForeignKey("users.id"))
    schedule = Column(String)
    metadata_json = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class LineageEdge(Base):
    __tablename__ = "lineage_edges"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    from_entity_type = Column(String, nullable=False)
    from_entity_id = Column(String, nullable=False)
    to_entity_type = Column(String, nullable=False)
    to_entity_id = Column(String, nullable=False)
    relationship_type = Column(String, nullable=False)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Report(Base):
    __tablename__ = "reports"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    report_type = Column(String, nullable=False)
    jurisdiction = Column(JSON, nullable=False, default=list)
    frequency = Column(String)
    owner_user_id = Column(String, ForeignKey("users.id"))
    description = Column(Text)
    metadata_json = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_report_name"),)


class Obligation(Base):
    __tablename__ = "obligations"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    framework = Column(String, nullable=False)
    jurisdiction = Column(JSON, nullable=False, default=list)
    description = Column(Text)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_obligation_code"),)


class ReportDatasetLink(Base):
    __tablename__ = "report_dataset_links"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    report_id = Column(String, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id = Column(String, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (UniqueConstraint("report_id", "dataset_id", name="uq_report_dataset"),)


class ReportObligationLink(Base):
    __tablename__ = "report_obligation_links"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    report_id = Column(String, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    obligation_id = Column(String, ForeignKey("obligations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (UniqueConstraint("report_id", "obligation_id", name="uq_report_obligation"),)


class ControlDefinition(Base):
    __tablename__ = "control_definitions"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    control_type = Column(String, nullable=False)
    target_entity_type = Column(String, nullable=False)
    target_entity_id = Column(String, nullable=False, index=True)
    severity = Column(String, nullable=False, default="medium")
    schedule = Column(String)
    rule_config = Column(JSON, nullable=False, default=dict)
    owner_user_id = Column(String, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ControlRun(Base):
    __tablename__ = "control_runs"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    control_definition_id = Column(String, ForeignKey("control_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    target_entity_type = Column(String, nullable=False)
    target_entity_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="queued")
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    triggered_by_type = Column(String, nullable=False, default="user")
    triggered_by_user_id = Column(String, ForeignKey("users.id"))
    summary = Column(Text)
    result_metrics = Column(JSON, nullable=False, default=dict)
    failure_sample = Column(JSON)
    execution_context = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ExceptionCase(Base):
    __tablename__ = "exceptions"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    control_run_id = Column(String, ForeignKey("control_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    severity = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open")
    title = Column(String, nullable=False)
    description = Column(Text)
    owner_user_id = Column(String, ForeignKey("users.id"))
    impacted_report_count = Column(Integer, nullable=False, default=0)
    impacted_obligation_count = Column(Integer, nullable=False, default=0)
    due_at = Column(DateTime)
    resolved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ExceptionEvent(Base):
    __tablename__ = "exception_events"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    exception_id = Column(String, ForeignKey("exceptions.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    actor_user_id = Column(String, ForeignKey("users.id"))
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Approval(Base):
    __tablename__ = "approvals"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False, index=True)
    approval_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    requested_by_user_id = Column(String, ForeignKey("users.id"))
    decided_by_user_id = Column(String, ForeignKey("users.id"))
    decision_notes = Column(Text)
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    decided_at = Column(DateTime)


class EvidencePack(Base):
    __tablename__ = "evidence_packs"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    scope_type = Column(String, nullable=False)
    scope_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="queued")
    generated_by_user_id = Column(String, ForeignKey("users.id"))
    storage_uri = Column(String)
    summary = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    generated_at = Column(DateTime)


class Webhook(Base):
    __tablename__ = "webhooks"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    target_url = Column(String, nullable=False)
    secret_hash = Column(String, nullable=False)
    event_types = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    webhook_id = Column(String, ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    status_code = Column(Integer)
    success = Column(Boolean, default=False, nullable=False)
    response_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=uid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_type = Column(String, nullable=False)
    actor_id = Column(String)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
