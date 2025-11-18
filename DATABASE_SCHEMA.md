# 🗄️ Hubsec SOC Platform - Database Schema

## Database Schema Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATABASE SCHEMA OVERVIEW                        │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────┐
│     USERS        │         │    INCIDENTS     │
├──────────────────┤         ├──────────────────┤
│ id (PK)          │────┐    │ id (PK)          │
│ username         │    │    │ title            │
│ email            │    │    │ description      │
│ full_name        │    │    │ severity         │
│ hashed_password  │    │    │ status           │
│ is_active        │    │    │ source           │
│ role             │    │    │ source_id        │
│ created_at       │    │    │ category         │
│ last_login       │    │    │ subcategory      │
└──────────────────┘    │    │ assigned_to_id ──┼────┐
                        │    │ created_at       │    │
                        │    │ updated_at       │    │
                        │    │ detected_at      │    │
                        │    │ resolved_at      │    │
                        │    │ meta_data        │    │
                        │    │ tags             │    │
                        │    └──────────────────┘    │
                        │             │              │
                        │             │ 1:N          │
                        │             ▼              │
                        │    ┌──────────────────┐   │
                        │    │      CASES       │   │
                        │    ├──────────────────┤   │
                        │    │ id (PK)          │   │
                        │    │ title            │   │
                        │    │ description      │   │
                        │    │ status           │   │
                        │    │ priority         │   │
                        │    │ incident_id (FK) │───┘
                        │    │ created_at       │
                        │    │ updated_at       │
                        │    │ closed_at        │
                        │    │ resolution       │
                        │    │ tags             │
                        │    │ meta_data        │
                        │    └──────────────────┘
                        │             │
                        │             │ M:N
                        │             ▼
┌─────────────────────────────────────────────┐
│        CASE_ASSIGNMENTS (Join Table)        │
├─────────────────────────────────────────────┤
│ case_id (PK, FK) ──┼── CASES.id            │
│ user_id (PK, FK) ──┼── USERS.id            │
└─────────────────────────────────────────────┘
                        │
                        │ M:N
                        ▼
┌─────────────────────────────────────────────┐
│          CASE_ALERTS (Join Table)           │
├─────────────────────────────────────────────┤
│ case_id (PK, FK) ──┼── CASES.id            │
│ alert_id (PK, FK) ─┼── ALERTS.id           │
└─────────────────────────────────────────────┘
                        │
                        ▼
                ┌──────────────────┐
                │     ALERTS       │
                ├──────────────────┤
                │ id (PK)          │
                │ source           │
                │ source_id        │
                │ rule_id          │
                │ rule_description │
                │ severity         │
                │ status           │
                │ event_type       │
                │ category         │
                │ src_ip           │
                │ dst_ip           │
                │ src_port         │
                │ dst_port         │
                │ protocol         │
                │ hostname         │
                │ agent_id         │
                │ agent_name       │
                │ username         │
                │ filename         │
                │ file_path        │
                │ file_hash        │
                │ timestamp        │
                │ created_at       │
                │ raw_data         │
                │ normalized_data  │
                └──────────────────┘

┌──────────────────┐         ┌──────────────────┐
│    COMMENTS      │         │   ACTIVITIES     │
├──────────────────┤         ├──────────────────┤
│ id (PK)          │         │ id (PK)          │
│ content          │         │ action           │
│ incident_id (FK) │         │ description      │
│ case_id (FK)     │         │ case_id (FK)     │
│ author_id (FK) ──┼───┐     │ user_id (FK) ────┼───┐
│ created_at       │   │     │ meta_data        │   │
│ updated_at       │   │     │ created_at       │   │
└──────────────────┘   │     └──────────────────┘   │
                       │                             │
                       └─────────────────────────────┘
                                   │
                                   └──► USERS.id


═══════════════════════════════════════════════════════════════════════

## RELATIONSHIPS

### One-to-Many (1:N)
- Users → Incidents (assigned_to)
- Incidents → Cases (incident_id)
- Incidents → Comments (incident_id)
- Cases → Comments (case_id)
- Cases → Activities (case_id)
- Users → Comments (author_id)
- Users → Activities (user_id)

### Many-to-Many (M:N)
- Cases ↔ Users (via case_assignments table)
- Cases ↔ Alerts (via case_alerts table)

═══════════════════════════════════════════════════════════════════════
```

## Detailed Table Definitions

### 1. **USERS** - SOC Analysts and Administrators
```sql
Table: users
- id              INTEGER PRIMARY KEY
- username        VARCHAR(100) UNIQUE NOT NULL
- email           VARCHAR(255) UNIQUE NOT NULL
- full_name       VARCHAR(255)
- hashed_password VARCHAR(255) NOT NULL
- is_active       INTEGER DEFAULT 1
- role            ENUM('admin', 'analyst', 'viewer', 'soc_manager')
- created_at      DATETIME
- last_login      DATETIME

Indexes:
- PRIMARY KEY (id)
- UNIQUE (username)
- UNIQUE (email)
```

### 2. **INCIDENTS** - High-level Security Incidents
```sql
Table: incidents
- id              INTEGER PRIMARY KEY
- title           VARCHAR(255) NOT NULL
- description     TEXT
- severity        ENUM('critical', 'high', 'medium', 'low', 'info')
- status          ENUM('open', 'in_progress', 'investigating', 'resolved', 'closed', 'false_positive')
- source          VARCHAR(100)
- source_id       VARCHAR(255)
- category        VARCHAR(100)
- subcategory     VARCHAR(100)
- assigned_to_id  INTEGER (FK → users.id)
- created_at      DATETIME
- updated_at      DATETIME
- detected_at     DATETIME
- resolved_at     DATETIME
- meta_data       JSON
- tags            JSON

Indexes:
- PRIMARY KEY (id)
- INDEX (title)
- INDEX (severity)
- INDEX (status)
- INDEX (category)
- INDEX (source_id)
- INDEX (created_at)
- INDEX (detected_at)
- FOREIGN KEY (assigned_to_id) → users(id)
```

### 3. **CASES** - Investigation Cases
```sql
Table: cases
- id              INTEGER PRIMARY KEY
- title           VARCHAR(255) NOT NULL
- description     TEXT
- status          ENUM('open', 'in_progress', 'pending', 'resolved', 'closed')
- priority        ENUM('critical', 'high', 'medium', 'low', 'info')
- incident_id     INTEGER NOT NULL (FK → incidents.id)
- created_at      DATETIME
- updated_at      DATETIME
- closed_at       DATETIME
- resolution      TEXT
- tags            JSON
- meta_data       JSON

Indexes:
- PRIMARY KEY (id)
- INDEX (title)
- INDEX (status)
- INDEX (priority)
- INDEX (incident_id)
- INDEX (created_at)
- FOREIGN KEY (incident_id) → incidents(id) ON DELETE CASCADE
```

### 4. **ALERTS** - Individual Security Alerts
```sql
Table: alerts
- id                INTEGER PRIMARY KEY
- source            VARCHAR(100) NOT NULL
- source_id         VARCHAR(255) UNIQUE
- rule_id           VARCHAR(100)
- rule_description  TEXT
- severity          ENUM('critical', 'high', 'medium', 'low', 'info')
- status            ENUM('new', 'triaged', 'in_case', 'ignored', 'resolved')
- event_type        VARCHAR(100)
- category          VARCHAR(100)
- src_ip            VARCHAR(45)
- dst_ip            VARCHAR(45)
- src_port          INTEGER
- dst_port          INTEGER
- protocol          VARCHAR(20)
- hostname          VARCHAR(255)
- agent_id          VARCHAR(100)
- agent_name        VARCHAR(255)
- username          VARCHAR(255)
- filename          VARCHAR(500)
- file_path         TEXT
- file_hash         VARCHAR(128)
- timestamp         DATETIME NOT NULL
- created_at        DATETIME
- raw_data          JSON
- normalized_data   JSON

Indexes:
- PRIMARY KEY (id)
- UNIQUE (source_id)
- INDEX (source)
- INDEX (rule_id)
- INDEX (severity)
- INDEX (status)
- INDEX (event_type)
- INDEX (category)
- INDEX (src_ip)
- INDEX (dst_ip)
- INDEX (hostname)
- INDEX (agent_id)
- INDEX (username)
- INDEX (timestamp)
```

### 5. **COMMENTS** - Comments on Incidents/Cases
```sql
Table: comments
- id              INTEGER PRIMARY KEY
- content         TEXT NOT NULL
- incident_id     INTEGER (FK → incidents.id)
- case_id         INTEGER (FK → cases.id)
- author_id       INTEGER NOT NULL (FK → users.id)
- created_at      DATETIME
- updated_at      DATETIME

Indexes:
- PRIMARY KEY (id)
- INDEX (incident_id)
- INDEX (case_id)
- FOREIGN KEY (incident_id) → incidents(id) ON DELETE CASCADE
- FOREIGN KEY (case_id) → cases(id) ON DELETE CASCADE
- FOREIGN KEY (author_id) → users(id)
```

### 6. **ACTIVITIES** - Audit Trail for Cases
```sql
Table: activities
- id              INTEGER PRIMARY KEY
- action          VARCHAR(100) NOT NULL
- description     TEXT
- case_id         INTEGER NOT NULL (FK → cases.id)
- user_id         INTEGER NOT NULL (FK → users.id)
- meta_data       JSON
- created_at      DATETIME

Indexes:
- PRIMARY KEY (id)
- INDEX (action)
- INDEX (case_id)
- INDEX (created_at)
- FOREIGN KEY (case_id) → cases(id) ON DELETE CASCADE
- FOREIGN KEY (user_id) → users(id)
```

### 7. **CASE_ASSIGNMENTS** - Many-to-Many Join Table
```sql
Table: case_assignments
- case_id         INTEGER (PK, FK → cases.id)
- user_id         INTEGER (PK, FK → users.id)

Indexes:
- PRIMARY KEY (case_id, user_id)
- FOREIGN KEY (case_id) → cases(id)
- FOREIGN KEY (user_id) → users(id)
```

### 8. **CASE_ALERTS** - Many-to-Many Join Table
```sql
Table: case_alerts
- case_id         INTEGER (PK, FK → cases.id)
- alert_id        INTEGER (PK, FK → alerts.id)

Indexes:
- PRIMARY KEY (case_id, alert_id)
- FOREIGN KEY (case_id) → cases(id)
- FOREIGN KEY (alert_id) → alerts(id)
```

═══════════════════════════════════════════════════════════════════════

## Enum Definitions

### SeverityLevel
- `critical` - Critical severity
- `high` - High severity
- `medium` - Medium severity
- `low` - Low severity
- `info` - Informational

### IncidentStatus
- `open` - Newly created incident
- `in_progress` - Being investigated
- `investigating` - Active investigation
- `resolved` - Issue resolved
- `closed` - Incident closed
- `false_positive` - Determined to be false alarm

### CaseStatus
- `open` - Case opened
- `in_progress` - Investigation in progress
- `pending` - Waiting for additional info
- `resolved` - Case resolved
- `closed` - Case closed

### AlertStatus
- `new` - Newly received alert
- `triaged` - Initial review completed
- `in_case` - Added to a case
- `ignored` - Marked as not relevant
- `resolved` - Handled/resolved

### UserRole
- `admin` - Full system access
- `analyst` - SOC analyst
- `viewer` - Read-only access
- `soc_manager` - Team manager

═══════════════════════════════════════════════════════════════════════

## Cascade Delete Rules

When deleting:
- **Incident** → All related cases, comments are deleted
- **Case** → All related comments and activities are deleted
- **User** → Assigned incidents remain but assignment is nullified

═══════════════════════════════════════════════════════════════════════

## Notes

1. **Database Engine**: SQLite (development) or PostgreSQL (production)
2. **ORM**: SQLAlchemy 2.0
3. **Migrations**: Alembic (optional, can be added)
4. **JSON Fields**: Store flexible metadata and configuration
5. **Timestamps**: Automatic tracking of creation and updates
6. **Indexes**: Optimized for common query patterns

═══════════════════════════════════════════════════════════════════════
