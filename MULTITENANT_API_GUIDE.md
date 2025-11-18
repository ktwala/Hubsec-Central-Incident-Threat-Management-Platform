# Multi-Tenant API Guide

## Quick Start

The Hubsec SOC Platform now has a **multi-tenant version** that supports multiple client organizations with PostgreSQL-specific optimizations.

### Prerequisites

- PostgreSQL 12+ installed and running
- Python 3.8+ with requirements installed
- Database initialized with `scripts/init_db_multitenant.py`

### Start the Multi-Tenant API

```bash
# Set PostgreSQL database URL
export DATABASE_URL="postgresql://hubsec:hubsec@localhost/hubsec_multitenant"

# Run the multi-tenant API
uvicorn backend.app.main_multitenant:app --reload
```

The API will be available at:
- **API Docs**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/health
- **Database Info**: http://localhost:8000/api/v1/info/database

---

## API Versions

| Version | File | Database | Use Case |
|---------|------|----------|----------|
| **Single-Tenant** | `main.py` | SQLite/PostgreSQL | Development, testing, single organization |
| **Multi-Tenant** | `main_multitenant.py` | PostgreSQL only | Production, multiple organizations |

---

## Authentication (Header-Based for Testing)

The multi-tenant API uses header-based authentication for testing. JWT authentication will be added in future releases.

### Request Headers

| Header | Type | Description | Example |
|--------|------|-------------|---------|
| `X-Tenant-ID` | UUID | Tenant identifier | `550e8400-e29b-41d4-a716-446655440000` |
| `X-Tenant-Code` | String | Tenant code (alternative) | `ECONET` |
| `X-User-ID` | UUID | User identifier | `6ba7b810-9dad-11d1-80b4-00c04fd430c8` |
| `X-Username` | String | Username (alternative) | `hubsec_analyst1` |

### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/tenants" \
  -H "X-User-ID: <user-uuid>" \
  -H "X-Tenant-Code: ECONET"
```

---

## API Endpoints

### Tenants

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/api/v1/tenants` | List all accessible tenants | Hubsec staff (all), Users (their tenants) |
| GET | `/api/v1/tenants/{id}` | Get tenant by ID | Hubsec staff or assigned users |
| GET | `/api/v1/tenants/{id}/stats` | Get tenant statistics | Hubsec staff or assigned users |
| POST | `/api/v1/tenants` | Create new tenant | Super admin only |
| PATCH | `/api/v1/tenants/{id}` | Update tenant | Super admin only |
| DELETE | `/api/v1/tenants/{id}` | Soft delete tenant | Super admin only |

### Source Systems (Coming Soon)

Integration management endpoints for Wazuh, IRIS, Jira, etc.

### Assets (Coming Soon)

IT asset inventory endpoints.

### Playbooks (Coming Soon)

Incident response playbook endpoints.

### Alerts, Incidents, Cases (Coming Soon)

Existing endpoints will be updated to support tenant filtering.

---

## Sample Tenants

After running `scripts/init_db_multitenant.py --seed`, you'll have:

| Name | Code | Industry | Tier |
|------|------|----------|------|
| Econet Wireless Zimbabwe | ECONET | Telecommunications | Enterprise |
| PostBank Zimbabwe | POSTBANK | Banking | Professional |
| TelOne Zimbabwe | TELONE | Telecommunications | Enterprise |

---

## Sample Users

### Hubsec Staff (Access All Tenants)

| Username | Role | Password | UUID |
|----------|------|----------|------|
| superadmin | SUPER_ADMIN | admin123 | Run init script to get UUID |
| hubsec_analyst1 | HUBSEC_ANALYST | analyst123 | Run init script to get UUID |
| hubsec_analyst2 | HUBSEC_ANALYST | analyst123 | Run init script to get UUID |

### Tenant Users (Single Tenant Access)

| Username | Tenant | Role | Password |
|----------|--------|------|----------|
| econet_admin | ECONET | TENANT_ADMIN | econet123 |
| econet_analyst | ECONET | ANALYST | econet123 |
| postbank_admin | POSTBANK | TENANT_ADMIN | postbank123 |
| telone_viewer | TELONE | VIEWER | telone123 |

---

## Testing Examples

### 1. List All Tenants (as Hubsec Staff)

```bash
# Get user ID first
psql -U hubsec -d hubsec_multitenant \
  -c "SELECT id, username FROM users WHERE username='hubsec_analyst1';"

# List tenants
curl -X GET "http://localhost:8000/api/v1/tenants" \
  -H "X-User-ID: <user-uuid>"
```

### 2. Get Tenant Statistics

```bash
# Get tenant ID
psql -U hubsec -d hubsec_multitenant \
  -c "SELECT id, code FROM tenants WHERE code='ECONET';"

# Get stats
curl -X GET "http://localhost:8000/api/v1/tenants/<tenant-uuid>/stats" \
  -H "X-User-ID: <user-uuid>" \
  -H "X-Tenant-Code: ECONET"
```

### 3. Create a New Tenant (as Super Admin)

```bash
curl -X POST "http://localhost:8000/api/v1/tenants" \
  -H "X-User-ID: <superadmin-uuid>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "NetOne Cellular",
    "code": "NETONE",
    "industry": "Telecommunications",
    "region": "Zimbabwe",
    "subscription_tier": "professional",
    "is_active": true
  }'
```

### 4. Access Denied Example

```bash
# Try to access ECONET tenant as PostBank user
curl -X GET "http://localhost:8000/api/v1/tenants/<econet-tenant-id>" \
  -H "X-Username: postbank_admin"

# Response: 403 Forbidden
# "User 'postbank_admin' does not have access to tenant 'ECONET'"
```

---

## Role-Based Access Control

### Role Hierarchy

```
SUPER_ADMIN (Hubsec)
    ↓
HUBSEC_ANALYST (Hubsec SOC)
    ↓
TENANT_ADMIN (Client Admin)
    ↓
ANALYST (Client Analyst)
    ↓
VIEWER (Read-Only)
```

### Access Matrix

| Action | Super Admin | Hubsec Analyst | Tenant Admin | Analyst | Viewer |
|--------|-------------|----------------|--------------|---------|--------|
| Create Tenant | ✅ | ❌ | ❌ | ❌ | ❌ |
| View All Tenants | ✅ | ✅ | ❌ | ❌ | ❌ |
| View Own Tenant | ✅ | ✅ | ✅ | ✅ | ✅ |
| Manage Incidents | ✅ | ✅ | ✅ | ✅ | ❌ |
| View Alerts | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## Database Schema

The multi-tenant schema uses **UUID primary keys** and **PostgreSQL-specific types**:

- **UUID**: Primary keys for all tables
- **INET**: IP addresses (IPv4/IPv6 native)
- **JSONB**: Metadata and configuration (indexable)
- **TEXT[]**: Arrays for tags
- **TIMESTAMPTZ**: Timezone-aware timestamps

### Key Tables

```
tenants
  ↓
├── source_systems (Wazuh, IRIS, Jira)
├── assets (Servers, workstations, etc.)
├── alerts (Security alerts)
├── incidents (Security incidents)
├── cases (Investigations)
└── playbooks (Automation)
```

All security entities (alerts, incidents, cases) have a `tenant_id` foreign key for data isolation.

---

## Middleware

The tenant middleware provides:

1. **Tenant Extraction**: Reads `X-Tenant-ID` or `X-Tenant-Code` header
2. **User Authentication**: Reads `X-User-ID` or `X-Username` header (mock for testing)
3. **Access Validation**: Ensures user can access the requested tenant
4. **Context Injection**: Makes tenant and user available in endpoints

### Usage in Endpoints

```python
from backend.app.middleware.tenant import require_tenant, get_tenant_context, TenantContext

# Require tenant header
@router.get("/alerts")
def list_alerts(
    tenant: Tenant = Depends(require_tenant),
    db: Session = Depends(get_db)
):
    alerts = db.query(Alert).filter(Alert.tenant_id == tenant.id).all()
    return alerts

# Get full context (optional tenant/user)
@router.get("/stats")
def get_stats(
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    # context.tenant - Current tenant or None
    # context.user - Current user or None
    # context.can_access_tenant(uuid) - Check access
    # context.is_super_admin() - Check role
    pass
```

---

## Troubleshooting

### Error: "Multi-tenant mode requires PostgreSQL!"

**Solution**: Set `DATABASE_URL` to PostgreSQL connection string:
```bash
export DATABASE_URL="postgresql://user:password@localhost/database"
```

### Error: "UUID extension not enabled"

**Solution**: The API automatically enables it on startup. If it fails, enable manually:
```bash
psql -U postgres -d hubsec_multitenant -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
```

### Error: "Database connection failed"

**Solution**: Check PostgreSQL is running and credentials are correct:
```bash
sudo systemctl status postgresql
psql -U hubsec -d hubsec_multitenant -c "SELECT 1;"
```

### No Data in Database

**Solution**: Run the initialization script:
```bash
python scripts/init_db_multitenant.py --database-url "$DATABASE_URL" --drop --seed
```

---

## Next Steps

### For Testing

1. Initialize database with sample data
2. Get user UUID from database
3. Test endpoints using curl or Swagger UI
4. Explore tenant filtering and access control

### For Development

1. Create additional endpoints (SourceSystems, Assets, Playbooks)
2. Update existing endpoints (Alerts, Incidents, Cases) for tenant filtering
3. Implement JWT authentication (replace mock auth)
4. Add WebSocket support for real-time alerts
5. Implement Row-Level Security in PostgreSQL

### For Production

1. Enable JWT authentication
2. Configure PostgreSQL connection pooling
3. Set up tenant-specific rate limiting
4. Implement audit logging
5. Add tenant data backup/restore

---

## Files Reference

| File | Purpose |
|------|---------|
| `backend/app/main_multitenant.py` | Multi-tenant FastAPI application |
| `backend/app/database_multitenant.py` | PostgreSQL database configuration |
| `backend/app/models/models_multitenant.py` | Multi-tenant SQLAlchemy models |
| `backend/app/schemas/schemas_multitenant.py` | Pydantic schemas with UUID support |
| `backend/app/middleware/tenant.py` | Tenant-aware middleware |
| `backend/app/api/v1/tenants.py` | Tenants API endpoints |
| `scripts/init_db_multitenant.py` | Database initialization |
| `MULTITENANT_MIGRATION_GUIDE.md` | Setup and migration guide |

---

## Support

For issues or questions:

1. Check the **API documentation**: http://localhost:8000/api/docs
2. Review **MULTITENANT_MIGRATION_GUIDE.md**
3. Examine database with `psql -U hubsec -d hubsec_multitenant`

---

## Summary

The multi-tenant API is now **partially integrated** with:

✅ **Complete**:
- PostgreSQL database with UUID models
- Tenant management endpoints
- Tenant-aware middleware
- Role-based access control
- Pydantic schemas for all models
- Sample data with 3 tenants, 7 users

🚧 **In Progress**:
- Source Systems, Assets, Playbooks endpoints (models ready, endpoints pending)
- Updated Alerts, Incidents, Cases endpoints with tenant filtering
- JWT authentication (currently using header-based mock)

The foundation is ready for full multi-tenant SOC operations!
