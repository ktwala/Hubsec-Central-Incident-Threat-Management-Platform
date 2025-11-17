# 🛡️ Hubsec SOC Platform

**Central Incident & Threat Management Platform for Security Operations Centers**

A comprehensive, production-ready Security Operations Center (SOC) platform built with FastAPI, designed to centralize incident management, alert correlation, and threat response.

---

## 🌟 Features

### Core Capabilities
- **🚨 Alert Management** - Ingest, normalize, and triage security alerts from multiple sources
- **📋 Incident Tracking** - Create and manage security incidents with full lifecycle support
- **💼 Case Management** - Investigation cases with automatic alert correlation
- **👥 User Management** - Role-based access control (Admin, Analyst, Manager, Viewer)
- **🔄 Wazuh Integration** - Native webhook support for Wazuh SIEM alerts
- **📊 Dashboard & Analytics** - Real-time SOC metrics and statistics
- **💬 Collaboration** - Comments and activity logs for team coordination

### Intelligence Features
- **Automatic Alert Correlation** - Groups related alerts into cases
- **Smart Case Creation** - Automatically creates cases from high-severity alerts
- **Severity Mapping** - Configurable rules for alert prioritization
- **Alert Normalization** - Standardizes alerts from different sources
- **MITRE ATT&CK Integration** - Tracks techniques and tactics

### Technical Highlights
- **RESTful API** - Clean, well-documented API endpoints
- **Database Agnostic** - Supports PostgreSQL, MySQL, SQLite
- **Docker Support** - Easy deployment with Docker Compose
- **Comprehensive Schemas** - Full request/response validation
- **Extensible Architecture** - Easy to add new alert sources

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
- Docker & Docker Compose (optional)
- PostgreSQL (optional, can use SQLite)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd Hubsec-Central-Incident-Threat-Management-Platform

# Install dependencies
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
# Create tables and seed with sample data
python scripts/init_db.py --seed
```

### 3. Start the API

```bash
# Development mode
uvicorn backend.app.main:app --reload

# Or with Docker
docker-compose up
```

### 4. Access the Platform

- **API Documentation**: http://localhost:8000/api/docs
- **Alternative Docs**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/health
- **Dashboard Stats**: http://localhost:8000/api/v1/stats

### Default Credentials
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
│  │  REST API Endpoints                              │  │
│  │  • /api/v1/incidents                             │  │
│  │  • /api/v1/cases                                 │  │
│  │  • /api/v1/alerts                                │  │
│  │  • /api/v1/users                                 │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│              Database (PostgreSQL/SQLite)                │
│  • Incidents  • Cases  • Alerts  • Users                │
│  • Comments   • Activities                              │
└─────────────────────────────────────────────────────────┘
```

### Database Schema

**Core Entities:**
- **Incident** - High-level security incident
- **Case** - Investigation case (belongs to incident)
- **Alert** - Individual security alert (can belong to multiple cases)
- **User** - SOC analyst or administrator
- **Comment** - Discussion on incidents/cases
- **Activity** - Audit trail for case activities

**Relationships:**
- 1 Incident → Many Cases
- 1 Case → Many Alerts (many-to-many)
- 1 User → Many Incidents (assigned)
- 1 Case → Many Users (assigned, many-to-many)

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

### Main Endpoints

#### Incidents
```http
GET    /incidents          # List all incidents
GET    /incidents/{id}     # Get incident details
POST   /incidents          # Create incident
PUT    /incidents/{id}     # Update incident
DELETE /incidents/{id}     # Delete incident
POST   /incidents/{id}/comments  # Add comment
GET    /incidents/{id}/timeline  # Get timeline
```

#### Cases
```http
GET    /cases              # List all cases
GET    /cases/{id}         # Get case details
POST   /cases              # Create case
PUT    /cases/{id}         # Update case
POST   /cases/{id}/alerts  # Add alerts to case
GET    /cases/{id}/statistics  # Get case stats
POST   /cases/{id}/escalate    # Escalate case
```

#### Alerts
```http
GET    /alerts             # List all alerts
GET    /alerts/{id}        # Get alert details
POST   /alerts             # Create alert
POST   /alerts/wazuh/webhook   # Wazuh webhook
POST   /alerts/bulk-triage      # Bulk update
GET    /alerts/search/ip/{ip}  # Search by IP
```

#### Users
```http
GET    /users              # List all users
GET    /users/{id}         # Get user details
POST   /users              # Create user
PUT    /users/{id}         # Update user
GET    /users/{id}/workload    # Get workload
GET    /users/{id}/activity    # Get activity
```

### Interactive Documentation
Visit http://localhost:8000/api/docs for the full interactive API documentation with request/response examples.

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
│       ├── main.py              # FastAPI application
│       ├── models/
│       │   └── models.py        # Database models
│       ├── schemas/
│       │   └── schemas.py       # Pydantic schemas
│       ├── api/
│       │   └── v1/
│       │       ├── incidents.py
│       │       ├── cases.py
│       │       ├── alerts.py
│       │       └── users.py
│       └── services/
│           ├── wazuh_normalizer.py
│           └── case_engine.py
├── config/
│   ├── wazuh_mapping.yml
│   └── severity_rules.yml
├── scripts/
│   └── init_db.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

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
