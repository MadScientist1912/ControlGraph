
from typing import Any, Optional, List, Dict
from pydantic import BaseModel, EmailStr, Field


class TenantRegisterIn(BaseModel):
    tenant_name: str
    tenant_slug: str
    admin_email: EmailStr
    admin_full_name: str
    admin_password: str = Field(min_length=8)


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: str


class APIKeyCreateIn(BaseModel):
    name: str
    scopes: list[str] = []
    role: str = "control_owner"


class DataSourceIn(BaseModel):
    name: str
    source_type: str
    environment: str = "production"
    connection_metadata: Dict[str, Any] = {}
    owner_user_id: Optional[str] = None


class DatasetIn(BaseModel):
    data_source_id: str
    name: str
    qualified_name: str
    domain: str
    criticality: str = "medium"
    classification: str = "internal"
    jurisdiction: list[str] = []
    refresh_schedule: Optional[str] = None
    owner_user_id: Optional[str] = None
    steward_user_id: Optional[str] = None
    tags: list[str] = []
    description: Optional[str] = None
    actual_path: Optional[str] = None
    actual_table: Optional[str] = None
    actual_query: Optional[str] = None
    freshness_column: Optional[str] = None


class DatasetFieldIn(BaseModel):
    name: str
    data_type: str
    is_nullable: bool = True
    semantic_type: Optional[str] = None
    description: Optional[str] = None
    ordinal_position: Optional[int] = None


class DatasetFieldsIn(BaseModel):
    fields: list[DatasetFieldIn]


class ReportIn(BaseModel):
    name: str
    report_type: str
    jurisdiction: list[str] = []
    frequency: Optional[str] = None
    owner_user_id: Optional[str] = None
    description: Optional[str] = None
    metadata_json: Dict[str, Any] = {}


class ObligationIn(BaseModel):
    code: str
    name: str
    framework: str
    jurisdiction: list[str] = []
    description: Optional[str] = None
    metadata_json: Dict[str, Any] = {}


class LinkIn(BaseModel):
    id: str


class ControlDefinitionIn(BaseModel):
    name: str
    control_type: str
    target_entity_type: str
    target_entity_id: str
    severity: str = "medium"
    schedule: Optional[str] = None
    rule_config: Dict[str, Any]
    owner_user_id: Optional[str] = None


class ControlRunIn(BaseModel):
    control_definition_id: str
    execution_context: Dict[str, Any] = {}


class ExceptionUpdateIn(BaseModel):
    status: Optional[str] = None
    owner_user_id: Optional[str] = None
    description: Optional[str] = None


class ExceptionCommentIn(BaseModel):
    comment: str


class OverrideRequestIn(BaseModel):
    reason: str


class ResolveIn(BaseModel):
    resolution_note: str


class ApprovalCreateIn(BaseModel):
    entity_type: str
    entity_id: str
    approval_type: str


class ApprovalDecisionIn(BaseModel):
    decision_notes: Optional[str] = None


class EvidencePackIn(BaseModel):
    name: str
    scope_type: str
    scope_id: str


class WebhookIn(BaseModel):
    name: str
    target_url: str
    event_types: list[str]


class LineageEdgesIn(BaseModel):
    edges: list[dict]
