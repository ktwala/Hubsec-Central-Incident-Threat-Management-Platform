"""
Database models for Hubsec Central SOC Platform - MULTI-TENANT VERSION
Enhanced schema supporting multiple tenants, integrations, playbooks, and assets

IMPORTANT: This schema uses PostgreSQL-specific types:
- UUID for primary keys (uses gen_random_uuid())
- INET for IP addresses
- TEXT[] (ARRAY) for tags
- JSONB for JSON data
- TIMESTAMPTZ for timestamps with timezone

For development/testing with SQLite, use the original models.py
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, Table, Boolean
from sqlalchemy.dialects.postgresql import UUID, INET, ARRAY, JSONB, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

Base = declarative_base()


# ============================================================================
# ASSOCIATION TABLES (Many-to-Many)
# ============================================================================

# Users can access multiple tenants with different roles
user_tenants = Table(
    'user_tenants',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('tenant_id', UUID(as_uuid=True), ForeignKey('tenants.id'), primary_key=True),
    Column('tenant_role', String(50))  # tenant_admin, tenant_analyst, tenant_viewer
)

# Cases can have multiple assigned users
case_assignments = Table(
    'case_assignments',
    Base.metadata,
    Column('case_id', UUID(as_uuid=True), ForeignKey('cases.id'), primary_key=True),
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
)

# Cases can have multiple alerts (alert correlation)
case_alerts = Table(
    'case_alerts',
    Base.metadata,
    Column('case_id', UUID(as_uuid=True), ForeignKey('cases.id'), primary_key=True),
    Column('alert_id', UUID(as_uuid=True), ForeignKey('alerts.id'), primary_key=True)
)


# ============================================================================
# ENUMS
# ============================================================================

class SeverityLevel(str, enum.Enum):
    """Severity/Priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IncidentStatus(str, enum.Enum):
    """Incident lifecycle status"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"
    FALSE_POSITIVE = "false_positive"


class CaseStatus(str, enum.Enum):
    """Case investigation status"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"


class AlertStatus(str, enum.Enum):
    """Alert processing status"""
    NEW = "new"
    TRIAGED = "triaged"
    IN_CASE = "in_case"
    IGNORED = "ignored"
    RESOLVED = "resolved"


class UserRole(str, enum.Enum):
    """Global platform roles"""
    SUPER_ADMIN = "super_admin"      # Hubsec super admin
    HUBSEC_ANALYST = "hubsec_analyst" # Hubsec SOC analyst (can see all tenants)
    TENANT_ADMIN = "tenant_admin"     # Client admin
    ANALYST = "analyst"               # SOC analyst
    VIEWER = "viewer"                 # Read-only access


class AssetType(str, enum.Enum):
    """Asset/endpoint types"""
    SERVER = "server"
    WORKSTATION = "workstation"
    NETWORK_DEVICE = "network_device"
    DATABASE = "database"
    APPLICATION = "application"
    CONTAINER = "container"
    CLOUD_RESOURCE = "cloud_resource"
    OTHER = "other"


class IntegrationType(str, enum.Enum):
    """Source system / integration types"""
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


class PlaybookStatus(str, enum.Enum):
    """Playbook execution status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# CORE MULTI-TENANT MODELS
# ============================================================================

class Tenant(Base):
    """
    Organizations/Clients in the multi-tenant platform
    Examples: Econet, PostBank, TelOne, etc.
    """
    __tablename__ = 'tenants'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False, unique=True)  # "Econet Wireless"
    code = Column(String(50), nullable=False, unique=True, index=True)  # "ECONET"

    # Organization details
    industry = Column(String(100))  # "Telecommunications", "Banking"
    region = Column(String(100))    # "Zimbabwe", "East Africa"
    contact_name = Column(String(255))
    contact_email = Column(String(255))
    contact_phone = Column(String(50))

    # Status and metadata
    is_active = Column(Boolean, default=True, index=True)
    subscription_tier = Column(String(50))  # "basic", "professional", "enterprise"
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Configuration
    settings = Column(JSONB)  # Tenant-specific settings

    # Relationships
    users = relationship("User", secondary=user_tenants, back_populates="tenants")
    source_systems = relationship("SourceSystem", back_populates="tenant", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="tenant")
    incidents = relationship("Incident", back_populates="tenant")
    cases = relationship("Case", back_populates="tenant")
    assets = relationship("Asset", back_populates="tenant", cascade="all, delete-orphan")
    playbooks = relationship("Playbook", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant(id={self.id}, code='{self.code}', name='{self.name}')>"


class SourceSystem(Base):
    """
    External integrations and data sources
    Examples: Wazuh Manager, IRIS instance, Jira project, FortiGate firewall
    """
    __tablename__ = 'source_systems'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)

    # System identification
    name = Column(String(255), nullable=False)  # "Econet Wazuh Manager"
    type = Column(Enum(IntegrationType), nullable=False, index=True)
    description = Column(Text)

    # Connection details
    base_url = Column(String(500))  # "https://wazuh.econet.co.zw"
    auth_type = Column(String(50))  # "api_key", "oauth2", "basic_auth"
    auth_config = Column(JSONB)  # Encrypted credentials (API keys, tokens, etc.)

    # Status and sync
    is_active = Column(Boolean, default=True, index=True)
    last_sync_at = Column(TIMESTAMP(timezone=True))
    sync_status = Column(String(50))  # "healthy", "error", "degraded"
    sync_error = Column(Text)

    # Configuration
    config = Column(JSONB)  # Integration-specific config

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="source_systems")
    alerts = relationship("Alert", back_populates="source_system")
    incidents = relationship("Incident", back_populates="source_system")

    def __repr__(self):
        return f"<SourceSystem(id={self.id}, name='{self.name}', type='{self.type}')>"


# ============================================================================
# USER & RBAC MODELS
# ============================================================================

class User(Base):
    """
    Platform users (Hubsec analysts + client users)
    Multi-tenant access via user_tenants join table
    """
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))

    # Authentication
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)

    # Global role (for Hubsec staff)
    role = Column(Enum(UserRole), default=UserRole.ANALYST, nullable=False)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    last_login = Column(TIMESTAMP(timezone=True))

    # Relationships
    tenants = relationship("Tenant", secondary=user_tenants, back_populates="users")
    assigned_incidents = relationship("Incident", back_populates="assigned_to")
    assigned_cases = relationship("Case", secondary=case_assignments, back_populates="assigned_users")
    comments = relationship("Comment", back_populates="author")
    activities = relationship("Activity", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


# ============================================================================
# ASSET MANAGEMENT
# ============================================================================

class Asset(Base):
    """
    IT Assets / Endpoints for context and correlation
    """
    __tablename__ = 'assets'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)

    # Asset identification
    hostname = Column(String(255), index=True)
    ip_address = Column(INET, index=True)  # PostgreSQL INET type for IPv4/IPv6
    mac_address = Column(String(17))

    # Asset classification
    asset_type = Column(Enum(AssetType), nullable=False, index=True)
    criticality = Column(Enum(SeverityLevel), default=SeverityLevel.MEDIUM, index=True)

    # Asset details
    os = Column(String(100))  # "Windows Server 2019", "Ubuntu 20.04"
    os_version = Column(String(50))
    environment = Column(String(50), index=True)  # "production", "development", "staging"

    # Ownership
    owner = Column(String(255))  # Business owner
    department = Column(String(100))
    location = Column(String(255))

    # Status
    is_active = Column(Boolean, default=True)
    last_seen = Column(TIMESTAMP(timezone=True))

    # Metadata
    tags = Column(ARRAY(Text))  # PostgreSQL TEXT[] array for tags
    meta_data = Column(JSONB)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="assets")
    alerts = relationship("Alert", back_populates="asset")

    def __repr__(self):
        return f"<Asset(id={self.id}, hostname='{self.hostname}', type='{self.asset_type}')>"


# ============================================================================
# PLAYBOOK / AUTOMATION MODELS
# ============================================================================

class Playbook(Base):
    """
    Incident response playbooks/runbooks
    Can be global (tenant_id=NULL) or tenant-specific
    """
    __tablename__ = 'playbooks'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=True, index=True)  # NULL = global

    # Playbook details
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    incident_type = Column(String(100), index=True)  # Maps to incident.category

    # Playbook definition
    definition = Column(JSONB, nullable=False)  # Array of steps, actions, decision points

    # Metadata
    version = Column(String(20), default="1.0")
    is_active = Column(Boolean, default=True)
    tags = Column(ARRAY(Text))  # PostgreSQL TEXT[] array

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))

    # Relationships
    tenant = relationship("Tenant", back_populates="playbooks")
    case_playbooks = relationship("CasePlaybook", back_populates="playbook")

    def __repr__(self):
        return f"<Playbook(id={self.id}, name='{self.name}', type='{self.incident_type}')>"


class CasePlaybook(Base):
    """
    Links playbooks to cases and tracks execution
    """
    __tablename__ = 'case_playbooks'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=False, index=True)
    playbook_id = Column(UUID(as_uuid=True), ForeignKey('playbooks.id'), nullable=False, index=True)

    # Execution tracking
    status = Column(Enum(PlaybookStatus), default=PlaybookStatus.NOT_STARTED, index=True)
    started_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    started_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))

    # Step tracking
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer)
    completed_steps = Column(JSONB)  # Array of completed step IDs

    # Results
    meta_data = Column(JSONB)  # Execution results, automation outputs

    # Relationships
    case = relationship("Case", back_populates="playbooks")
    playbook = relationship("Playbook", back_populates="case_playbooks")

    def __repr__(self):
        return f"<CasePlaybook(case_id={self.case_id}, playbook_id={self.playbook_id}, status='{self.status}')>"


# ============================================================================
# ALERT MANAGEMENT
# ============================================================================

class Alert(Base):
    """
    Security alerts from various sources (multi-tenant)
    """
    __tablename__ = 'alerts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    source_system_id = Column(UUID(as_uuid=True), ForeignKey('source_systems.id'), index=True)
    asset_id = Column(UUID(as_uuid=True), ForeignKey('assets.id'), nullable=True, index=True)

    # Source identification
    source_id = Column(String(255), unique=True, index=True)  # Original ID from source

    # Alert classification
    rule_id = Column(String(100), index=True)
    rule_description = Column(Text)
    severity = Column(Enum(SeverityLevel), nullable=False, index=True)
    status = Column(Enum(AlertStatus), default=AlertStatus.NEW, index=True)
    event_type = Column(String(100), index=True)
    category = Column(String(100), index=True)

    # Network context - Using PostgreSQL INET for IP addresses
    src_ip = Column(INET, index=True)
    dst_ip = Column(INET, index=True)
    src_port = Column(Integer)
    dst_port = Column(Integer)
    protocol = Column(String(20))

    # Host context
    hostname = Column(String(255), index=True)
    agent_id = Column(String(100), index=True)
    agent_name = Column(String(255))

    # User context
    username = Column(String(255), index=True)

    # File context
    filename = Column(String(500))
    file_path = Column(Text)
    file_hash = Column(String(128))

    # Timestamps
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, index=True)  # Event time
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)     # Ingestion time

    # Data
    raw_data = Column(JSONB)        # Original alert
    normalized_data = Column(JSONB) # Processed/enriched data

    # Relationships
    tenant = relationship("Tenant", back_populates="alerts")
    source_system = relationship("SourceSystem", back_populates="alerts")
    asset = relationship("Asset", back_populates="alerts")
    cases = relationship("Case", secondary=case_alerts, back_populates="alerts")

    def __repr__(self):
        return f"<Alert(id={self.id}, tenant_id={self.tenant_id}, severity='{self.severity}')>"


# ============================================================================
# INCIDENT & CASE MANAGEMENT
# ============================================================================

class Incident(Base):
    """
    High-level security incidents (multi-tenant)
    """
    __tablename__ = 'incidents'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    source_system_id = Column(UUID(as_uuid=True), ForeignKey('source_systems.id'), nullable=True, index=True)

    # Incident details
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    severity = Column(Enum(SeverityLevel), nullable=False, index=True)
    status = Column(Enum(IncidentStatus), default=IncidentStatus.OPEN, index=True)

    # Classification
    category = Column(String(100), index=True)
    subcategory = Column(String(100))
    incident_type = Column(String(100), index=True)  # For playbook matching

    # Assignment
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, index=True)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    detected_at = Column(TIMESTAMP(timezone=True), index=True)
    resolved_at = Column(TIMESTAMP(timezone=True))

    # Metadata
    meta_data = Column(JSONB)
    tags = Column(ARRAY(Text))  # PostgreSQL TEXT[] array

    # Relationships
    tenant = relationship("Tenant", back_populates="incidents")
    source_system = relationship("SourceSystem", back_populates="incidents")
    assigned_to = relationship("User", back_populates="assigned_incidents")
    cases = relationship("Case", back_populates="incident", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="incident", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Incident(id={self.id}, tenant_id={self.tenant_id}, title='{self.title}')>"


class Case(Base):
    """
    Investigation cases (multi-tenant)
    """
    __tablename__ = 'cases'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    incident_id = Column(UUID(as_uuid=True), ForeignKey('incidents.id'), nullable=False, index=True)

    # Case details
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    status = Column(Enum(CaseStatus), default=CaseStatus.OPEN, index=True)
    priority = Column(Enum(SeverityLevel), nullable=False, index=True)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, index=True)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(TIMESTAMP(timezone=True))

    # Resolution
    resolution = Column(Text)

    # Metadata
    tags = Column(ARRAY(Text))  # PostgreSQL TEXT[] array
    meta_data = Column(JSONB)

    # Relationships
    tenant = relationship("Tenant", back_populates="cases")
    incident = relationship("Incident", back_populates="cases")
    assigned_users = relationship("User", secondary=case_assignments, back_populates="assigned_cases")
    alerts = relationship("Alert", secondary=case_alerts, back_populates="cases")
    comments = relationship("Comment", back_populates="case", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="case", cascade="all, delete-orphan")
    playbooks = relationship("CasePlaybook", back_populates="case", cascade="all, delete-orphan")
    external_refs = relationship("CaseExternalRef", back_populates="case", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Case(id={self.id}, tenant_id={self.tenant_id}, title='{self.title}')>"


class CaseExternalRef(Base):
    """
    Links to external systems (IRIS, Jira, ServiceNow, etc.)
    """
    __tablename__ = 'case_external_refs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=False, index=True)

    # External system reference
    system_type = Column(String(50), nullable=False, index=True)  # "iris", "jira", "servicenow"
    external_id = Column(String(255), nullable=False, index=True)  # "IRIS-0001", "SOC-123"
    url = Column(String(500))  # Direct link

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    synced_at = Column(TIMESTAMP(timezone=True))
    sync_status = Column(String(50))  # "synced", "out_of_sync", "error"

    # Relationships
    case = relationship("Case", back_populates="external_refs")

    def __repr__(self):
        return f"<CaseExternalRef(case_id={self.case_id}, type='{self.system_type}', id='{self.external_id}')>"


# ============================================================================
# COLLABORATION & AUDIT
# ============================================================================

class Comment(Base):
    """
    Comments on incidents and cases
    """
    __tablename__ = 'comments'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    content = Column(Text, nullable=False)

    # Links
    incident_id = Column(UUID(as_uuid=True), ForeignKey('incidents.id'), index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), index=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    incident = relationship("Incident", back_populates="comments")
    case = relationship("Case", back_populates="comments")
    author = relationship("User", back_populates="comments")

    def __repr__(self):
        return f"<Comment(id={self.id}, author_id={self.author_id})>"


class Activity(Base):
    """
    Audit trail for case activities
    """
    __tablename__ = 'activities'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Activity details
    action = Column(String(100), nullable=False, index=True)
    description = Column(Text)

    # Links
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Metadata
    meta_data = Column(JSONB)

    # Timestamp
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, index=True)

    # Relationships
    case = relationship("Case", back_populates="activities")
    user = relationship("User", back_populates="activities")

    def __repr__(self):
        return f"<Activity(id={self.id}, action='{self.action}', case_id={self.case_id})>"
