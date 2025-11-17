# ⚡ Quick Start Guide - Hubsec SOC Platform

Get the Hubsec SOC Platform up and running in 5 minutes!

---

## 🎯 Goal

By the end of this guide, you'll have:
- ✅ A running Hubsec API server
- ✅ Sample data loaded (users, incidents, cases, alerts)
- ✅ Access to the interactive API documentation
- ✅ Understanding of basic operations

---

## 📋 Prerequisites

Choose ONE of these options:

### Option A: Local Python (Recommended for Development)
- Python 3.11 or higher
- pip (Python package manager)

### Option B: Docker (Recommended for Production)
- Docker Desktop or Docker Engine
- Docker Compose

---

## 🚀 Option A: Local Setup (5 minutes)

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd Hubsec-Central-Incident-Threat-Management-Platform
```

### Step 2: Install Dependencies
```bash
# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### Step 3: Initialize Database
```bash
# Create database and add sample data
python scripts/init_db.py --seed
```

**Expected output:**
```
============================================================
Hubsec SOC Platform - Database Initialization
============================================================

📊 Database: sqlite:///./hubsec.db

Creating database tables...
✅ Tables created successfully

🌱 Seeding database with sample data...

📝 Seeding users...
✅ Created 5 users

🚨 Seeding alerts...
✅ Created 30 alerts

📋 Seeding incidents...
✅ Created 4 incidents

💼 Seeding cases...
✅ Created 3 cases

💬 Seeding comments...
✅ Created 4 comments

============================================================
✅ Database initialization complete!
============================================================

📊 Summary:
  • Users: 5
  • Alerts: 30
  • Incidents: 4
  • Cases: 3

🔐 Default Login Credentials:
  • Admin:    admin / admin123
  • Analyst:  analyst1 / analyst123
  • Manager:  manager / manager123

🚀 Start the API with:
  uvicorn backend.app.main:app --reload

📝 API Documentation:
  http://localhost:8000/api/docs
============================================================
```

### Step 4: Start the API Server
```bash
uvicorn backend.app.main:app --reload
```

**Expected output:**
```
==================================================
🚀 Hubsec SOC Platform Starting...
==================================================
📊 Database: sqlite:///./hubsec.db
📝 API Docs: http://localhost:8000/api/docs
🏥 Health Check: http://localhost:8000/health
==================================================
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### Step 5: Verify Installation
Open your browser and visit:
- **API Docs**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/health

You should see the Swagger UI with all available endpoints!

---

## 🐳 Option B: Docker Setup (5 minutes)

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd Hubsec-Central-Incident-Threat-Management-Platform
```

### Step 2: Start Services
```bash
# Start PostgreSQL and API
docker-compose up -d
```

### Step 3: Initialize Database
```bash
# Wait a few seconds for services to start, then:
docker-compose exec api python scripts/init_db.py --seed
```

### Step 4: Verify Installation
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f api
```

Open your browser:
- **API Docs**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/health

---

## 🎮 Your First API Calls

### 1. Check System Health
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0"
}
```

### 2. Get Dashboard Statistics
```bash
curl http://localhost:8000/api/v1/stats
```

**Response:**
```json
{
  "total_incidents": 4,
  "open_incidents": 3,
  "total_cases": 3,
  "open_cases": 2,
  "total_alerts": 30,
  "new_alerts": 10,
  "alerts_by_severity": {
    "critical": 5,
    "high": 8,
    "medium": 12,
    "low": 3,
    "info": 2
  },
  ...
}
```

### 3. List All Incidents
```bash
curl http://localhost:8000/api/v1/incidents
```

### 4. Get a Specific Incident
```bash
curl http://localhost:8000/api/v1/incidents/1
```

### 5. Create a New Incident
```bash
curl -X POST http://localhost:8000/api/v1/incidents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Suspicious Network Activity",
    "description": "Multiple connection attempts from unknown IP",
    "severity": "high",
    "category": "network",
    "source": "Manual"
  }'
```

---

## 📚 Explore the API

### Interactive Documentation
Visit http://localhost:8000/api/docs

**What you can do:**
- 📖 See all available endpoints
- 🧪 Test API calls directly in the browser
- 📝 View request/response schemas
- 🔍 Explore data models

### Main Endpoints to Try:

#### Incidents
- `GET /api/v1/incidents` - List all incidents
- `GET /api/v1/incidents/{id}` - Get specific incident
- `POST /api/v1/incidents` - Create new incident

#### Cases
- `GET /api/v1/cases` - List all cases
- `GET /api/v1/cases/{id}/statistics` - Get case metrics
- `POST /api/v1/cases/{id}/alerts` - Add alerts to case

#### Alerts
- `GET /api/v1/alerts?severity=critical` - Filter alerts
- `GET /api/v1/alerts/search/ip/192.168.1.100` - Search by IP
- `POST /api/v1/alerts/bulk-triage` - Bulk triage alerts

#### Users
- `GET /api/v1/users` - List all users
- `GET /api/v1/users/1/workload` - Get user workload
- `GET /api/v1/users/1/activity` - Get user activity

---

## 🔑 Default User Accounts

| Username | Password | Role | Description |
|----------|----------|------|-------------|
| admin | admin123 | Admin | Full system access |
| analyst1 | analyst123 | Analyst | SOC analyst |
| analyst2 | analyst123 | Analyst | SOC analyst |
| manager | manager123 | SOC Manager | Team manager |
| viewer | viewer123 | Viewer | Read-only access |

**⚠️ Important:** Change these passwords in production!

---

## 🎯 Common Use Cases

### Use Case 1: Triage New Alerts

1. **List new alerts:**
```bash
curl "http://localhost:8000/api/v1/alerts?status=new&limit=10"
```

2. **Mark alerts as triaged:**
```bash
curl -X POST http://localhost:8000/api/v1/alerts/bulk-triage \
  -H "Content-Type: application/json" \
  -d '{"alert_ids": [1, 2, 3], "new_status": "triaged"}'
```

### Use Case 2: Investigate an Incident

1. **Get incident details:**
```bash
curl http://localhost:8000/api/v1/incidents/1
```

2. **View incident timeline:**
```bash
curl http://localhost:8000/api/v1/incidents/1/timeline
```

3. **Add a comment:**
```bash
curl -X POST http://localhost:8000/api/v1/incidents/1/comments \
  -H "Content-Type: application/json" \
  -d '{"content": "Initial investigation shows this is a false positive"}'
```

### Use Case 3: Manage Cases

1. **List open cases:**
```bash
curl "http://localhost:8000/api/v1/cases?status=open"
```

2. **Get case statistics:**
```bash
curl http://localhost:8000/api/v1/cases/1/statistics
```

3. **Add alerts to case:**
```bash
curl -X POST http://localhost:8000/api/v1/cases/1/alerts \
  -H "Content-Type: application/json" \
  -d '{"alert_ids": [5, 6, 7]}'
```

---

## 🔄 Integrating with Wazuh

### Step 1: Configure Wazuh
Edit `/var/ossec/etc/ossec.conf` on your Wazuh manager:

```xml
<integration>
  <name>custom-webhook</name>
  <hook_url>http://your-server:8000/api/v1/alerts/wazuh/webhook</hook_url>
  <level>7</level>
  <alert_format>json</alert_format>
</integration>
```

### Step 2: Restart Wazuh
```bash
systemctl restart wazuh-manager
```

### Step 3: Verify
Watch for alerts in Hubsec:
```bash
# Local setup
tail -f hubsec.db.log

# Docker setup
docker-compose logs -f api
```

---

## 🛠️ Troubleshooting

### Problem: "Module not found" errors
**Solution:**
```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Problem: Database connection errors
**Solution:**
```bash
# Reinitialize database
python scripts/init_db.py --drop --seed
```

### Problem: Port 8000 already in use
**Solution:**
```bash
# Use a different port
uvicorn backend.app.main:app --reload --port 8001
```

### Problem: Docker services won't start
**Solution:**
```bash
# Stop all services
docker-compose down

# Remove volumes
docker-compose down -v

# Start fresh
docker-compose up -d
```

---

## 📖 Next Steps

Now that you have Hubsec running:

1. **Explore the API** - Try different endpoints in the interactive docs
2. **Read the README** - Learn about architecture and features
3. **Configure Integrations** - Connect Wazuh or other alert sources
4. **Customize** - Modify severity rules and field mappings
5. **Deploy to Production** - Follow the deployment guide in README.md

---

## 🆘 Getting Help

- **API Documentation**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/health
- **GitHub Issues**: Report bugs and request features
- **README**: Full documentation

---

**You're all set! Happy SOC-ing! 🛡️**
