-- ============================================================================
-- Hubsec SOC Platform - Database Schema
-- Generated SQL DDL for SQLite/PostgreSQL
-- ============================================================================

-- ============================================================================
-- TABLE: users
-- SOC Analysts and Administrators
-- ============================================================================
CREATE TABLE users (
    id INTEGER NOT NULL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    hashed_password VARCHAR(255) NOT NULL,
    is_active INTEGER DEFAULT 1,
    role VARCHAR(11) NOT NULL,  -- admin, analyst, viewer, soc_manager
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- ============================================================================
-- TABLE: incidents
-- High-level Security Incidents
-- ============================================================================
CREATE TABLE incidents (
    id INTEGER NOT NULL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    severity VARCHAR(8) NOT NULL,  -- critical, high, medium, low, info
    status VARCHAR(14) DEFAULT 'open',  -- open, in_progress, investigating, resolved, closed, false_positive
    source VARCHAR(100),
    source_id VARCHAR(255),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    assigned_to_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    detected_at DATETIME,
    resolved_at DATETIME,
    meta_data JSON,
    tags JSON,
    FOREIGN KEY(assigned_to_id) REFERENCES users(id)
);

CREATE INDEX idx_incidents_title ON incidents(title);
CREATE INDEX idx_incidents_severity ON incidents(severity);
CREATE INDEX idx_incidents_status ON incidents(status);
CREATE INDEX idx_incidents_category ON incidents(category);
CREATE INDEX idx_incidents_source_id ON incidents(source_id);
CREATE INDEX idx_incidents_created_at ON incidents(created_at);
CREATE INDEX idx_incidents_detected_at ON incidents(detected_at);

-- ============================================================================
-- TABLE: cases
-- Investigation Cases
-- ============================================================================
CREATE TABLE cases (
    id INTEGER NOT NULL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(11) DEFAULT 'open',  -- open, in_progress, pending, resolved, closed
    priority VARCHAR(8) NOT NULL,  -- critical, high, medium, low, info
    incident_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    closed_at DATETIME,
    resolution TEXT,
    tags JSON,
    meta_data JSON,
    FOREIGN KEY(incident_id) REFERENCES incidents(id) ON DELETE CASCADE
);

CREATE INDEX idx_cases_title ON cases(title);
CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_priority ON cases(priority);
CREATE INDEX idx_cases_incident_id ON cases(incident_id);
CREATE INDEX idx_cases_created_at ON cases(created_at);

-- ============================================================================
-- TABLE: alerts
-- Individual Security Alerts
-- ============================================================================
CREATE TABLE alerts (
    id INTEGER NOT NULL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,
    source_id VARCHAR(255) UNIQUE,
    rule_id VARCHAR(100),
    rule_description TEXT,
    severity VARCHAR(8) NOT NULL,  -- critical, high, medium, low, info
    status VARCHAR(8) DEFAULT 'new',  -- new, triaged, in_case, ignored, resolved
    event_type VARCHAR(100),
    category VARCHAR(100),
    src_ip VARCHAR(45),
    dst_ip VARCHAR(45),
    src_port INTEGER,
    dst_port INTEGER,
    protocol VARCHAR(20),
    hostname VARCHAR(255),
    agent_id VARCHAR(100),
    agent_name VARCHAR(255),
    username VARCHAR(255),
    filename VARCHAR(500),
    file_path TEXT,
    file_hash VARCHAR(128),
    timestamp DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    raw_data JSON,
    normalized_data JSON
);

CREATE INDEX idx_alerts_source ON alerts(source);
CREATE INDEX idx_alerts_source_id ON alerts(source_id);
CREATE INDEX idx_alerts_rule_id ON alerts(rule_id);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_event_type ON alerts(event_type);
CREATE INDEX idx_alerts_category ON alerts(category);
CREATE INDEX idx_alerts_src_ip ON alerts(src_ip);
CREATE INDEX idx_alerts_dst_ip ON alerts(dst_ip);
CREATE INDEX idx_alerts_hostname ON alerts(hostname);
CREATE INDEX idx_alerts_agent_id ON alerts(agent_id);
CREATE INDEX idx_alerts_username ON alerts(username);
CREATE INDEX idx_alerts_timestamp ON alerts(timestamp);

-- ============================================================================
-- TABLE: comments
-- Comments on Incidents and Cases
-- ============================================================================
CREATE TABLE comments (
    id INTEGER NOT NULL PRIMARY KEY,
    content TEXT NOT NULL,
    incident_id INTEGER,
    case_id INTEGER,
    author_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(incident_id) REFERENCES incidents(id) ON DELETE CASCADE,
    FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY(author_id) REFERENCES users(id)
);

CREATE INDEX idx_comments_incident_id ON comments(incident_id);
CREATE INDEX idx_comments_case_id ON comments(case_id);

-- ============================================================================
-- TABLE: activities
-- Audit Trail for Case Activities
-- ============================================================================
CREATE TABLE activities (
    id INTEGER NOT NULL PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    description TEXT,
    case_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    meta_data JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE INDEX idx_activities_action ON activities(action);
CREATE INDEX idx_activities_case_id ON activities(case_id);
CREATE INDEX idx_activities_created_at ON activities(created_at);

-- ============================================================================
-- TABLE: case_alerts (Join Table)
-- Many-to-Many: Cases <-> Alerts
-- ============================================================================
CREATE TABLE case_alerts (
    case_id INTEGER NOT NULL,
    alert_id INTEGER NOT NULL,
    PRIMARY KEY (case_id, alert_id),
    FOREIGN KEY(case_id) REFERENCES cases(id),
    FOREIGN KEY(alert_id) REFERENCES alerts(id)
);

-- ============================================================================
-- TABLE: case_assignments (Join Table)
-- Many-to-Many: Cases <-> Users
-- ============================================================================
CREATE TABLE case_assignments (
    case_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY (case_id, user_id),
    FOREIGN KEY(case_id) REFERENCES cases(id),
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- ============================================================================
-- SAMPLE DATA (Optional - for testing)
-- ============================================================================

-- Insert sample admin user (password: admin123)
INSERT INTO users (username, email, full_name, role, hashed_password, is_active)
VALUES ('admin', 'admin@hubsec.local', 'System Administrator', 'admin',
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 1);

-- Note: Run the Python script scripts/init_db.py --seed for complete sample data
