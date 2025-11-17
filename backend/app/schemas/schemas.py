"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums (matching database models)
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
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    SOC_MANAGER = "soc_manager"


# ============================================================================
# USER SCHEMAS
# ============================================================================

class UserBase(BaseModel):
    """Base user schema"""
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole = UserRole.ANALYST


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema for updating user"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserInDB(UserBase):
    """User schema as stored in database"""
    id: int
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class User(UserInDB):
    """Public user schema (response)"""
    pass


# ============================================================================
# ALERT SCHEMAS
# ============================================================================

class AlertBase(BaseModel):
    """Base alert schema"""
    source: str
    source_id: str
    rule_id: Optional[str] = None
    rule_description: Optional[str] = None
    severity: SeverityLevel
    event_type: Optional[str] = None
    category: Optional[str] = None


class AlertCreate(AlertBase):
    """Schema for creating an alert"""
    timestamp: datetime
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


class AlertUpdate(BaseModel):
    """Schema for updating an alert"""
    status: Optional[AlertStatus] = None
    severity: Optional[SeverityLevel] = None


class AlertInDB(AlertBase):
    """Alert schema as stored in database"""
    id: int
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
    pass


# ============================================================================
# COMMENT SCHEMAS
# ============================================================================

class CommentBase(BaseModel):
    """Base comment schema"""
    content: str = Field(..., min_length=1)


class CommentCreate(CommentBase):
    """Schema for creating a comment"""
    incident_id: Optional[int] = None
    case_id: Optional[int] = None


class CommentInDB(CommentBase):
    """Comment schema as stored in database"""
    id: int
    incident_id: Optional[int] = None
    case_id: Optional[int] = None
    author_id: int
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
    action: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ActivityCreate(ActivityBase):
    """Schema for creating an activity"""
    case_id: int
    user_id: int


class ActivityInDB(ActivityBase):
    """Activity schema as stored in database"""
    id: int
    case_id: int
    user_id: int
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
    incident_id: int
    assigned_user_ids: Optional[List[int]] = None


class CaseUpdate(BaseModel):
    """Schema for updating a case"""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    status: Optional[CaseStatus] = None
    priority: Optional[SeverityLevel] = None
    resolution: Optional[str] = None
    tags: Optional[List[str]] = None
    assigned_user_ids: Optional[List[int]] = None


class CaseInDB(CaseBase):
    """Case schema as stored in database"""
    id: int
    status: CaseStatus
    incident_id: int
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    resolution: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class Case(CaseInDB):
    """Public case schema (response)"""
    assigned_users: List[User] = []
    alerts: List[Alert] = []
    comments: List[Comment] = []
    activities: List[Activity] = []


class CaseAddAlerts(BaseModel):
    """Schema for adding alerts to a case"""
    alert_ids: List[int] = Field(..., min_items=1)


# ============================================================================
# INCIDENT SCHEMAS
# ============================================================================

class IncidentBase(BaseModel):
    """Base incident schema"""
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    severity: SeverityLevel
    category: Optional[str] = None
    subcategory: Optional[str] = None
    tags: Optional[List[str]] = None


class IncidentCreate(IncidentBase):
    """Schema for creating an incident"""
    source: str = "Manual"
    source_id: Optional[str] = None
    detected_at: Optional[datetime] = None
    assigned_to_id: Optional[int] = None


class IncidentUpdate(BaseModel):
    """Schema for updating an incident"""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    severity: Optional[SeverityLevel] = None
    status: Optional[IncidentStatus] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    assigned_to_id: Optional[int] = None
    tags: Optional[List[str]] = None


class IncidentInDB(IncidentBase):
    """Incident schema as stored in database"""
    id: int
    status: IncidentStatus
    source: str
    source_id: Optional[str] = None
    assigned_to_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    detected_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class Incident(IncidentInDB):
    """Public incident schema (response)"""
    assigned_to: Optional[User] = None
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


# ============================================================================
# DASHBOARD/STATS SCHEMAS
# ============================================================================

class DashboardStats(BaseModel):
    """Dashboard statistics"""
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
