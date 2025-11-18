# 🏢 Hubsec Central SOC Platform - Enhanced Multi-Tenant Schema

## Overview

This is the **production-ready multi-tenant schema** for Hubsec's central incident and threat management platform, supporting:

- ✅ **Multiple clients/tenants** (Net, Bank, TelOne, etc.)
- ✅ **Multiple integrations** (Wazuh, IRIS, Jira, firewalls, EDR)
- ✅ **Playbooks & automation**
- ✅ **Asset tracking & context**
- ✅ **External system synchronization**

---

## 📊 Entity Relationship Diagram

```
╔════════════════════════════════════════════════════════════════════════════╗
║        EXTENDED ER – CENTRAL INCIDENT & THREAT MANAGEMENT PLATFORM        ║
╚════════════════════════════════════════════════════════════════════════════╝


┌────────────────────────┐
│        TENANTS         │
├────────────────────────┤
│ PK  id                 │  UUID
│     name               │  TEXT
│     code               │  TEXT (e.g. "NET", "BANK")
│     industry           │  TEXT
│     region             │  TEXT
│     is_active          │  BOOLEAN
│     created_at         │  TIMESTAMPTZ
└────────────────────────┘
         │
         │ 1:N
         ▼
┌────────────────────────┐
│     SOURCE_SYSTEMS     │   (Connectors / Integrations)
├────────────────────────┤
│ PK  id                 │  UUID
│ FK  tenant_id          │  FK → tenants.id
│     name               │  TEXT  -- "Econet Wazuh", "Postbank IRIS"
│     type               │  TEXT  -- "wazuh", "iris", "jira", "fortigate", …
│     base_url           │  TEXT
│     auth_type          │  TEXT  -- "api_key", "oauth2", etc.
│     auth_config        │  JSONB -- encrypted credentials/config
│     is_active          │  BOOLEAN
│     created_at         │  TIMESTAMPTZ
└────────────────────────┘


┌────────────────────────┐
│         USERS          │
├────────────────────────┤
│ PK  id                 │  UUID
│     username           │  TEXT
│     email              │  TEXT (UNIQUE)
│     password_hash      │  TEXT
│     role               │  TEXT  -- global: super_admin, hubsec_analyst…
│     is_active          │  BOOLEAN
│     last_login         │  TIMESTAMPTZ
│     created_at         │  TIMESTAMPTZ
└────────────────────────┘
         │      │
         │      │ M:N (via user_tenants)
         │      ▼
         │ ┌────────────────────────┐
         │ │      USER_TENANTS      │   (Multi-tenant RBAC)
         │ ├────────────────────────┤
         │ │ PK  user_id            │  FK → users.id
         │ │ PK  tenant_id          │  FK → tenants.id
         │ │     tenant_role        │  TEXT  -- tenant_admin, tenant_analyst
         │ │     created_at         │  TIMESTAMPTZ
         │ └────────────────────────┘
         │
         │ 1:N (author)
         ▼
┌────────────────────────┐
│        COMMENTS        │   (Discussion on incidents/cases)
├────────────────────────┤
│ PK  id                 │  UUID
│     content            │  TEXT
│ FK  incident_id        │  FK → incidents.id (nullable)
│ FK  case_id            │  FK → cases.id (nullable)
│ FK  author_id          │  FK → users.id
│     created_at         │  TIMESTAMPTZ
│     updated_at         │  TIMESTAMPTZ
└────────────────────────┘


┌────────────────────────┐
│         ASSETS         │   (Hosts / endpoints / devices)
├────────────────────────┤
│ PK  id                 │  UUID
│ FK  tenant_id          │  FK → tenants.id
│     hostname           │  TEXT
│     ip_address         │  INET
│     asset_type         │  TEXT  -- "server", "workstation", "network_device"
│     criticality        │  TEXT  -- "low", "medium", "high", "critical"
│ FK  owner_user_id      │  FK → users.id (optional)
│     metadata           │  JSONB -- OS, environment, tags
│     created_at         │  TIMESTAMPTZ
└────────────────────────┘
         │
         │ 1:N
         ▼
┌────────────────────────┐
│         ALERTS         │   (Normalized alerts from SIEM/EDR/etc.)
├────────────────────────┤
│ PK  id                 │  UUID
│ FK  tenant_id          │  FK → tenants.id
│ FK  source_system_id   │  FK → source_systems.id
│     source_alert_id    │  TEXT  -- ID in Wazuh / EDR / FW, etc.
│     category           │  TEXT  -- "bruteforce", "malware", "phishing", …
│     event_type         │  TEXT
│     severity           │  INT
│     status             │  TEXT  -- "new", "triaged", "suppressed"
│     title              │  TEXT
│     description        │  TEXT
│     src_ip             │  INET
│     dst_ip             │  INET
│     src_port           │  INT
│     dst_port           │  INT
│     protocol           │  TEXT
│     username           │  TEXT
│     hostname           │  TEXT
│ FK  asset_id           │  FK → assets.id  (optional)
│     rule_id            │  TEXT  -- from source
│     rule_description   │  TEXT
│     raw_data           │  JSONB -- original log/alert from source
│     normalized_data    │  JSONB -- parsed fields / enrichment
│     timestamp          │  TIMESTAMPTZ  -- event time from source
│     created_at         │  TIMESTAMPTZ  -- ingestion time
└────────────────────────┘


┌────────────────────────┐
│       INCIDENTS        │   (High-level incidents / tickets)
├────────────────────────┤
│ PK  id                 │  UUID
│ FK  tenant_id          │  FK → tenants.id
│     title              │  TEXT
│     description        │  TEXT
│     severity           │  INT   -- 1–10 or 1–100
│     status             │  TEXT  -- "open", "in_progress", "resolved"
│     category           │  TEXT  -- "bruteforce", "malware", "phishing"
│     subcategory        │  TEXT
│     source             │  TEXT  -- human label e.g. "SIEM", "EDR"
│ FK  source_system_id   │  FK → source_systems.id  (optional)
│     source_id          │  TEXT  -- ID in external system
│     detected_at        │  TIMESTAMPTZ
│     resolved_at        │  TIMESTAMPTZ
│     meta_data          │  JSONB
│     tags               │  TEXT[]
│ FK  owner_user_id      │  FK → users.id
│     created_at         │  TIMESTAMPTZ
│     updated_at         │  TIMESTAMPTZ
└────────────────────────┘
         │
         │ 1:N
         ▼
┌────────────────────────┐
│         CASES          │   (Technical investigations)
├────────────────────────┤
│ PK  id                 │  UUID
│ FK  tenant_id          │  FK → tenants.id
│ FK  incident_id        │  FK → incidents.id
│     title              │  TEXT
│     description        │  TEXT
│     incident_type      │  TEXT  -- for playbook matching
│     priority           │  TEXT  -- "low", "medium", "high", "critical"
│     severity           │  INT
│     status             │  TEXT  -- "open", "in_triage", "contained"
│     phase              │  TEXT  -- NIST: "detection", "containment"…
│ FK  assignee_user_id   │  FK → users.id
│     opened_at          │  TIMESTAMPTZ
│     closed_at          │  TIMESTAMPTZ
│     resolution_summary │  TEXT
│     tags               │  TEXT[]
│     external_refs      │  JSONB -- {"iris": "...", "jira": "..."}
│     metadata           │  JSONB
│     created_at         │  TIMESTAMPTZ
│     updated_at         │  TIMESTAMPTZ
└────────────────────────┘
         │      │      │
         │      │      │ 1:N
         │      │      ▼
         │      │ ┌────────────────────────┐
         │      │ │       ACTIVITIES       │   (Audit trail)
         │      │ ├────────────────────────┤
         │      │ │ PK  id                 │  UUID
         │      │ │     action             │  TEXT
         │      │ │     description        │  TEXT
         │      │ │ FK  case_id            │  FK → cases.id
         │      │ │ FK  user_id            │  FK → users.id
         │      │ │     meta_data          │  JSONB
         │      │ │     created_at         │  TIMESTAMPTZ
         │      │ └────────────────────────┘
         │      │
         │      │ M:N (via case_alerts)
         │      ▼
         │ ┌────────────────────────┐
         │ │      CASE_ALERTS       │
         │ ├────────────────────────┤
         │ │ PK  case_id            │  FK → cases.id
         │ │ PK  alert_id           │  FK → alerts.id
         │ │     created_at         │  TIMESTAMPTZ
         │ └────────────────────────┘
         │
         │ M:N (via case_assignments)
         ▼
    ┌────────────────────────┐
    │    CASE_ASSIGNMENTS    │
    ├────────────────────────┤
    │ PK  case_id            │  FK → cases.id
    │ PK  user_id            │  FK → users.id
    │     role               │  TEXT  -- "lead_analyst", "support"
    │     assigned_at        │  TIMESTAMPTZ
    └────────────────────────┘


┌────────────────────────┐
│       PLAYBOOKS        │   (Standard response runbooks)
├────────────────────────┤
│ PK  id                 │  UUID
│ FK  tenant_id          │  FK → tenants.id (nullable for global)
│     name               │  TEXT
│     description        │  TEXT
│     incident_type      │  TEXT  -- "bruteforce", "malware", …
│     is_active          │  BOOLEAN
│     definition         │  JSONB -- steps array, actions
│     created_at         │  TIMESTAMPTZ
└────────────────────────┘
         │
         │ M:N (via case_playbooks)
         ▼
    ┌────────────────────────┐
    │     CASE_PLAYBOOKS     │
    ├────────────────────────┤
    │ PK  case_id            │  FK → cases.id
    │ PK  playbook_id        │  FK → playbooks.id
    │     status             │  TEXT  -- "not_started", "in_progress"
    │     started_at         │  TIMESTAMPTZ
    │     completed_at       │  TIMESTAMPTZ
    │     metadata           │  JSONB
    └────────────────────────┘


┌────────────────────────┐
│   CASE_EXTERNAL_REFS   │   (Links to IRIS, Jira, etc.)
├────────────────────────┤
│ PK  id                 │  UUID
│ FK  case_id            │  FK → cases.id
│     system_type        │  TEXT  -- "iris", "jira", "servicenow"
│     external_id        │  TEXT  -- "IRIS-0001", "SOC-123"
│     url                │  TEXT
│     created_at         │  TIMESTAMPTZ
└────────────────────────┘
```

---

## 📋 Table Definitions

### Core Multi-Tenant Tables

#### 1. **TENANTS** - Organizations/Clients
```sql
CREATE TABLE tenants (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL UNIQUE,
    code                TEXT NOT NULL UNIQUE,  -- "NET", "BANK"
    industry            TEXT,
    region              TEXT,
    is_active           BOOLEAN DEFAULT true,
    subscription_tier   TEXT,  -- "basic", "professional", "enterprise"
    contact_name        TEXT,
    contact_email       TEXT,
    settings            JSONB,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tenants_code ON tenants(code);
CREATE INDEX idx_tenants_active ON tenants(is_active);
```

#### 2. **USERS** - Platform Users
```sql
CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username            TEXT NOT NULL UNIQUE,
    email               TEXT NOT NULL UNIQUE,
    password_hash       TEXT NOT NULL,
    role                TEXT NOT NULL,  -- super_admin, hubsec_analyst, analyst, viewer
    is_active           BOOLEAN DEFAULT true,
    last_login          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);
```

#### 3. **USER_TENANTS** - Multi-Tenant RBAC
```sql
CREATE TABLE user_tenants (
    user_id             UUID NOT NULL REFERENCES users(id),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    tenant_role         TEXT NOT NULL,  -- tenant_admin, tenant_analyst, tenant_viewer
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, tenant_id)
);

CREATE INDEX idx_user_tenants_tenant ON user_tenants(tenant_id);
```

---

### Integration & Context Tables

#### 4. **SOURCE_SYSTEMS** - Connectors/Integrations
```sql
CREATE TABLE source_systems (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    name                TEXT NOT NULL,
    type                TEXT NOT NULL,  -- wazuh, iris, jira, fortigate, crowdstrike
    base_url            TEXT,
    auth_type           TEXT,  -- api_key, oauth2, basic_auth
    auth_config         JSONB,  -- Encrypted credentials
    is_active           BOOLEAN DEFAULT true,
    last_sync_at        TIMESTAMPTZ,
    sync_status         TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_source_systems_tenant ON source_systems(tenant_id);
CREATE INDEX idx_source_systems_type ON source_systems(type);
```

#### 5. **ASSETS** - IT Assets/Endpoints
```sql
CREATE TABLE assets (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    hostname            TEXT,
    ip_address          INET,
    asset_type          TEXT NOT NULL,  -- server, workstation, network_device
    criticality         TEXT,  -- low, medium, high, critical
    owner_user_id       UUID REFERENCES users(id),
    os                  TEXT,
    environment         TEXT,  -- production, staging, development
    metadata            JSONB,
    is_active           BOOLEAN DEFAULT true,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_assets_tenant ON assets(tenant_id);
CREATE INDEX idx_assets_hostname ON assets(hostname);
CREATE INDEX idx_assets_ip ON assets(ip_address);
CREATE INDEX idx_assets_criticality ON assets(criticality);
```

---

### Alert & Incident Tables

#### 6. **ALERTS** - Normalized Security Alerts
```sql
CREATE TABLE alerts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    source_system_id    UUID REFERENCES source_systems(id),
    asset_id            UUID REFERENCES assets(id),
    source_alert_id     TEXT UNIQUE,
    category            TEXT,
    event_type          TEXT,
    severity            INT,
    status              TEXT DEFAULT 'new',
    title               TEXT,
    description         TEXT,
    src_ip              INET,
    dst_ip              INET,
    src_port            INT,
    dst_port            INT,
    protocol            TEXT,
    username            TEXT,
    hostname            TEXT,
    rule_id             TEXT,
    rule_description    TEXT,
    raw_data            JSONB,
    normalized_data     JSONB,
    timestamp           TIMESTAMPTZ NOT NULL,  -- Event time
    created_at          TIMESTAMPTZ DEFAULT NOW()  -- Ingestion time
);

CREATE INDEX idx_alerts_tenant ON alerts(tenant_id);
CREATE INDEX idx_alerts_source_system ON alerts(source_system_id);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_src_ip ON alerts(src_ip);
CREATE INDEX idx_alerts_dst_ip ON alerts(dst_ip);
CREATE INDEX idx_alerts_hostname ON alerts(hostname);
CREATE INDEX idx_alerts_timestamp ON alerts(timestamp);
```

#### 7. **INCIDENTS** - High-Level Incidents
```sql
CREATE TABLE incidents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    source_system_id    UUID REFERENCES source_systems(id),
    title               TEXT NOT NULL,
    description         TEXT,
    severity            INT,
    status              TEXT DEFAULT 'open',
    category            TEXT,
    subcategory         TEXT,
    source              TEXT,
    source_id           TEXT,
    detected_at         TIMESTAMPTZ,
    resolved_at         TIMESTAMPTZ,
    meta_data           JSONB,
    tags                TEXT[],
    owner_user_id       UUID REFERENCES users(id),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_incidents_tenant ON incidents(tenant_id);
CREATE INDEX idx_incidents_status ON incidents(status);
CREATE INDEX idx_incidents_severity ON incidents(severity);
CREATE INDEX idx_incidents_category ON incidents(category);
```

#### 8. **CASES** - Investigation Cases
```sql
CREATE TABLE cases (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    incident_id         UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    description         TEXT,
    incident_type       TEXT,
    priority            TEXT,
    severity            INT,
    status              TEXT DEFAULT 'open',
    phase               TEXT,  -- NIST IR phases
    assignee_user_id    UUID REFERENCES users(id),
    opened_at           TIMESTAMPTZ DEFAULT NOW(),
    closed_at           TIMESTAMPTZ,
    resolution_summary  TEXT,
    tags                TEXT[],
    external_refs       JSONB,  -- {"iris": "IRIS-0001", "jira": "SOC-123"}
    metadata            JSONB,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_cases_tenant ON cases(tenant_id);
CREATE INDEX idx_cases_incident ON cases(incident_id);
CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_priority ON cases(priority);
```

---

### Playbook & Automation Tables

#### 9. **PLAYBOOKS** - Response Runbooks
```sql
CREATE TABLE playbooks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID REFERENCES tenants(id),  -- NULL = global playbook
    name                TEXT NOT NULL,
    description         TEXT,
    incident_type       TEXT,
    is_active           BOOLEAN DEFAULT true,
    definition          JSONB NOT NULL,  -- Steps, actions, integrations
    version             TEXT DEFAULT '1.0',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_playbooks_tenant ON playbooks(tenant_id);
CREATE INDEX idx_playbooks_type ON playbooks(incident_type);
```

#### 10. **CASE_PLAYBOOKS** - Playbook Execution
```sql
CREATE TABLE case_playbooks (
    case_id             UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    playbook_id         UUID NOT NULL REFERENCES playbooks(id),
    status              TEXT DEFAULT 'not_started',
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    metadata            JSONB,
    PRIMARY KEY (case_id, playbook_id)
);
```

---

### Join & Reference Tables

#### 11. **CASE_ALERTS** - Case ↔ Alert Correlation
```sql
CREATE TABLE case_alerts (
    case_id             UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    alert_id            UUID NOT NULL REFERENCES alerts(id),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (case_id, alert_id)
);
```

#### 12. **CASE_ASSIGNMENTS** - Case ↔ User Assignments
```sql
CREATE TABLE case_assignments (
    case_id             UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(id),
    role                TEXT,  -- lead_analyst, support_analyst
    assigned_at         TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (case_id, user_id)
);
```

#### 13. **CASE_EXTERNAL_REFS** - External System Links
```sql
CREATE TABLE case_external_refs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id             UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    system_type         TEXT NOT NULL,  -- iris, jira, servicenow
    external_id         TEXT NOT NULL,
    url                 TEXT,
    synced_at           TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_external_refs_case ON case_external_refs(case_id);
```

---

### Collaboration & Audit Tables

#### 14. **COMMENTS** - Discussion Threads
```sql
CREATE TABLE comments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content             TEXT NOT NULL,
    incident_id         UUID REFERENCES incidents(id) ON DELETE CASCADE,
    case_id             UUID REFERENCES cases(id) ON DELETE CASCADE,
    author_id           UUID NOT NULL REFERENCES users(id),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_comments_incident ON comments(incident_id);
CREATE INDEX idx_comments_case ON comments(case_id);
```

#### 15. **ACTIVITIES** - Audit Trail
```sql
CREATE TABLE activities (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action              TEXT NOT NULL,
    description         TEXT,
    case_id             UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(id),
    meta_data           JSONB,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_activities_case ON activities(case_id);
CREATE INDEX idx_activities_action ON activities(action);
```

---

## 🔐 Key Design Decisions

### 1. UUID vs Integer IDs
- **UUIDs** allow distributed generation without coordination
- Better for multi-tenant SaaS with data partitioning
- Prevents ID enumeration attacks

### 2. JSONB for Flexibility
- `auth_config` - Encrypted connector credentials
- `definition` - Playbook steps and automation logic
- `metadata` - Extensible context without schema changes
- `external_refs` - Dynamic links to various systems

### 3. PostgreSQL-Specific Types
- `INET` for IP addresses (validates and indexes efficiently)
- `TEXT[]` for tags (queryable arrays)
- `JSONB` for JSON with indexing support
- `TIMESTAMPTZ` for timezone-aware timestamps

### 4. Soft Deletes for Tenants
- Mark `is_active = false` instead of hard delete
- Preserves historical data for compliance
- Allows re-activation if needed

### 5. Cascade Rules
See CASCADE DELETE RULES section in the ER diagram above.

---

## 📈 Scaling Considerations

### Partitioning Strategy
```sql
-- Partition alerts by tenant_id for better performance
CREATE TABLE alerts_econet PARTITION OF alerts
FOR VALUES IN ('uuid-of-econet-tenant');

CREATE TABLE alerts_postbank PARTITION OF alerts
FOR VALUES IN ('uuid-of-postbank-tenant');
```

### Row-Level Security (RLS)
```sql
ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON incidents
    USING (tenant_id IN (
        SELECT tenant_id FROM user_tenants WHERE user_id = current_user_id()
    ));
```

---

## 🔄 Migration Path

### From Single-Tenant to Multi-Tenant

```sql
-- Add tenant_id to existing tables
ALTER TABLE alerts ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE incidents ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE cases ADD COLUMN tenant_id UUID REFERENCES tenants(id);

-- Populate with default tenant for existing data
UPDATE alerts SET tenant_id = (SELECT id FROM tenants WHERE code = 'DEFAULT');
```

---

## ✅ Schema Benefits

| Feature | Benefit |
|---------|---------|
| **Multi-Tenancy** | Serve multiple clients from single platform |
| **Source Systems** | Plug in any SIEM/EDR/ticketing tool |
| **Playbooks** | Automate response with reusable runbooks |
| **Assets** | Context-aware alerting and correlation |
| **External Refs** | Bi-directional sync with IRIS/Jira |
| **UUIDs** | Distributed-friendly, secure |
| **JSONB** | Flexible without schema migrations |
| **Audit Trail** | Full compliance and forensics |

---

**This schema is production-ready for a multi-tenant SOC platform!** 🚀
