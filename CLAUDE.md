# CLAUDE.md - AI Assistant Guide

**Last Updated**: 2025-11-23
**Repository**: Hubsec Central Incident & Threat Management Platform
**Purpose**: Comprehensive guide for AI assistants working with this codebase

---

## Table of Contents

1. [Repository Overview](#repository-overview)
2. [Codebase Architecture](#codebase-architecture)
3. [Technology Stack](#technology-stack)
4. [Key Conventions](#key-conventions)
5. [Development Workflows](#development-workflows)
6. [Common Tasks](#common-tasks)
7. [Database Patterns](#database-patterns)
8. [API Development Guidelines](#api-development-guidelines)
9. [Multi-Tenant Considerations](#multi-tenant-considerations)
10. [Authentication & Authorization](#authentication--authorization)
11. [Testing Strategy](#testing-strategy)
12. [Error Handling](#error-handling)
13. [Code Quality](#code-quality)
14. [Important Commands](#important-commands)
15. [Known Limitations](#known-limitations)

---

## Repository Overview

### What is This?

A production-ready, multi-tenant Security Operations Center (SOC) platform built with FastAPI and PostgreSQL. It centralizes incident management, alert correlation, and threat response for multiple client organizations.

### Project Stats

- **Lines of Code**: 5,000+ Python lines
- **API Endpoints**: 76 endpoints across 8 routers
- **Database Models**: 15 multi-tenant models
- **Backend Files**: 26 Python files
- **Documentation**: 9 comprehensive markdown files

### Key Features

- Multi-tenant architecture with complete data isolation
- Alert ingestion and normalization (Wazuh, custom sources)
- Incident and case management
- Asset inventory with criticality tracking
- Playbook automation for incident response
- Integration management (Wazuh, IRIS, Jira, FortiGate, etc.)
- Role-based access control (RBAC) with 5 role levels

---

## Codebase Architecture

### Dual Architecture Pattern

**CRITICAL**: This repository supports TWO operational modes:

#### 1. Single-Tenant Mode (Development)
- **Entry**: `backend/app/main.py`
- **Database**: `database.py` (SQLite)
- **Models**: `models.py` (Integer IDs)
- **Schemas**: `schemas.py`
- **Use Case**: Development, single-client deployments

#### 2. Multi-Tenant Mode (Production) ⭐ RECOMMENDED
- **Entry**: `backend/app/main_multitenant.py`
- **Database**: `database_multitenant.py` (PostgreSQL required)
- **Models**: `models_multitenant.py` (UUID IDs, 15 tables)
- **Schemas**: `schemas_multitenant.py`
- **Use Case**: Production, multiple client organizations

### Directory Structure

```
Hubsec-Central-Incident-Threat-Management-Platform/
├── backend/
│   └── app/
│       ├── api/
│       │   └── v1/              # API endpoint implementations
│       │       ├── tenants.py          # 6 endpoints, 256 lines
│       │       ├── source_systems.py   # 7 endpoints, 355 lines
│       │       ├── assets.py           # 9 endpoints, 401 lines
│       │       ├── playbooks.py        # 10 endpoints, 483 lines
│       │       ├── alerts.py           # 9 endpoints, 531 lines
│       │       ├── incidents.py        # 8 endpoints, 435 lines
│       │       ├── cases.py            # 14 endpoints, 813 lines
│       │       └── users.py            # 13 endpoints, 612 lines
│       ├── middleware/
│       │   └── tenant.py        # Tenant context & RBAC (246 lines)
│       ├── models/
│       │   ├── models.py                # Single-tenant (301 lines)
│       │   └── models_multitenant.py    # Multi-tenant (628 lines) ⭐
│       ├── schemas/
│       │   ├── schemas.py               # Single-tenant (392 lines)
│       │   └── schemas_multitenant.py   # Multi-tenant (781 lines) ⭐
│       ├── services/
│       │   ├── wazuh_normalizer.py      # Alert normalization
│       │   └── case_engine.py           # Case correlation engine
│       ├── main.py                      # Single-tenant FastAPI app
│       ├── main_multitenant.py          # Multi-tenant FastAPI app ⭐
│       ├── database.py                  # SQLite config
│       └── database_multitenant.py      # PostgreSQL config ⭐
├── config/
│   ├── wazuh_mapping.yml         # Field mapping for Wazuh alerts
│   └── severity_rules.yml        # Severity calculation rules
├── scripts/
│   ├── init_db.py                # Single-tenant DB init
│   └── init_db_multitenant.py    # Multi-tenant DB init + seed ⭐
├── .env.example                  # Environment configuration template
├── requirements.txt              # Python dependencies (25 packages)
├── docker-compose.yml            # Docker orchestration
└── Dockerfile                    # Container definition
```

**⭐ = Multi-tenant specific files**

### Core Components

#### 1. API Layer (`backend/app/api/v1/`)
- RESTful endpoints following OpenAPI spec
- Automatic documentation via Swagger UI (`/api/docs`)
- Versioned API (`/api/v1/...`)
- 8 router modules with 76 total endpoints

#### 2. Database Layer
- **ORM**: SQLAlchemy 2.0.23
- **Single-tenant**: SQLite with Integer IDs
- **Multi-tenant**: PostgreSQL 12+ with UUID IDs
- **Connection pooling**: pool_size=10, max_overflow=20

#### 3. Middleware Layer (`backend/app/middleware/`)
- Tenant context management
- Header-based authentication (testing/mock)
- RBAC enforcement
- Access validation

#### 4. Services Layer (`backend/app/services/`)
- Alert normalization (Wazuh format → standard format)
- Case correlation engine (auto-case creation)
- Business logic separated from API layer

#### 5. Configuration
- YAML-based configuration (field mappings, severity rules)
- Environment-based settings (.env)
- Type-safe config loading

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Web Framework** | FastAPI | 0.104.1 | Async REST API |
| **ASGI Server** | Uvicorn | 0.24.0 | Production server |
| **ORM** | SQLAlchemy | 2.0.23 | Database abstraction |
| **DB (Production)** | PostgreSQL | 12+ | Multi-tenant data |
| **DB (Dev)** | SQLite | 3.x | Single-tenant dev |
| **PG Driver** | psycopg2-binary | 2.9.9 | PostgreSQL adapter |
| **Validation** | Pydantic | 2.5.0 | Schema validation |
| **Migration Tool** | Alembic | 1.12.1 | DB migrations (planned) |
| **Config** | PyYAML | 6.0.1 | YAML parsing |
| **Auth** | python-jose | 3.3.0 | JWT handling (planned) |
| **Password** | passlib[bcrypt] | 1.7.4 | Password hashing |
| **HTTP Client** | httpx | 0.25.1 | Async HTTP |

### PostgreSQL-Specific Types (Multi-Tenant Only)

```python
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB, ARRAY

# Used extensively in models_multitenant.py:
- UUID(as_uuid=True)      # Primary keys
- INET                     # IP addresses (automatic validation)
- JSONB                    # Flexible metadata
- ARRAY(Text)             # Tags, lists
- TIMESTAMP(timezone=True) # Timezone-aware timestamps
```

### Development Tools

```python
# Code Quality (in requirements.txt)
black==23.11.0     # Code formatter
flake8==6.1.0      # Linter
mypy==1.7.1        # Type checker

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
```

---

## Key Conventions

### Naming Conventions

#### Files
- **Models**: `models.py`, `models_multitenant.py`
- **Schemas**: `schemas.py`, `schemas_multitenant.py`
- **API routers**: Lowercase with underscores (`source_systems.py`, `assets.py`)
- **Services**: Descriptive purpose (`wazuh_normalizer.py`, `case_engine.py`)
- **Scripts**: Action-based (`init_db.py`, `init_db_multitenant.py`)

#### Functions
```python
# CRUD operations
list_alerts()       # GET all
get_alert()         # GET one
create_alert()      # POST
update_alert()      # PATCH
delete_alert()      # DELETE (soft)

# Special operations
trigger_sync()      # POST action
update_heartbeat()  # POST action
search_by_ip()      # GET with search

# Private helpers
_should_create_case()    # Internal logic
_find_related_case()     # Internal helper
_validate_access()       # Internal check
```

#### Database Columns
```python
# Primary keys
id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))

# Foreign keys
tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"))
user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))

# Timestamps
created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())
last_seen = Column(TIMESTAMP(timezone=True))
last_login = Column(TIMESTAMP(timezone=True))

# Status flags
is_active = Column(Boolean, default=True)
is_deleted = Column(Boolean, default=False)  # Soft delete
is_global = Column(Boolean, default=False)   # Global vs tenant-specific

# Metadata
settings = Column(JSONB)
config = Column(JSONB)
meta_data = Column(JSONB)
```

#### Pydantic Schemas

**Standard Pattern per Entity:**

```python
# 1. Base schema - common fields
class TenantBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None

# 2. Create schema - for POST requests
class TenantCreate(TenantBase):
    admin_email: str

# 3. Update schema - for PATCH requests (all optional)
class TenantUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None

# 4. InDB schema - database representation
class TenantInDB(TenantBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True

# 5. Response schema - public API response
class Tenant(TenantInDB):
    user_count: Optional[int] = None
    alert_count: Optional[int] = None
```

### Code Style

- **Format**: Black (line length 88)
- **Imports**: Absolute imports, grouped (stdlib, third-party, local)
- **Type hints**: Required for function signatures
- **Docstrings**: Google style for complex functions
- **Comments**: Only for non-obvious business logic

---

## Development Workflows

### Initial Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd Hubsec-Central-Incident-Threat-Management-Platform

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup PostgreSQL (multi-tenant)
sudo -u postgres psql
CREATE DATABASE hubsec_multitenant;
CREATE USER hubsec WITH PASSWORD 'hubsec';
GRANT ALL PRIVILEGES ON DATABASE hubsec_multitenant TO hubsec;
\q

# 5. Set environment
export DATABASE_URL="postgresql://hubsec:hubsec@localhost/hubsec_multitenant"

# 6. Initialize database with seed data
python scripts/init_db_multitenant.py --database-url "$DATABASE_URL" --drop --seed

# 7. Start development server
uvicorn backend.app.main_multitenant:app --reload
```

### Running the Application

**Multi-Tenant Mode (Recommended):**
```bash
uvicorn backend.app.main_multitenant:app --reload --host 0.0.0.0 --port 8000
```

**Single-Tenant Mode:**
```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

**Access Points:**
- API Documentation: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- Health Check: http://localhost:8000/health
- Database Info: http://localhost:8000/api/v1/info/database

### Database Operations

**Initialize Multi-Tenant Database:**
```bash
# Drop existing, create fresh with seed data
python scripts/init_db_multitenant.py --database-url "$DATABASE_URL" --drop --seed

# Just create schema (no seed data)
python scripts/init_db_multitenant.py --database-url "$DATABASE_URL"

# Seed data only (assumes schema exists)
python scripts/init_db_multitenant.py --database-url "$DATABASE_URL" --seed
```

**Seed Data Includes:**
- 3 Tenants (Econet, PostBank, TelOne)
- 7 Users (3 Hubsec staff + 4 tenant users)
- 5 Source Systems (Wazuh, IRIS, Jira integrations)
- 4 Assets (servers with various criticality levels)
- 50 Alerts across tenants
- 2 Incidents, 2 Cases
- 2 Playbooks (1 global, 1 tenant-specific)

### Testing with Curl

**Get User and Tenant IDs:**
```bash
# Query database for UUIDs
export USER_ID=$(psql $DATABASE_URL -t -c "SELECT id FROM users WHERE username='hubsec_analyst1';" | tr -d ' ')
export TENANT_ID=$(psql $DATABASE_URL -t -c "SELECT id FROM tenants WHERE code='ECONET';" | tr -d ' ')
```

**Test Authentication:**
```bash
# Using username
curl -X GET "http://localhost:8000/api/v1/tenants" \
  -H "X-Username: hubsec_analyst1"

# Using user ID
curl -X GET "http://localhost:8000/api/v1/tenants" \
  -H "X-User-ID: $USER_ID"

# With tenant context
curl -X GET "http://localhost:8000/api/v1/alerts?tenant_id=$TENANT_ID" \
  -H "X-Username: econet_admin"
```

See **API_TESTING_GUIDE.md** for comprehensive testing examples.

---

## Common Tasks

### Adding a New Entity (Multi-Tenant)

**Example: Adding a "ThreatIntelligence" entity**

**1. Add Model (`backend/app/models/models_multitenant.py`):**

```python
class ThreatIntelligence(Base):
    __tablename__ = "threat_intelligence"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    indicator_type = Column(String, nullable=False)  # ip, domain, hash, etc.
    indicator_value = Column(String, nullable=False)
    severity = Column(Enum(SeverityLevel), nullable=False)
    source = Column(String)  # MISP, AlienVault, etc.
    tags = Column(ARRAY(Text))
    meta_data = Column(JSONB)

    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

    # Relationship
    tenant = relationship("Tenant", back_populates="threat_intelligence")

    def __repr__(self):
        return f"<ThreatIntelligence {self.indicator_type}:{self.indicator_value}>"

# Update Tenant model to add back_populates
# In Tenant class, add:
# threat_intelligence = relationship("ThreatIntelligence", back_populates="tenant")
```

**2. Add Schemas (`backend/app/schemas/schemas_multitenant.py`):**

```python
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

class ThreatIntelligenceBase(BaseModel):
    indicator_type: str
    indicator_value: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    source: Optional[str] = None
    tags: Optional[List[str]] = None
    meta_data: Optional[Dict[str, Any]] = None

class ThreatIntelligenceCreate(ThreatIntelligenceBase):
    tenant_id: UUID

class ThreatIntelligenceUpdate(BaseModel):
    indicator_type: Optional[str] = None
    indicator_value: Optional[str] = None
    severity: Optional[str] = None
    source: Optional[str] = None
    tags: Optional[List[str]] = None
    meta_data: Optional[Dict[str, Any]] = None

class ThreatIntelligenceInDB(ThreatIntelligenceBase):
    id: UUID
    tenant_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class ThreatIntelligence(ThreatIntelligenceInDB):
    pass
```

**3. Create API Router (`backend/app/api/v1/threat_intelligence.py`):**

```python
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ...database_multitenant import get_db
from ...models.models_multitenant import ThreatIntelligence as ThreatIntelModel
from ...schemas.schemas_multitenant import (
    ThreatIntelligence,
    ThreatIntelligenceCreate,
    ThreatIntelligenceUpdate
)
from ...middleware.tenant import TenantContext, get_tenant_context, require_auth

router = APIRouter(prefix="/threat-intelligence", tags=["threat-intelligence"])

@router.get("/", response_model=List[ThreatIntelligence])
async def list_threat_intelligence(
    tenant_id: Optional[UUID] = Query(None),
    indicator_type: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context)
):
    """List threat intelligence indicators with tenant filtering."""
    query = db.query(ThreatIntelModel).filter(ThreatIntelModel.is_active == True)

    # Tenant filtering
    if context.is_hubsec_staff():
        if tenant_id:
            query = query.filter(ThreatIntelModel.tenant_id == tenant_id)
    else:
        user_tenant_ids = [t.id for t in context.user.tenants]
        query = query.filter(ThreatIntelModel.tenant_id.in_(user_tenant_ids))

    # Additional filters
    if indicator_type:
        query = query.filter(ThreatIntelModel.indicator_type == indicator_type)

    return query.offset(skip).limit(limit).all()

@router.post("/", response_model=ThreatIntelligence, status_code=status.HTTP_201_CREATED)
async def create_threat_intelligence(
    intel: ThreatIntelligenceCreate,
    db: Session = Depends(get_db),
    context: TenantContext = Depends(require_auth)
):
    """Create a new threat intelligence indicator."""
    # Validate tenant access
    if not context.can_access_tenant(intel.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
        )

    db_intel = ThreatIntelModel(**intel.model_dump())
    db.add(db_intel)
    db.commit()
    db.refresh(db_intel)
    return db_intel

@router.get("/{intel_id}", response_model=ThreatIntelligence)
async def get_threat_intelligence(
    intel_id: UUID,
    db: Session = Depends(get_db),
    context: TenantContext = Depends(require_auth)
):
    """Get threat intelligence indicator by ID."""
    intel = db.query(ThreatIntelModel).filter(
        ThreatIntelModel.id == intel_id,
        ThreatIntelModel.is_active == True
    ).first()

    if not intel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Threat intelligence {intel_id} not found"
        )

    if not context.can_access_tenant(intel.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
        )

    return intel

# Add update, delete endpoints following same patterns...
```

**4. Register Router (`backend/app/main_multitenant.py`):**

```python
from .api.v1 import threat_intelligence

# In create_app() or at module level:
app.include_router(threat_intelligence.router, prefix="/api/v1")
```

**5. Update Database Init Script (`scripts/init_db_multitenant.py`):**

```python
# Add seed data function
def seed_threat_intelligence(session, tenants):
    """Seed threat intelligence data."""
    indicators = [
        ThreatIntelligence(
            tenant_id=tenants[0].id,  # Econet
            indicator_type="ip",
            indicator_value="192.168.1.100",
            severity=SeverityLevel.HIGH,
            source="Internal Analysis",
            tags=["malware", "c2"]
        ),
        # Add more...
    ]
    session.add_all(indicators)
    session.commit()

# Call in seed_database():
# seed_threat_intelligence(session, tenants)
```

### Modifying an Existing Endpoint

**Example: Add filtering by severity to alerts endpoint**

**1. Update function signature:**
```python
@router.get("/", response_model=List[Alert])
async def list_alerts(
    # ... existing parameters ...
    severity: Optional[str] = Query(None, description="Filter by severity"),  # ADD THIS
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context)
):
```

**2. Add filter logic:**
```python
    # ... existing tenant filtering ...

    # Add severity filter
    if severity:
        query = query.filter(AlertModel.severity == severity)

    return query.offset(skip).limit(limit).all()
```

### Adding Configuration

**Example: Add rate limiting config**

**1. Update `.env.example`:**
```bash
# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
```

**2. Create config module (`backend/app/config.py`):**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Existing settings...

    # Rate limiting
    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 60

    class Config:
        env_file = ".env"

settings = Settings()
```

**3. Use in middleware:**
```python
from .config import settings

if settings.rate_limit_enabled:
    # Apply rate limiting logic
    pass
```

---

## Database Patterns

### Multi-Tenant Query Pattern

**CRITICAL**: Every query in multi-tenant mode MUST filter by tenant.

```python
@router.get("/", response_model=List[Entity])
async def list_entities(
    tenant_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context)
):
    """Standard multi-tenant list pattern."""
    # Start with base query
    query = db.query(EntityModel).filter(EntityModel.is_active == True)

    # REQUIRED: Tenant filtering
    if context.is_hubsec_staff():
        # Hubsec staff can see all or filter by specific tenant
        if tenant_id:
            query = query.filter(EntityModel.tenant_id == tenant_id)
    else:
        # Regular users see only their assigned tenants
        user_tenant_ids = [t.id for t in context.user.tenants]
        query = query.filter(EntityModel.tenant_id.in_(user_tenant_ids))

    # Additional filters...

    return query.offset(skip).limit(limit).all()
```

### Soft Delete Pattern

**NEVER hard delete** - always use soft delete with `is_active` flag.

```python
@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entity(
    entity_id: UUID,
    db: Session = Depends(get_db),
    user = Depends(require_super_admin)  # Usually restricted
):
    """Soft delete pattern."""
    entity = db.query(EntityModel).filter(
        EntityModel.id == entity_id,
        EntityModel.is_active == True  # Only "active" records
    ).first()

    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity {entity_id} not found"
        )

    # Soft delete
    entity.is_active = False
    db.commit()
    return None
```

### Relationship Patterns

**One-to-Many:**
```python
class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(UUID(as_uuid=True), primary_key=True)

    # Relationship
    alerts = relationship("Alert", back_populates="tenant")

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    # Relationship
    tenant = relationship("Tenant", back_populates="alerts")
```

**Many-to-Many:**
```python
# Association table
case_alerts = Table(
    "case_alerts",
    Base.metadata,
    Column("case_id", UUID(as_uuid=True), ForeignKey("cases.id"), primary_key=True),
    Column("alert_id", UUID(as_uuid=True), ForeignKey("alerts.id"), primary_key=True),
)

class Case(Base):
    __tablename__ = "cases"
    id = Column(UUID(as_uuid=True), primary_key=True)

    # Many-to-many
    alerts = relationship("Alert", secondary=case_alerts, back_populates="cases")

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(UUID(as_uuid=True), primary_key=True)

    # Many-to-many
    cases = relationship("Case", secondary=case_alerts, back_populates="alerts")
```

### PostgreSQL-Specific Patterns

**IP Address (INET):**
```python
# Model
src_ip = Column(INET)
dst_ip = Column(INET)

# Schema (converts to string)
src_ip: Optional[str] = None  # "192.168.1.1"
dst_ip: Optional[str] = None

# Query
query.filter(Alert.src_ip == "192.168.1.100")
```

**Tags (ARRAY):**
```python
# Model
tags = Column(ARRAY(Text))

# Schema
tags: Optional[List[str]] = None

# Query - contains
query.filter(Alert.tags.contains(["malware"]))

# Query - overlap
query.filter(Alert.tags.overlap(["malware", "ransomware"]))
```

**Metadata (JSONB):**
```python
# Model
meta_data = Column(JSONB)

# Schema
meta_data: Optional[Dict[str, Any]] = None

# Store
alert.meta_data = {"source": "wazuh", "rule_id": "5710"}

# Query - key exists
query.filter(Alert.meta_data.has_key("source"))

# Query - value match
query.filter(Alert.meta_data["source"].astext == "wazuh")
```

### Transaction Pattern

```python
try:
    # Multiple operations
    db.add(entity1)
    db.add(entity2)

    # Related update
    existing.status = "updated"

    # Commit all together
    db.commit()

    # Refresh to get DB-generated values
    db.refresh(entity1)
    db.refresh(entity2)

    return entity1
except Exception as e:
    db.rollback()
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Database error: {str(e)}"
    )
```

---

## API Development Guidelines

### REST Conventions

| HTTP Method | Purpose | URL Pattern | Status Code |
|-------------|---------|-------------|-------------|
| GET | List all | `/entities` | 200 OK |
| GET | Get one | `/entities/{id}` | 200 OK |
| POST | Create | `/entities` | 201 Created |
| PATCH | Update | `/entities/{id}` | 200 OK |
| DELETE | Delete | `/entities/{id}` | 204 No Content |
| POST | Action | `/entities/{id}/action` | 200 OK or 202 Accepted |

### Endpoint Structure

```python
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

router = APIRouter(prefix="/entities", tags=["entities"])

@router.get("/", response_model=List[EntitySchema])
async def list_entities(
    # Query parameters
    tenant_id: Optional[UUID] = Query(None, description="Filter by tenant"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Page size"),
    # Dependencies
    db: Session = Depends(get_db),
    context: TenantContext = Depends(get_tenant_context)
):
    """
    List entities with pagination and filtering.

    - **tenant_id**: Filter by specific tenant (Hubsec staff only)
    - **status**: Filter by status
    - **skip**: Number of records to skip
    - **limit**: Maximum records to return
    """
    # Implementation...
    pass

@router.post("/", response_model=EntitySchema, status_code=status.HTTP_201_CREATED)
async def create_entity(
    entity: EntityCreate,
    db: Session = Depends(get_db),
    context: TenantContext = Depends(require_auth)
):
    """Create a new entity."""
    # Validate access
    if not context.can_access_tenant(entity.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
        )

    # Create
    db_entity = EntityModel(**entity.model_dump())
    db.add(db_entity)
    db.commit()
    db.refresh(db_entity)
    return db_entity
```

### Response Status Codes

```python
# Success
status.HTTP_200_OK              # GET, PATCH successful
status.HTTP_201_CREATED         # POST successful
status.HTTP_204_NO_CONTENT      # DELETE successful

# Client Errors
status.HTTP_400_BAD_REQUEST     # Invalid input
status.HTTP_401_UNAUTHORIZED    # Not authenticated
status.HTTP_403_FORBIDDEN       # Not authorized for this resource
status.HTTP_404_NOT_FOUND       # Resource doesn't exist
status.HTTP_409_CONFLICT        # Duplicate or constraint violation

# Server Errors
status.HTTP_500_INTERNAL_SERVER_ERROR  # Database error, unexpected error
status.HTTP_503_SERVICE_UNAVAILABLE    # External service down
```

### Pagination

```python
@router.get("/", response_model=List[Entity])
async def list_entities(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Standard pagination pattern."""
    query = db.query(EntityModel)
    total = query.count()
    results = query.offset(skip).limit(limit).all()

    # Note: Can add total count to response headers if needed
    # response.headers["X-Total-Count"] = str(total)

    return results
```

### Search and Filtering

```python
@router.get("/search")
async def search_entities(
    q: str = Query(..., min_length=2, description="Search query"),
    field: str = Query("all", description="Field to search"),
    db: Session = Depends(get_db)
):
    """Search with multiple fields."""
    query = db.query(EntityModel)

    if field == "all":
        # Search across multiple fields
        query = query.filter(
            or_(
                EntityModel.name.ilike(f"%{q}%"),
                EntityModel.description.ilike(f"%{q}%")
            )
        )
    else:
        # Search specific field
        query = query.filter(getattr(EntityModel, field).ilike(f"%{q}%"))

    return query.all()
```

---

## Multi-Tenant Considerations

### Tenant Isolation Rules

**CRITICAL**: Every operation MUST respect tenant boundaries.

1. **Query Filtering**: Always filter by `tenant_id`
2. **Access Validation**: Check `context.can_access_tenant(tenant_id)`
3. **Creation**: Validate user can create in target tenant
4. **Updates**: Verify ownership before allowing changes
5. **Deletion**: Super admin or tenant admin only

### Role Hierarchy

```
SUPER_ADMIN (Level 5)
  ├─ Full platform access
  ├─ All tenants visible
  ├─ Can create/delete tenants
  └─ Can manage all users

HUBSEC_ANALYST (Level 4)
  ├─ View all tenants
  ├─ Limited admin operations
  ├─ Cross-tenant analytics
  └─ Cannot delete tenants

TENANT_ADMIN (Level 3)
  ├─ Full access to assigned tenant(s)
  ├─ Manage tenant users
  ├─ Configure integrations
  └─ Cannot see other tenants

ANALYST (Level 2)
  ├─ Work within assigned tenant(s)
  ├─ Create/update incidents, cases, alerts
  ├─ Cannot manage users
  └─ Cannot see other tenants

VIEWER (Level 1)
  ├─ Read-only access
  ├─ Assigned tenant(s) only
  ├─ Cannot create/update
  └─ Cannot see other tenants
```

### Access Control Helpers

```python
# In backend/app/middleware/tenant.py

class TenantContext:
    """Encapsulates tenant and user context."""

    def __init__(self, user=None, tenant=None):
        self.user = user
        self.tenant = tenant

    def is_super_admin(self) -> bool:
        """Check if user is super admin."""
        return self.user and self.user.role == UserRole.SUPER_ADMIN

    def is_hubsec_staff(self) -> bool:
        """Check if user is Hubsec staff (super admin or analyst)."""
        return self.user and self.user.role in [
            UserRole.SUPER_ADMIN,
            UserRole.HUBSEC_ANALYST
        ]

    def can_access_tenant(self, tenant_id: UUID) -> bool:
        """Check if user can access specific tenant."""
        if self.is_hubsec_staff():
            return True  # Hubsec staff can access all

        if not self.user:
            return False

        # Check if tenant is in user's assigned tenants
        return any(t.id == tenant_id for t in self.user.tenants)

    def get_accessible_tenant_ids(self) -> List[UUID]:
        """Get list of tenant IDs user can access."""
        if not self.user:
            return []
        return [t.id for t in self.user.tenants]

# Dependencies
async def require_super_admin(
    context: TenantContext = Depends(get_tenant_context)
):
    """Require super admin role."""
    if not context.is_super_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return context.user

async def require_hubsec_staff(
    context: TenantContext = Depends(get_tenant_context)
):
    """Require Hubsec staff role."""
    if not context.is_hubsec_staff():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hubsec staff access required"
        )
    return context.user
```

### Global vs Tenant-Specific Resources

Some resources can be **global** (shared across all tenants) or **tenant-specific**.

**Example: Playbooks**

```python
class Playbook(Base):
    __tablename__ = "playbooks"

    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)  # NULL = global
    is_global = Column(Boolean, default=False)
    # ...

# Query for playbooks
def get_available_playbooks(tenant_id: UUID, db: Session):
    """Get both global and tenant-specific playbooks."""
    return db.query(Playbook).filter(
        or_(
            Playbook.is_global == True,  # Global playbooks
            Playbook.tenant_id == tenant_id  # Tenant-specific
        )
    ).all()
```

---

## Authentication & Authorization

### Current Implementation (Testing/Mock)

**Header-Based Authentication** - Used for testing, NOT production-ready.

**Headers:**
```bash
X-User-ID: <uuid>           # User UUID
X-Username: <username>      # Alternative to UUID
X-Tenant-ID: <uuid>         # Tenant context (optional)
X-Tenant-Code: <code>       # Alternative to tenant UUID
```

**Implementation:**
```python
# backend/app/middleware/tenant.py

async def get_current_user_mock(
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    username: Optional[str] = Header(None, alias="X-Username"),
    db: Session = Depends(get_db)
):
    """Mock authentication via headers - FOR TESTING ONLY."""
    if not user_id and not username:
        return None  # Anonymous access (some endpoints allow)

    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
    else:
        user = db.query(User).filter(User.username == username).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive user"
        )

    return user
```

### Future: JWT Authentication (Planned)

**Implementation Pattern:**

```python
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# JWT token generation
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# JWT token validation
async def get_current_user_jwt(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    return user

# Login endpoint
@router.post("/auth/login")
async def login(
    credentials: LoginCredentials,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == credentials.username).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
```

### Role-Based Endpoint Protection

```python
# Public endpoint - no auth required
@router.get("/health")
async def health_check():
    return {"status": "healthy"}

# Authenticated - any logged-in user
@router.get("/profile")
async def get_profile(user = Depends(require_auth)):
    return user

# Role-restricted - Hubsec staff only
@router.get("/admin/tenants")
async def list_all_tenants(user = Depends(require_hubsec_staff)):
    return tenants

# Role-restricted - Super admin only
@router.post("/tenants")
async def create_tenant(
    tenant: TenantCreate,
    user = Depends(require_super_admin)
):
    # Create tenant
    pass
```

---

## Testing Strategy

### Current State

- **No unit tests** currently exist (pytest configured but no test files)
- **Manual testing** via:
  - Swagger UI at `/api/docs`
  - Curl commands in **API_TESTING_GUIDE.md**
  - Postman/Insomnia collections (user-created)

### Testing Infrastructure (Configured)

```python
# requirements.txt includes:
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
```

### Recommended Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures
├── test_api/
│   ├── __init__.py
│   ├── test_tenants.py
│   ├── test_alerts.py
│   ├── test_incidents.py
│   └── test_cases.py
├── test_services/
│   ├── test_wazuh_normalizer.py
│   └── test_case_engine.py
└── test_models/
    └── test_multitenant_models.py
```

### Testing Patterns

**Fixture Example (conftest.py):**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main_multitenant import app
from backend.app.database_multitenant import Base, get_db
from backend.app.models.models_multitenant import Tenant, User

# Test database
SQLALCHEMY_TEST_DATABASE_URL = "postgresql://test:test@localhost/hubsec_test"

@pytest.fixture(scope="session")
def engine():
    """Create test database engine."""
    engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(engine):
    """Create fresh database session for each test."""
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.rollback()
    session.close()

@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_tenant(db_session):
    """Create test tenant."""
    tenant = Tenant(
        name="Test Tenant",
        code="TEST",
        description="Test tenant for unit tests"
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant

@pytest.fixture
def test_user(db_session, test_tenant):
    """Create test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed",
        role=UserRole.ANALYST
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Associate with tenant
    user.tenants.append(test_tenant)
    db_session.commit()

    return user
```

**Test Example:**

```python
# tests/test_api/test_tenants.py

def test_list_tenants(client, test_tenant, test_user):
    """Test listing tenants."""
    response = client.get(
        "/api/v1/tenants",
        headers={"X-Username": test_user.username}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["code"] == "TEST"

def test_create_tenant_requires_super_admin(client, test_user):
    """Test that only super admin can create tenants."""
    response = client.post(
        "/api/v1/tenants",
        headers={"X-Username": test_user.username},
        json={
            "name": "New Tenant",
            "code": "NEW",
            "description": "New tenant"
        }
    )
    assert response.status_code == 403  # Forbidden

def test_get_tenant_by_id(client, test_tenant, test_user):
    """Test getting tenant by ID."""
    response = client.get(
        f"/api/v1/tenants/{test_tenant.id}",
        headers={"X-Username": test_user.username}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Tenant"
```

**Running Tests:**

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest tests/test_api/test_tenants.py

# Run specific test
pytest tests/test_api/test_tenants.py::test_list_tenants

# Run with verbose output
pytest -v

# Run with print statements
pytest -s
```

### Manual Testing with Curl

See **API_TESTING_GUIDE.md** for comprehensive curl examples.

**Quick Test Commands:**

```bash
# Get UUIDs from database
export USER_ID=$(psql $DATABASE_URL -t -c "SELECT id FROM users WHERE username='hubsec_analyst1';" | tr -d ' ')

# Test authentication
curl -X GET "http://localhost:8000/api/v1/tenants" \
  -H "X-Username: hubsec_analyst1"

# Test tenant creation (super admin only)
curl -X POST "http://localhost:8000/api/v1/tenants" \
  -H "Content-Type: application/json" \
  -H "X-Username: superadmin" \
  -d '{
    "name": "New Client",
    "code": "NEWCLIENT",
    "description": "New client organization"
  }'

# Test alert creation
curl -X POST "http://localhost:8000/api/v1/alerts" \
  -H "Content-Type: application/json" \
  -H "X-Username: econet_admin" \
  -d '{
    "tenant_id": "'"$TENANT_ID"'",
    "source": "Manual",
    "severity": "high",
    "rule_description": "Test alert",
    "src_ip": "192.168.1.100"
  }'
```

---

## Error Handling

### Standard Error Responses

```python
from fastapi import HTTPException, status

# 400 Bad Request - Invalid input
if not entity.name:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Entity name is required"
    )

# 401 Unauthorized - Not authenticated
if not user:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required"
    )

# 403 Forbidden - Not authorized
if not context.can_access_tenant(tenant_id):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied to this tenant"
    )

# 404 Not Found - Resource doesn't exist
entity = db.query(EntityModel).filter(EntityModel.id == entity_id).first()
if not entity:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Entity {entity_id} not found"
    )

# 409 Conflict - Duplicate or constraint violation
existing = db.query(EntityModel).filter(EntityModel.code == code).first()
if existing:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"Entity with code '{code}' already exists"
    )

# 500 Internal Server Error - Database error
try:
    db.add(entity)
    db.commit()
except Exception as e:
    db.rollback()
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Database error: {str(e)}"
    )
```

### Database Transaction Error Handling

```python
@router.post("/", response_model=EntitySchema)
async def create_entity(
    entity: EntityCreate,
    db: Session = Depends(get_db)
):
    """Create entity with proper error handling."""
    try:
        # Validate
        if not entity.name:
            raise ValueError("Name is required")

        # Create
        db_entity = EntityModel(**entity.model_dump())
        db.add(db_entity)
        db.commit()
        db.refresh(db_entity)

        return db_entity

    except ValueError as e:
        # Business logic error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except IntegrityError as e:
        # Database constraint violation
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate entity or constraint violation"
        )
    except Exception as e:
        # Unexpected error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )
```

### Validation Errors

Pydantic automatically handles validation errors with detailed messages:

```python
# Invalid input automatically returns 422 Unprocessable Entity
{
  "detail": [
    {
      "loc": ["body", "severity"],
      "msg": "value is not a valid enumeration member; permitted: 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'",
      "type": "type_error.enum"
    }
  ]
}
```

---

## Code Quality

### Formatting and Linting

```bash
# Format code with Black
black backend/

# Check format without changes
black --check backend/

# Lint with flake8
flake8 backend/

# Type checking with mypy
mypy backend/
```

### Pre-Commit Recommendations

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

### Code Review Checklist

When reviewing or creating code, check for:

- [ ] Tenant filtering applied to all multi-tenant queries
- [ ] Access control validated (can_access_tenant)
- [ ] Soft delete used instead of hard delete
- [ ] Proper error handling with appropriate status codes
- [ ] Type hints on all function signatures
- [ ] Docstrings on complex functions
- [ ] Pydantic schemas follow Create/Update/InDB pattern
- [ ] Database transactions committed and refreshed
- [ ] No hardcoded credentials or secrets
- [ ] Proper pagination on list endpoints
- [ ] Input validation via Pydantic
- [ ] Relationships defined bidirectionally
- [ ] Foreign keys properly indexed

---

## Important Commands

### Database Commands

```bash
# Connect to PostgreSQL
psql $DATABASE_URL

# Or with explicit connection
psql -h localhost -U hubsec -d hubsec_multitenant

# List tables
\dt

# Describe table
\d tenants

# Count records
SELECT COUNT(*) FROM tenants;

# Get UUIDs for testing
SELECT id, username, role FROM users;
SELECT id, name, code FROM tenants;

# Check user-tenant associations
SELECT u.username, t.name
FROM users u
JOIN user_tenants ut ON u.id = ut.user_id
JOIN tenants t ON ut.tenant_id = t.id;
```

### Application Commands

```bash
# Start multi-tenant API (development)
uvicorn backend.app.main_multitenant:app --reload

# Start with custom host/port
uvicorn backend.app.main_multitenant:app --reload --host 0.0.0.0 --port 8080

# Start single-tenant API
uvicorn backend.app.main:app --reload

# Initialize multi-tenant database
python scripts/init_db_multitenant.py --database-url "$DATABASE_URL" --drop --seed

# Initialize single-tenant database
python scripts/init_db.py --seed
```

### Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Execute command in container
docker-compose exec api python scripts/init_db_multitenant.py --seed

# Restart service
docker-compose restart api

# Stop all services
docker-compose down

# Rebuild and start
docker-compose up -d --build
```

### Development Workflow

```bash
# Setup development environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run code formatter
black backend/

# Run linter
flake8 backend/

# Run type checker
mypy backend/

# Run tests (when implemented)
pytest
pytest --cov=backend --cov-report=html

# View coverage report
open htmlcov/index.html
```

---

## Known Limitations

### Current Limitations

1. **Authentication**: Header-based mock authentication (not production-ready)
   - **Status**: JWT implementation planned
   - **Impact**: Cannot be used in production without real authentication

2. **Database Migrations**: Using `create_all()` instead of Alembic migrations
   - **Status**: Alembic configured but not implemented
   - **Impact**: Schema changes require manual migration or database recreation

3. **No Unit Tests**: Test framework configured but no test files
   - **Status**: Manual testing via Swagger UI and curl
   - **Impact**: No automated testing, potential for regressions

4. **No Rate Limiting**: No request rate limiting implemented
   - **Status**: Planned feature
   - **Impact**: Vulnerable to abuse in production

5. **No Caching**: No Redis or caching layer
   - **Status**: Redis dependency included but not integrated
   - **Impact**: Slower response times for frequently accessed data

6. **Basic Logging**: Minimal structured logging
   - **Status**: python-json-logger installed but not fully configured
   - **Impact**: Difficult to debug production issues

7. **No Email Notifications**: No email integration for alerts
   - **Status**: Planned feature
   - **Impact**: Users don't receive email notifications

8. **No Websockets**: No real-time updates
   - **Status**: Not planned
   - **Impact**: UI must poll for updates

9. **No Background Tasks**: No Celery or background job processing
   - **Status**: Planned for async operations
   - **Impact**: Long-running operations block requests

10. **Limited Search**: Basic SQL ILIKE search only
    - **Status**: Full-text search planned
    - **Impact**: Slow search on large datasets

### Workarounds

**For Authentication (Development/Testing):**
```bash
# Use header-based auth with predefined users
curl -H "X-Username: hubsec_analyst1" http://localhost:8000/api/v1/tenants
```

**For Database Migrations:**
```bash
# Currently: Drop and recreate
python scripts/init_db_multitenant.py --drop --seed

# Future: Use Alembic
alembic revision --autogenerate -m "Add new column"
alembic upgrade head
```

**For Testing:**
```bash
# Use Swagger UI for manual testing
# Visit: http://localhost:8000/api/docs

# Or use curl scripts from API_TESTING_GUIDE.md
```

---

## Quick Reference

### File Locations

| Purpose | Path |
|---------|------|
| Multi-tenant app | `backend/app/main_multitenant.py` |
| Multi-tenant models | `backend/app/models/models_multitenant.py` |
| Multi-tenant schemas | `backend/app/schemas/schemas_multitenant.py` |
| Database config | `backend/app/database_multitenant.py` |
| Tenant middleware | `backend/app/middleware/tenant.py` |
| API endpoints | `backend/app/api/v1/*.py` |
| Wazuh normalizer | `backend/app/services/wazuh_normalizer.py` |
| Case engine | `backend/app/services/case_engine.py` |
| DB init script | `scripts/init_db_multitenant.py` |
| Wazuh mapping | `config/wazuh_mapping.yml` |
| Severity rules | `config/severity_rules.yml` |

### Key Enums

```python
# Severity
CRITICAL, HIGH, MEDIUM, LOW, INFO

# Incident Status
OPEN, IN_PROGRESS, INVESTIGATING, RESOLVED, CLOSED, FALSE_POSITIVE

# Case Status
OPEN, IN_PROGRESS, PENDING, RESOLVED, CLOSED

# Alert Status
NEW, TRIAGED, IN_CASE, IGNORED, RESOLVED

# User Role
SUPER_ADMIN, HUBSEC_ANALYST, TENANT_ADMIN, ANALYST, VIEWER

# Asset Type
SERVER, WORKSTATION, NETWORK_DEVICE, DATABASE, MOBILE_DEVICE,
IOT_DEVICE, CLOUD_RESOURCE, APPLICATION, OTHER

# Integration Type
WAZUH, IRIS, JIRA, SERVICENOW, FORTIGATE, PFSENSE, SURICATA,
MISP, THEHIVE, CORTEX, SPLUNK, ELASTIC, OTHER
```

### Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@localhost/dbname

# Optional
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=your-secret-key
ALLOWED_ORIGINS=http://localhost:3000
```

### Common Patterns Quick Reference

**Query with tenant filtering:**
```python
query = db.query(Model).filter(Model.is_active == True)
if context.is_hubsec_staff():
    if tenant_id:
        query = query.filter(Model.tenant_id == tenant_id)
else:
    query = query.filter(Model.tenant_id.in_(context.get_accessible_tenant_ids()))
```

**Check tenant access:**
```python
if not context.can_access_tenant(entity.tenant_id):
    raise HTTPException(status_code=403, detail="Access denied")
```

**Soft delete:**
```python
entity.is_active = False
db.commit()
```

**Transaction with error handling:**
```python
try:
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity
except Exception as e:
    db.rollback()
    raise HTTPException(status_code=500, detail=str(e))
```

---

## Additional Resources

### Documentation Files

- **README.md**: Main project overview and setup instructions
- **IMPLEMENTATION_STATUS.md**: Complete implementation checklist and statistics
- **API_TESTING_GUIDE.md**: Comprehensive curl examples for all endpoints
- **MULTITENANT_API_GUIDE.md**: Multi-tenant setup and testing scenarios
- **MULTITENANT_MIGRATION_GUIDE.md**: Migration from single to multi-tenant
- **ENHANCED_DATABASE_SCHEMA.md**: Complete schema documentation with ER diagrams
- **QUICK_START.md**: 5-minute setup guide
- **BUILD_COMPLETE.md**: Project completion summary

### Interactive Documentation

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- OpenAPI JSON: http://localhost:8000/api/openapi.json

### External Documentation

- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://docs.sqlalchemy.org/
- Pydantic: https://docs.pydantic.dev/
- PostgreSQL: https://www.postgresql.org/docs/

---

**Last Updated**: 2025-11-23
**Maintained By**: Development Team
**For Questions**: See project README or open an issue
