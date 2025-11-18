"""
Pydantic schemas for Multi-Tenant API request/response validation
Supports UUID primary keys and PostgreSQL-specific types
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from uuid import UUID


# ============================================================================
# ENUMS (matching models_multitenant.py)
# ============================================================================

class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IncidentStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"
    FALSE_POSITIVE = "false_positive"


class CaseStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"


class AlertStatus(str, Enum):
    NEW = "new"
    TRIAGED = "triaged"
    IN_CASE = "in_case"
    IGNORED = "ignored"
    RESOLVED = "resolved"


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    HUBSEC_ANALYST = "hubsec_analyst"
    TENANT_ADMIN = "tenant_admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class AssetType(str, Enum):
    SERVER = "server"
    WORKSTATION = "workstation"
    NETWORK_DEVICE = "network_device"
    DATABASE = "database"
    APPLICATION = "application"
    CONTAINER = "container"
    CLOUD_RESOURCE = "cloud_resource"
    OTHER = "other"


class IntegrationType(str, Enum):
    WAZUH = "wazuh"
    IRIS = "iris"
    JIRA = "jira"
    SERVICENOW = "servicenow"
    FORTIGATE = "fortigate"
    PALO_ALTO = "palo_alto"
    CROWDSTRIKE = "crowdstrike"
    SENTINEL_ONE = "sentinel_one"
    SPLUNK = "splunk"
    ELASTICSEARCH = "elasticsearch"
    CUSTOM = "custom"


class PlaybookStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# TENANT SCHEMAS
# ============================================================================

class TenantBase(BaseModel):
    """Base tenant schema"""
    name: str = Field(..., min_length=3, max_length=255)
    code: str = Field(..., min_length=2, max_length=50)
    industry: Optional[str] = Field(None, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    subscription_tier: Optional[str] = Field(None, max_length=50)
    settings: Optional[Dict[str, Any]] = None


class TenantCreate(TenantBase):
    """Schema for creating a tenant"""
    is_active: bool = True


class TenantUpdate(BaseModel):
    """Schema for updating a tenant"""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    industry: Optional[str] = None
    region: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: Optional[bool] = None
    subscription_tier: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class TenantInDB(TenantBase):
    """Tenant schema as stored in database"""
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Tenant(TenantInDB):
    """Public tenant schema (response)"""
    pass


# ============================================================================
# SOURCE SYSTEM SCHEMAS
# ============================================================================

class SourceSystemBase(BaseModel):
    """Base source system schema"""
    name: str = Field(..., min_length=3, max_length=255)
    type: IntegrationType
    description: Optional[str] = None
    base_url: Optional[str] = Field(None, max_length=500)
    auth_type: Optional[str] = Field(None, max_length=50)
    auth_config: Optional[Dict[str, Any]] = None  # Encrypted credentials
    config: Optional[Dict[str, Any]] = None


class SourceSystemCreate(SourceSystemBase):
    """Schema for creating a source system"""
    tenant_id: UUID
    is_active: bool = True


class SourceSystemUpdate(BaseModel):
    """Schema for updating a source system"""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    base_url: Optional[str] = None
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    sync_status: Optional[str] = None
    sync_error: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class SourceSystemInDB(SourceSystemBase):
    """Source system schema as stored in database"""
    id: UUID
    tenant_id: UUID
    is_active: bool
    last_sync_at: Optional[datetime] = None
    sync_status: Optional[str] = None
    sync_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SourceSystem(SourceSystemInDB):
    """Public source system schema (response)"""
    pass


# ============================================================================
# ASSET SCHEMAS
# ============================================================================

class AssetBase(BaseModel):
    """Base asset schema"""
    hostname: Optional[str] = Field(None, max_length=255)
    ip_address: Optional[str] = None  # INET stored as string in Pydantic
    mac_address: Optional[str] = Field(None, max_length=17)
    asset_type: AssetType
    criticality: SeverityLevel = SeverityLevel.MEDIUM
    os: Optional[str] = Field(None, max_length=100)
    os_version: Optional[str] = Field(None, max_length=50)
    environment: Optional[str] = Field(None, max_length=50)
    owner: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = None
    meta_data: Optional[Dict[str, Any]] = None


class AssetCreate(AssetBase):
    """Schema for creating an asset"""
    tenant_id: UUID
    is_active: bool = True


class AssetUpdate(BaseModel):
    """Schema for updating an asset"""
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    asset_type: Optional[AssetType] = None
    criticality: Optional[SeverityLevel] = None
    os: Optional[str] = None
    os_version: Optional[str] = None
    environment: Optional[str] = None
    owner: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None
    tags: Optional[List[str]] = None
    meta_data: Optional[Dict[str, Any]] = None


class AssetInDB(AssetBase):
    """Asset schema as stored in database"""
    id: UUID
    tenant_id: UUID
    is_active: bool
    last_seen: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Asset(AssetInDB):
    """Public asset schema (response)"""
    pass


# ============================================================================
# PLAYBOOK SCHEMAS
# ============================================================================

class PlaybookBase(BaseModel):
    """Base playbook schema"""
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    incident_type: Optional[str] = Field(None, max_length=100)
    definition: Dict[str, Any]  # JSONB with steps/actions
    version: str = "1.0"
    is_active: bool = True
    tags: Optional[List[str]] = None


class PlaybookCreate(PlaybookBase):
    """Schema for creating a playbook"""
    tenant_id: Optional[UUID] = None  # NULL = global playbook
    created_by: Optional[UUID] = None


class PlaybookUpdate(BaseModel):
    """Schema for updating a playbook"""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    incident_type: Optional[str] = None
    definition: Optional[Dict[str, Any]] = None
    version: Optional[str] = None
    is_active: Optional[bool] = None
    tags: Optional[List[str]] = None


class PlaybookInDB(PlaybookBase):
    """Playbook schema as stored in database"""
    id: UUID
    tenant_id: Optional[UUID] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Playbook(PlaybookInDB):
    """Public playbook schema (response)"""
    pass


# ============================================================================
# CASE PLAYBOOK SCHEMAS
# ============================================================================

class CasePlaybookBase(BaseModel):
    """Base case playbook schema"""
    status: PlaybookStatus = PlaybookStatus.NOT_STARTED
    current_step: int = 0
    total_steps: Optional[int] = None
    completed_steps: Optional[Dict[str, Any]] = None
    meta_data: Optional[Dict[str, Any]] = None


class CasePlaybookCreate(CasePlaybookBase):
    """Schema for creating a case playbook"""
    case_id: UUID
    playbook_id: UUID
    started_by: Optional[UUID] = None


class CasePlaybookUpdate(BaseModel):
    """Schema for updating a case playbook"""
    status: Optional[PlaybookStatus] = None
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    completed_steps: Optional[Dict[str, Any]] = None
    meta_data: Optional[Dict[str, Any]] = None


class CasePlaybookInDB(CasePlaybookBase):
    """Case playbook schema as stored in database"""
    id: UUID
    case_id: UUID
    playbook_id: UUID
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    started_by: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class CasePlaybook(CasePlaybookInDB):
    """Public case playbook schema (response)"""
    playbook: Optional[Playbook] = None


# ============================================================================
# CASE EXTERNAL REF SCHEMAS
# ============================================================================

class CaseExternalRefBase(BaseModel):
    """Base case external reference schema"""
    system_type: str = Field(..., max_length=50)
    external_id: str = Field(..., max_length=255)
    url: Optional[str] = Field(None, max_length=500)


class CaseExternalRefCreate(CaseExternalRefBase):
    """Schema for creating a case external reference"""
    case_id: UUID


class CaseExternalRefUpdate(BaseModel):
    """Schema for updating a case external reference"""
    url: Optional[str] = None
    sync_status: Optional[str] = None


class CaseExternalRefInDB(CaseExternalRefBase):
    """Case external reference schema as stored in database"""
    id: UUID
    case_id: UUID
    created_at: datetime
    synced_at: Optional[datetime] = None
    sync_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CaseExternalRef(CaseExternalRefInDB):
    """Public case external reference schema (response)"""
    pass


# ============================================================================
# USER SCHEMAS
# ============================================================================

class UserBase(BaseModel):
    """Base user schema"""
    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., max_length=255)
    full_name: Optional[str] = Field(None, max_length=255)
    role: UserRole = UserRole.ANALYST


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=8)
    tenant_ids: Optional[List[UUID]] = None  # Tenants to assign user to


class UserUpdate(BaseModel):
    """Schema for updating user"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    tenant_ids: Optional[List[UUID]] = None


class UserInDB(UserBase):
    """User schema as stored in database"""
    id: UUID
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class User(UserInDB):
    """Public user schema (response)"""
    tenants: List[Tenant] = []


# ============================================================================
# ALERT SCHEMAS
# ============================================================================

class AlertBase(BaseModel):
    """Base alert schema"""
    source_id: str = Field(..., max_length=255)
    rule_id: Optional[str] = Field(None, max_length=100)
    rule_description: Optional[str] = None
    severity: SeverityLevel
    event_type: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)


class AlertCreate(AlertBase):
    """Schema for creating an alert"""
    tenant_id: UUID
    source_system_id: Optional[UUID] = None
    asset_id: Optional[UUID] = None
    timestamp: datetime
    src_ip: Optional[str] = None  # INET as string
    dst_ip: Optional[str] = None  # INET as string
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    protocol: Optional[str] = Field(None, max_length=20)
    hostname: Optional[str] = Field(None, max_length=255)
    agent_id: Optional[str] = Field(None, max_length=100)
    agent_name: Optional[str] = Field(None, max_length=255)
    username: Optional[str] = Field(None, max_length=255)
    filename: Optional[str] = Field(None, max_length=500)
    file_path: Optional[str] = None
    file_hash: Optional[str] = Field(None, max_length=128)
    raw_data: Optional[Dict[str, Any]] = None
    normalized_data: Optional[Dict[str, Any]] = None


class AlertUpdate(BaseModel):
    """Schema for updating an alert"""
    status: Optional[AlertStatus] = None
    severity: Optional[SeverityLevel] = None
    normalized_data: Optional[Dict[str, Any]] = None


class AlertInDB(AlertBase):
    """Alert schema as stored in database"""
    id: UUID
    tenant_id: UUID
    source_system_id: Optional[UUID] = None
    asset_id: Optional[UUID] = None
    status: AlertStatus
    timestamp: datetime
    created_at: datetime
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    protocol: Optional[str] = None
    hostname: Optional[str] = None
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    username: Optional[str] = None
    filename: Optional[str] = None
    file_path: Optional[str] = None
    file_hash: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    normalized_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class Alert(AlertInDB):
    """Public alert schema (response)"""
    asset: Optional[Asset] = None
    source_system: Optional[SourceSystem] = None


# ============================================================================
# COMMENT SCHEMAS
# ============================================================================

class CommentBase(BaseModel):
    """Base comment schema"""
    content: str = Field(..., min_length=1)


class CommentCreate(CommentBase):
    """Schema for creating a comment"""
    incident_id: Optional[UUID] = None
    case_id: Optional[UUID] = None


class CommentInDB(CommentBase):
    """Comment schema as stored in database"""
    id: UUID
    incident_id: Optional[UUID] = None
    case_id: Optional[UUID] = None
    author_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Comment(CommentInDB):
    """Public comment schema (response)"""
    author: Optional[User] = None


# ============================================================================
# ACTIVITY SCHEMAS
# ============================================================================

class ActivityBase(BaseModel):
    """Base activity schema"""
    action: str = Field(..., max_length=100)
    description: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None


class ActivityCreate(ActivityBase):
    """Schema for creating an activity"""
    case_id: UUID
    user_id: UUID


class ActivityInDB(ActivityBase):
    """Activity schema as stored in database"""
    id: UUID
    case_id: UUID
    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Activity(ActivityInDB):
    """Public activity schema (response)"""
    user: Optional[User] = None


# ============================================================================
# CASE SCHEMAS
# ============================================================================

class CaseBase(BaseModel):
    """Base case schema"""
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    priority: SeverityLevel
    tags: Optional[List[str]] = None


class CaseCreate(CaseBase):
    """Schema for creating a case"""
    tenant_id: UUID
    incident_id: UUID
    assigned_user_ids: Optional[List[UUID]] = None


class CaseUpdate(BaseModel):
    """Schema for updating a case"""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    status: Optional[CaseStatus] = None
    priority: Optional[SeverityLevel] = None
    resolution: Optional[str] = None
    tags: Optional[List[str]] = None
    assigned_user_ids: Optional[List[UUID]] = None
    meta_data: Optional[Dict[str, Any]] = None


class CaseInDB(CaseBase):
    """Case schema as stored in database"""
    id: UUID
    tenant_id: UUID
    incident_id: UUID
    status: CaseStatus
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    resolution: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class Case(CaseInDB):
    """Public case schema (response)"""
    assigned_users: List[User] = []
    alerts: List[Alert] = []
    comments: List[Comment] = []
    activities: List[Activity] = []
    playbooks: List[CasePlaybook] = []
    external_refs: List[CaseExternalRef] = []


class CaseAddAlerts(BaseModel):
    """Schema for adding alerts to a case"""
    alert_ids: List[UUID] = Field(..., min_length=1)


# ============================================================================
# INCIDENT SCHEMAS
# ============================================================================

class IncidentBase(BaseModel):
    """Base incident schema"""
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    severity: SeverityLevel
    category: Optional[str] = Field(None, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    incident_type: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None


class IncidentCreate(IncidentBase):
    """Schema for creating an incident"""
    tenant_id: UUID
    source_system_id: Optional[UUID] = None
    detected_at: Optional[datetime] = None
    assigned_to_id: Optional[UUID] = None


class IncidentUpdate(BaseModel):
    """Schema for updating an incident"""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    severity: Optional[SeverityLevel] = None
    status: Optional[IncidentStatus] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    incident_type: Optional[str] = None
    assigned_to_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    meta_data: Optional[Dict[str, Any]] = None


class IncidentInDB(IncidentBase):
    """Incident schema as stored in database"""
    id: UUID
    tenant_id: UUID
    source_system_id: Optional[UUID] = None
    status: IncidentStatus
    assigned_to_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    detected_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    meta_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class Incident(IncidentInDB):
    """Public incident schema (response)"""
    assigned_to: Optional[User] = None
    source_system: Optional[SourceSystem] = None
    cases: List[Case] = []
    comments: List[Comment] = []


# ============================================================================
# WAZUH WEBHOOK SCHEMAS
# ============================================================================

class WazuhAlert(BaseModel):
    """Schema for incoming Wazuh alerts"""
    timestamp: str
    rule: Dict[str, Any]
    agent: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
    full_log: Optional[str] = None
    decoder: Optional[Dict[str, Any]] = None
    id: str
    location: Optional[str] = None


class WazuhWebhook(BaseModel):
    """Schema for Wazuh webhook payload"""
    alerts: List[WazuhAlert]
    tenant_id: UUID  # Required to identify which tenant's Wazuh this is


# ============================================================================
# DASHBOARD/STATS SCHEMAS
# ============================================================================

class TenantDashboardStats(BaseModel):
    """Dashboard statistics for a specific tenant"""
    tenant_id: UUID
    tenant_name: str
    total_incidents: int
    open_incidents: int
    total_cases: int
    open_cases: int
    total_alerts: int
    new_alerts: int
    alerts_by_severity: Dict[str, int]
    incidents_by_status: Dict[str, int]
    cases_by_status: Dict[str, int]
    recent_incidents: List[Incident]
    recent_cases: List[Case]


class GlobalDashboardStats(BaseModel):
    """Global dashboard statistics across all tenants"""
    total_tenants: int
    active_tenants: int
    total_incidents: int
    total_cases: int
    total_alerts: int
    tenant_stats: List[TenantDashboardStats]


# ============================================================================
# PAGINATION SCHEMAS
# ============================================================================

class PaginationParams(BaseModel):
    """Query parameters for pagination"""
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)


class PaginatedResponse(BaseModel):
    """Generic paginated response"""
    total: int
    skip: int
    limit: int
    items: List[Any]


# ============================================================================
# AUTHENTICATION SCHEMAS
# ============================================================================

class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user: User
    tenant_id: Optional[UUID] = None  # Current tenant context


class TokenData(BaseModel):
    """JWT token payload data"""
    user_id: UUID
    username: str
    role: UserRole
    tenant_id: Optional[UUID] = None  # Current tenant context
    tenant_ids: List[UUID] = []  # All accessible tenants
