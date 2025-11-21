# 🛡️ Hubsec SOC Platform

**Central Multi-Tenant Incident & Threat Management Platform for Security Operations Centers**

A comprehensive, production-ready Security Operations Center (SOC) platform built with FastAPI and PostgreSQL, designed to centralize incident management, alert correlation, and threat response for multiple client organizations.

---

## ✨ Platform Versions

| Version | Database | Use Case | Status |
|---------|----------|----------|--------|
| **Multi-Tenant** | PostgreSQL | Production, Multiple Organizations | ✅ **Recommended** |
| Single-Tenant | SQLite/PostgreSQL | Development, Single Organization | ✅ Available |

---

## 🌟 Features

### 🏢 Multi-Tenant Capabilities (NEW)
- **Multiple Organizations** - Serve multiple clients from one platform
- **Data Isolation** - Complete tenant separation at database level
- **Tenant Management** - Create, configure, and manage client organizations
- **Multi-Tenant RBAC** - Users can access multiple tenants with different roles
- **Tenant-Aware APIs** - All endpoints automatically filter by tenant
- **Cross-Tenant Analytics** - Hubsec staff can view all tenants

### 🔌 Integration Management
- **Source Systems API** - Manage integrations (Wazuh, IRIS, Jira, FortiGate, etc.)
- **Integration Health Checks** - Monitor connectivity and sync status
- **Multiple Integrations per Tenant** - Each client has their own integrations
- **Sync Triggers** - Manual or automated synchronization

### 💻 Asset Management
- **IT Asset Inventory** - Track servers, workstations, network devices, databases
- **Asset Criticality** - Critical, High, Medium, Low classifications
- **Asset Search** - Search by hostname, IP address, or tags
- **Asset-Alert Correlation** - Link alerts to specific assets
- **Asset Heartbeat** - Track last seen timestamps

### 📖 Playbook Automation
- **Incident Response Playbooks** - Automated runbooks for common incidents
- **Global & Tenant Playbooks** - Shared or organization-specific playbooks
- **Execution Tracking** - Monitor playbook progress per case
- **Step-by-Step Workflow** - Track completed steps and metadata

### 🚨 Core SOC Capabilities
- **Alert Management** - Ingest, normalize, and triage security alerts
- **Incident Tracking** - Full lifecycle incident management
- **Case Management** - Investigation cases with alert correlation
- **User Management** - Multi-tenant role-based access control
- **Wazuh Integration** - Native webhook support for Wazuh SIEM
- **Dashboard & Analytics** - Real-time metrics per tenant or globally
- **Collaboration** - Comments and activity logs

### 🔐 Security & Access Control
- **Tenant Isolation** - Users only see their assigned tenants
- **Role Hierarchy** - Super Admin → Hubsec Analyst → Tenant Admin → Analyst → Viewer
- **Resource Permissions** - Fine-grained access control per resource
- **Audit Trail** - Complete activity logging

### 🚀 Technical Highlights
- **RESTful API** - 32+ well-documented endpoints
- **PostgreSQL Optimized** - UUID, INET, JSONB, ARRAY types
- **Async Architecture** - FastAPI with async/await support
- **Comprehensive Schemas** - Pydantic validation throughout
- **Extensible Design** - Easy to add new features
- **API Documentation** - Auto-generated Swagger UI & ReDoc

---

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#️-configuration)
- [API Documentation](#-api-documentation)
- [Integration Guide](#-integration-guide)
- [Development](#-development)
- [Deployment](#-deployment)
- [Contributing](#-contributing)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 12+ (for multi-tenant)
- Docker & Docker Compose (optional)

### Option 1: Multi-Tenant Mode (Recommended)

```bash
# 1. Clone repository
git clone <repository-url>
cd Hubsec-Central-Incident-Threat-Management-Platform

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup PostgreSQL
sudo -u postgres psql
CREATE DATABASE hubsec_multitenant;
CREATE USER hubsec WITH PASSWORD 'hubsec';
GRANT ALL PRIVILEGES ON DATABASE hubsec_multitenant TO hubsec;
\q

# 4. Set environment
export DATABASE_URL="postgresql://hubsec:hubsec@localhost/hubsec_multitenant"

# 5. Initialize with sample data
python scripts/init_db_multitenant.py --database-url "$DATABASE_URL" --drop --seed

# 6. Start multi-tenant API
uvicorn backend.app.main_multitenant:app --reload
```

**Access**:
- **API Documentation**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/health
- **Database Info**: http://localhost:8000/api/v1/info/database

**Sample Data**:
- 3 Tenants (Econet, PostBank, TelOne)
- 7 Users (3 Hubsec staff + 4 tenant users)
- 5 Source Systems (Wazuh, IRIS, Jira)
- 4 Assets, 50 Alerts, 2 Incidents, 2 Cases

**Test Credentials**:
```
Hubsec Super Admin: superadmin / admin123
Hubsec Analyst:     hubsec_analyst1 / analyst123
Econet Admin:       econet_admin / econet123
PostBank Admin:     postbank_admin / postbank123
```

**Authentication**: Use headers for testing:
```bash
curl -X GET "http://localhost:8000/api/v1/tenants" \
  -H "X-Username: hubsec_analyst1"
```

### Option 2: Single-Tenant Mode (Development)

```bash
# 1-2. Same as above

# 3. Initialize SQLite database
python scripts/init_db.py --seed

# 4. Start single-tenant API
uvicorn backend.app.main:app --reload
```

**Access**:
- **API Documentation**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/health

**Default Credentials**:
```
Admin:    admin / admin123
Analyst:  analyst1 / analyst123
Manager:  manager / manager123
```

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    External Sources                      │
│  (Wazuh, Suricata, Custom Integrations)                 │
└─────────────────┬───────────────────────────────────────┘
                  │ Webhooks / API
                  ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Application                     │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Alert Ingestion & Normalization                 │  │
│  │  • Wazuh Normalizer                              │  │
│  │  • Field Mapping                                 │  │
│  │  • Severity Calculation                          │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Case Management Engine                          │  │
│  │  • Alert Correlation                             │  │
│  │  • Automatic Case Creation                       │  │
│  │  • Priority Escalation                           │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  REST API Endpoints (32 endpoints)               │  │
│  │  • /api/v1/tenants (6)                           │  │
│  │  • /api/v1/source-systems (7)                    │  │
│  │  • /api/v1/assets (9)                            │  │
│  │  • /api/v1/playbooks (10)                        │  │
│  │  • /api/v1/incidents (legacy)                    │  │
│  │  • /api/v1/cases (legacy)                        │  │
│  │  • /api/v1/alerts (legacy)                       │  │
│  │  • /api/v1/users (legacy)                        │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│              Database (PostgreSQL - Multi-Tenant)        │
│  • Tenants  • Source Systems  • Assets  • Playbooks     │
│  • Incidents  • Cases  • Alerts  • Users                │
│  • Comments   • Activities  • External References       │
└─────────────────────────────────────────────────────────┘
```

### Database Schema (Multi-Tenant)

**Core Entities (15 tables):**
- **Tenant** - Client organization (Econet, PostBank, etc.)
- **SourceSystem** - Integration endpoints (Wazuh, IRIS, Jira)
- **Asset** - IT assets/endpoints with criticality tracking
- **Playbook** - Automated incident response runbooks
- **Incident** - High-level security incident
- **Case** - Investigation case (belongs to incident)
- **Alert** - Individual security alert (can belong to multiple cases)
- **User** - SOC analyst or administrator with multi-tenant access
- **Comment** - Discussion on incidents/cases
- **Activity** - Audit trail for case activities
- **CasePlaybook** - Playbook execution tracking per case
- **CaseExternalRef** - External system references (IRIS cases, Jira tickets)

**Multi-Tenant Relationships:**
- 1 Tenant → Many Users (many-to-many with roles per tenant)
- 1 Tenant → Many Source Systems, Assets, Alerts, Incidents, Cases
- 1 Playbook → Can be global (NULL tenant) or tenant-specific
- 1 Incident → Many Cases
- 1 Case → Many Alerts (many-to-many)
- 1 Case → Many Playbooks (execution tracking)
- 1 Asset → Many Alerts (correlation)

For detailed schema documentation, see [ENHANCED_DATABASE_SCHEMA.md](./docs/ENHANCED_DATABASE_SCHEMA.md)

---

## 💻 Installation

### Method 1: Local Installation

```bash
# 1. Clone repository
git clone <repository-url>
cd Hubsec-Central-Incident-Threat-Management-Platform

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialize database
python scripts/init_db.py --seed

# 5. Start API
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Method 2: Docker Deployment

```bash
# Start all services
docker-compose up -d

# Initialize database in container
docker-compose exec api python scripts/init_db.py --seed

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### Method 3: Docker with PostgreSQL

```bash
# Use PostgreSQL backend
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
docker-compose up api

# Access pgAdmin (optional)
docker-compose --profile tools up pgadmin
# Open http://localhost:5050
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/hubsec
# Or for SQLite:
# DATABASE_URL=sqlite:///./hubsec.db

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# Security
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
```

### Configuration Files

**config/wazuh_mapping.yml** - Field mappings for Wazuh alerts
```yaml
field_mappings:
  source_ip:
    - data.srcip
    - data.src_ip
  username:
    - data.dstuser
    - data.win.eventdata.targetUserName
```

**config/severity_rules.yml** - Severity calculation rules
```yaml
rule_level_mapping:
  range:
    '0-3': info
    '4-6': low
    '7-10': medium
    '11-14': high
    '15-20': critical
```

---

## 📚 API Documentation

### Base URL
```
http://localhost:8000/api/v1
```

### Main Endpoints (76 total)

#### 🏢 Tenants (6 endpoints)
```http
GET    /tenants            # List all tenants
GET    /tenants/{id}       # Get tenant details
POST   /tenants            # Create tenant
PATCH  /tenants/{id}       # Update tenant
DELETE /tenants/{id}       # Delete tenant (soft)
GET    /tenants/{id}/stats # Get tenant statistics
```

#### 🔌 Source Systems (7 endpoints)
```http
GET    /source-systems                # List integrations
GET    /source-systems/{id}           # Get integration details
POST   /source-systems                # Create integration
PATCH  /source-systems/{id}           # Update integration
DELETE /source-systems/{id}           # Delete integration (soft)
POST   /source-systems/{id}/sync      # Trigger sync
GET    /source-systems/{id}/health    # Check health
```

#### 💻 Assets (9 endpoints)
```http
GET    /assets                # List all assets
GET    /assets/{id}           # Get asset details
POST   /assets                # Create asset
PATCH  /assets/{id}           # Update asset
DELETE /assets/{id}           # Delete asset (soft)
POST   /assets/{id}/heartbeat # Update last_seen timestamp
GET    /assets/{id}/alerts    # Get alerts for asset
```

#### 📖 Playbooks (10 endpoints)
```http
GET    /playbooks                     # List all playbooks
GET    /playbooks/{id}                # Get playbook details
POST   /playbooks                     # Create playbook
PATCH  /playbooks/{id}                # Update playbook
DELETE /playbooks/{id}                # Delete playbook (soft)
POST   /playbooks/execute             # Attach playbook to case
PATCH  /playbooks/executions/{id}    # Update execution status
GET    /playbooks/executions/case/{id} # Get case playbooks
```

#### 🚨 Incidents (8 endpoints)
```http
GET    /incidents                   # List incidents (tenant-filtered)
POST   /incidents                   # Create incident
GET    /incidents/{id}              # Get incident details
PATCH  /incidents/{id}              # Update incident
DELETE /incidents/{id}              # Soft delete
POST   /incidents/{id}/comments     # Add comment
GET    /incidents/{id}/timeline     # Get event timeline
GET    /incidents/{id}/statistics   # Get statistics
```

#### 📂 Cases (14 endpoints)
```http
GET    /cases                          # List cases (tenant-filtered)
POST   /cases                          # Create case
GET    /cases/{id}                     # Get case details
PATCH  /cases/{id}                     # Update case
DELETE /cases/{id}                     # Soft delete
POST   /cases/{id}/alerts              # Add alerts to case
DELETE /cases/{id}/alerts/{alert_id}   # Remove alert
POST   /cases/{id}/comments            # Add comment
GET    /cases/{id}/statistics          # Get statistics
POST   /cases/{id}/escalate            # Escalate case
POST   /cases/{id}/playbooks/{id}/attach  # Attach playbook
GET    /cases/{id}/playbooks           # List case playbooks
POST   /cases/{id}/external-refs       # Create external reference
GET    /cases/{id}/external-refs       # List external references
```

#### 🔔 Alerts (9 endpoints)
```http
GET    /alerts                   # List alerts (tenant-filtered)
POST   /alerts                   # Create alert
GET    /alerts/{id}              # Get alert details
PATCH  /alerts/{id}              # Update alert
DELETE /alerts/{id}              # Soft delete
POST   /alerts/wazuh/webhook     # Wazuh integration endpoint
POST   /alerts/bulk-triage       # Bulk status update
GET    /alerts/search/ip/{ip}    # Search by IP address
GET    /alerts/search/hostname/{hostname}  # Search by hostname
```

#### 👤 Users (13 endpoints)
```http
GET    /users                          # List users (tenant-filtered)
POST   /users                          # Create user
GET    /users/{id}                     # Get user details
GET    /users/username/{username}      # Get by username
PATCH  /users/{id}                     # Update user
DELETE /users/{id}                     # Soft delete
POST   /users/{id}/activate            # Activate user
POST   /users/{id}/deactivate          # Deactivate user
POST   /users/{id}/tenants/{id}/assign # Assign to tenant
DELETE /users/{id}/tenants/{id}/unassign # Unassign from tenant
GET    /users/{id}/tenants             # Get user tenants
GET    /users/{id}/workload            # Get workload statistics
GET    /users/{id}/activity            # Get activity log
```

### Interactive Documentation
Visit http://localhost:8000/api/docs for the full interactive API documentation with request/response examples.

For detailed testing examples, see [API_TESTING_GUIDE.md](./API_TESTING_GUIDE.md).

---

## 🔌 Integration Guide

### Integrating with Wazuh

**1. Configure Wazuh Integration**

In `/var/ossec/etc/ossec.conf`:
```xml
<integration>
  <name>custom-webhook</name>
  <hook_url>http://your-hubsec-server:8000/api/v1/alerts/wazuh/webhook</hook_url>
  <level>7</level>
  <alert_format>json</alert_format>
</integration>
```

**2. Restart Wazuh Manager**
```bash
systemctl restart wazuh-manager
```

**3. Verify Integration**
Check the Hubsec logs to see alerts being received:
```bash
docker-compose logs -f api
```

### Custom Alert Sources

Create a custom integration by posting to `/api/v1/alerts`:

```python
import requests

alert = {
    "source": "CustomSource",
    "source_id": "unique-id-123",
    "severity": "high",
    "rule_description": "Custom alert description",
    "timestamp": "2024-01-15T10:30:00Z",
    "src_ip": "192.168.1.100"
}

response = requests.post(
    "http://localhost:8000/api/v1/alerts",
    json=alert
)
```

---

## 🛠️ Development

### Project Structure
```
hubsec-platform/
├── backend/
│   └── app/
│       ├── main.py                     # Single-tenant FastAPI application
│       ├── main_multitenant.py         # Multi-tenant FastAPI application ✨
│       ├── database.py                 # Single-tenant database config
│       ├── database_multitenant.py     # Multi-tenant PostgreSQL config ✨
│       ├── models/
│       │   ├── models.py               # Single-tenant SQLAlchemy models
│       │   └── models_multitenant.py   # Multi-tenant models (15 tables) ✨
│       ├── schemas/
│       │   ├── schemas.py              # Single-tenant Pydantic schemas
│       │   └── schemas_multitenant.py  # Multi-tenant schemas (UUID) ✨
│       ├── middleware/
│       │   └── tenant.py               # Tenant-aware RBAC middleware ✨
│       ├── api/
│       │   └── v1/
│       │       ├── tenants.py          # Tenant management API ✨
│       │       ├── source_systems.py   # Integration management API ✨
│       │       ├── assets.py           # Asset inventory API ✨
│       │       ├── playbooks.py        # Playbook automation API ✨
│       │       ├── incidents.py        # Incident management (legacy)
│       │       ├── cases.py            # Case management (legacy)
│       │       ├── alerts.py           # Alert management (legacy)
│       │       └── users.py            # User management (legacy)
│       └── services/
│           ├── wazuh_normalizer.py
│           └── case_engine.py
├── config/
│   ├── wazuh_mapping.yml
│   └── severity_rules.yml
├── scripts/
│   ├── init_db.py                      # Single-tenant DB initialization
│   └── init_db_multitenant.py          # Multi-tenant DB initialization ✨
├── docs/
│   ├── ENHANCED_DATABASE_SCHEMA.md
│   ├── MULTITENANT_MIGRATION_GUIDE.md
│   ├── IMPLEMENTATION_STATUS.md
│   └── API_TESTING_GUIDE.md            # Complete API testing guide ✨
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

**✨ = New multi-tenant files**

### Running Tests
```bash
# Install dev dependencies
pip install -r requirements.txt

# Run tests
pytest

# With coverage
pytest --cov=backend --cov-report=html
```

### Code Quality
```bash
# Format code
black backend/

# Lint
flake8 backend/

# Type checking
mypy backend/
```

---

## 🚀 Deployment

### Production Checklist

- [ ] Change default passwords
- [ ] Set strong `SECRET_KEY` in environment
- [ ] Use PostgreSQL (not SQLite)
- [ ] Configure CORS for specific origins
- [ ] Enable HTTPS/TLS
- [ ] Set up log aggregation
- [ ] Configure backup strategy
- [ ] Set up monitoring/alerting
- [ ] Review security headers
- [ ] Implement rate limiting

### Production Deployment

```bash
# 1. Set environment variables
export DATABASE_URL=postgresql://user:pass@db:5432/hubsec
export SECRET_KEY=$(openssl rand -hex 32)

# 2. Start with production settings
docker-compose -f docker-compose.prod.yml up -d

# 3. Run migrations
docker-compose exec api alembic upgrade head

# 4. Create admin user
docker-compose exec api python scripts/create_admin.py
```

---

## 📊 Monitoring & Metrics

### Health Checks
```bash
curl http://localhost:8000/health
```

### Dashboard Statistics
```bash
curl http://localhost:8000/api/v1/stats
```

### Prometheus Metrics (Optional)
Enable Prometheus metrics endpoint for monitoring.

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run code quality checks
6. Submit a pull request

---

## 📝 License

This project is licensed under the MIT License.

---

## 🆘 Support

For questions and support:
- Open an issue on GitHub
- Check the documentation at `/api/docs`
- Review the Quick Start guide

---

## 🙏 Acknowledgments

Built with:
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - Python SQL toolkit
- **Pydantic** - Data validation
- **Wazuh** - Security monitoring platform

---

**Made with ❤️ for SOC teams everywhere**
