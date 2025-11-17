"""
Database models for Hubsec SOC Platform
Defines all database tables and relationships
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, JSON, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


# Association table for many-to-many relationship between cases and alerts
case_alerts = Table(
    'case_alerts',
    Base.metadata,
    Column('case_id', Integer, ForeignKey('cases.id'), primary_key=True),
    Column('alert_id', Integer, ForeignKey('alerts.id'), primary_key=True)
)

# Association table for case assignments
case_assignments = Table(
    'case_assignments',
    Base.metadata,
    Column('case_id', Integer, ForeignKey('cases.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
)


class SeverityLevel(str, enum.Enum):
    """Severity levels for incidents and alerts"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IncidentStatus(str, enum.Enum):
    """Status values for incidents"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"
    FALSE_POSITIVE = "false_positive"


class CaseStatus(str, enum.Enum):
    """Status values for cases"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"


class AlertStatus(str, enum.Enum):
    """Status values for alerts"""
    NEW = "new"
    TRIAGED = "triaged"
    IN_CASE = "in_case"
    IGNORED = "ignored"
    RESOLVED = "resolved"


class UserRole(str, enum.Enum):
    """User roles and permissions"""
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    SOC_MANAGER = "soc_manager"


class Incident(Base):
    """
    Incident model - High-level security incidents
    """
    __tablename__ = 'incidents'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    severity = Column(Enum(SeverityLevel), nullable=False, index=True)
    status = Column(Enum(IncidentStatus), default=IncidentStatus.OPEN, index=True)

    # Source information
    source = Column(String(100))  # e.g., "Wazuh", "Manual", "SIEM"
    source_id = Column(String(255), index=True)  # Original ID from source system

    # Categorization
    category = Column(String(100), index=True)  # e.g., "Malware", "Intrusion", "DDoS"
    subcategory = Column(String(100))

    # Assignment and ownership
    assigned_to_id = Column(Integer, ForeignKey('users.id'))
    assigned_to = relationship("User", back_populates="assigned_incidents")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    detected_at = Column(DateTime, index=True)
    resolved_at = Column(DateTime)

    # Additional metadata
    meta_data = Column(JSON)  # Flexible field for additional data
    tags = Column(JSON)  # Array of tags

    # Relationships
    cases = relationship("Case", back_populates="incident", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="incident", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Incident(id={self.id}, title='{self.title}', severity='{self.severity}')>"


class Case(Base):
    """
    Case model - Investigation cases linked to incidents
    """
    __tablename__ = 'cases'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    status = Column(Enum(CaseStatus), default=CaseStatus.OPEN, index=True)
    priority = Column(Enum(SeverityLevel), nullable=False, index=True)

    # Link to parent incident
    incident_id = Column(Integer, ForeignKey('incidents.id'), nullable=False, index=True)
    incident = relationship("Incident", back_populates="cases")

    # Assignment (can have multiple analysts)
    assigned_users = relationship("User", secondary=case_assignments, back_populates="assigned_cases")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime)

    # Case details
    resolution = Column(Text)
    tags = Column(JSON)
    meta_data = Column(JSON)

    # Relationships
    alerts = relationship("Alert", secondary=case_alerts, back_populates="cases")
    comments = relationship("Comment", back_populates="case", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="case", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Case(id={self.id}, title='{self.title}', status='{self.status}')>"


class Alert(Base):
    """
    Alert model - Individual security alerts from various sources
    """
    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True, index=True)

    # Source information
    source = Column(String(100), nullable=False, index=True)  # e.g., "Wazuh", "Suricata"
    source_id = Column(String(255), unique=True, index=True)  # Unique ID from source

    # Alert details
    rule_id = Column(String(100), index=True)
    rule_description = Column(Text)
    severity = Column(Enum(SeverityLevel), nullable=False, index=True)
    status = Column(Enum(AlertStatus), default=AlertStatus.NEW, index=True)

    # Normalized fields
    event_type = Column(String(100), index=True)  # Normalized event type
    category = Column(String(100), index=True)

    # Network information
    src_ip = Column(String(45), index=True)  # IPv4 or IPv6
    dst_ip = Column(String(45), index=True)
    src_port = Column(Integer)
    dst_port = Column(Integer)
    protocol = Column(String(20))

    # Host information
    hostname = Column(String(255), index=True)
    agent_id = Column(String(100), index=True)
    agent_name = Column(String(255))

    # User information
    username = Column(String(255), index=True)

    # File information
    filename = Column(String(500))
    file_path = Column(Text)
    file_hash = Column(String(128))

    # Timestamps
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Raw data
    raw_data = Column(JSON)  # Complete original alert data
    normalized_data = Column(JSON)  # Processed and normalized data

    # Relationships
    cases = relationship("Case", secondary=case_alerts, back_populates="alerts")

    def __repr__(self):
        return f"<Alert(id={self.id}, source='{self.source}', severity='{self.severity}')>"


class User(Base):
    """
    User model - SOC analysts and administrators
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))

    # Authentication
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Integer, default=1)  # Using Integer for SQLite compatibility

    # Role and permissions
    role = Column(Enum(UserRole), default=UserRole.ANALYST, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

    # Relationships
    assigned_incidents = relationship("Incident", back_populates="assigned_to")
    assigned_cases = relationship("Case", secondary=case_assignments, back_populates="assigned_users")
    comments = relationship("Comment", back_populates="author")
    activities = relationship("Activity", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class Comment(Base):
    """
    Comment model - Comments on incidents and cases
    """
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)

    # Link to either incident or case
    incident_id = Column(Integer, ForeignKey('incidents.id'), index=True)
    case_id = Column(Integer, ForeignKey('cases.id'), index=True)

    # Author
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    author = relationship("User", back_populates="comments")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    incident = relationship("Incident", back_populates="comments")
    case = relationship("Case", back_populates="comments")

    def __repr__(self):
        return f"<Comment(id={self.id}, author_id={self.author_id})>"


class Activity(Base):
    """
    Activity model - Audit trail for case activities
    """
    __tablename__ = 'activities'

    id = Column(Integer, primary_key=True, index=True)

    # Activity details
    action = Column(String(100), nullable=False, index=True)  # e.g., "status_changed", "alert_added"
    description = Column(Text)

    # Link to case
    case_id = Column(Integer, ForeignKey('cases.id'), nullable=False, index=True)
    case = relationship("Case", back_populates="activities")

    # User who performed the action
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User", back_populates="activities")

    # Metadata
    meta_data = Column(JSON)  # Additional context about the activity

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<Activity(id={self.id}, action='{self.action}', case_id={self.case_id})>"
