#!/usr/bin/env python3
"""
Database Initialization Script for Multi-Tenant PostgreSQL Schema
Creates tables and optionally seeds with sample multi-tenant data

IMPORTANT: This script requires PostgreSQL with UUID extension
"""
import sys
import os
from datetime import datetime, timedelta
import random
import uuid

# Add parent directory to path to import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.app.models.models_multitenant import (
    Base, User, Tenant, SourceSystem, Asset, Incident, Case, Alert,
    Comment, Activity, Playbook, CasePlaybook, CaseExternalRef,
    UserRole, IncidentStatus, CaseStatus, AlertStatus, SeverityLevel,
    AssetType, IntegrationType, PlaybookStatus
)
import hashlib


def hash_password(password: str) -> str:
    """Simple password hashing (same as in users.py)"""
    return hashlib.sha256(password.encode()).hexdigest()


def enable_uuid_extension(engine):
    """Enable PostgreSQL UUID extension"""
    print("Enabling PostgreSQL UUID extension...")
    with engine.connect() as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        conn.commit()
    print("✅ UUID extension enabled")


def create_tables(engine):
    """Create all database tables"""
    print("\nCreating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully")


def seed_tenants(session):
    """Create sample tenant organizations"""
    print("\n🏢 Seeding tenants...")

    tenants = [
        Tenant(
            name="Econet Wireless Zimbabwe",
            code="ECONET",
            industry="Telecommunications",
            region="Zimbabwe",
            contact_name="John Doe",
            contact_email="security@econet.co.zw",
            contact_phone="+263-4-123456",
            is_active=True,
            subscription_tier="enterprise",
            settings={"alert_threshold": "medium", "retention_days": 90}
        ),
        Tenant(
            name="PostBank Zimbabwe",
            code="POSTBANK",
            industry="Banking",
            region="Zimbabwe",
            contact_name="Jane Smith",
            contact_email="security@postbank.co.zw",
            contact_phone="+263-4-654321",
            is_active=True,
            subscription_tier="professional",
            settings={"alert_threshold": "low", "retention_days": 180}
        ),
        Tenant(
            name="TelOne Zimbabwe",
            code="TELONE",
            industry="Telecommunications",
            region="Zimbabwe",
            contact_name="Mike Johnson",
            contact_email="security@telone.co.zw",
            contact_phone="+263-4-789012",
            is_active=True,
            subscription_tier="enterprise",
            settings={"alert_threshold": "high", "retention_days": 120}
        )
    ]

    for tenant in tenants:
        session.add(tenant)

    session.commit()
    print(f"✅ Created {len(tenants)} tenants")
    return tenants


def seed_users(session, tenants):
    """Create sample users (Hubsec staff + tenant users)"""
    print("\n👥 Seeding users...")

    # Hubsec super admin and analysts
    hubsec_users = [
        User(
            username="superadmin",
            email="admin@hubsec.local",
            full_name="Hubsec Super Admin",
            role=UserRole.SUPER_ADMIN,
            hashed_password=hash_password("admin123"),
            is_active=True
        ),
        User(
            username="hubsec_analyst1",
            email="analyst1@hubsec.local",
            full_name="Hubsec SOC Analyst 1",
            role=UserRole.HUBSEC_ANALYST,
            hashed_password=hash_password("analyst123"),
            is_active=True
        ),
        User(
            username="hubsec_analyst2",
            email="analyst2@hubsec.local",
            full_name="Hubsec SOC Analyst 2",
            role=UserRole.HUBSEC_ANALYST,
            hashed_password=hash_password("analyst123"),
            is_active=True
        )
    ]

    # Tenant-specific users
    tenant_users = [
        User(
            username="econet_admin",
            email="admin@econet.local",
            full_name="Econet Security Admin",
            role=UserRole.TENANT_ADMIN,
            hashed_password=hash_password("econet123"),
            is_active=True
        ),
        User(
            username="econet_analyst",
            email="analyst@econet.local",
            full_name="Econet Security Analyst",
            role=UserRole.ANALYST,
            hashed_password=hash_password("econet123"),
            is_active=True
        ),
        User(
            username="postbank_admin",
            email="admin@postbank.local",
            full_name="PostBank Security Admin",
            role=UserRole.TENANT_ADMIN,
            hashed_password=hash_password("postbank123"),
            is_active=True
        ),
        User(
            username="telone_viewer",
            email="viewer@telone.local",
            full_name="TelOne Security Viewer",
            role=UserRole.VIEWER,
            hashed_password=hash_password("telone123"),
            is_active=True
        )
    ]

    all_users = hubsec_users + tenant_users
    for user in all_users:
        session.add(user)

    session.flush()  # Get user IDs

    # Assign Hubsec analysts to all tenants
    for analyst in hubsec_users[1:]:  # Skip super admin
        for tenant in tenants:
            analyst.tenants.append(tenant)

    # Assign tenant users to their respective tenants
    tenant_users[0].tenants.append(tenants[0])  # Econet admin
    tenant_users[1].tenants.append(tenants[0])  # Econet analyst
    tenant_users[2].tenants.append(tenants[1])  # PostBank admin
    tenant_users[3].tenants.append(tenants[2])  # TelOne viewer

    session.commit()
    print(f"✅ Created {len(all_users)} users with tenant associations")
    return all_users


def seed_source_systems(session, tenants):
    """Create sample source systems/integrations"""
    print("\n🔌 Seeding source systems...")

    systems = [
        # Econet integrations
        SourceSystem(
            tenant_id=tenants[0].id,
            name="Econet Wazuh Manager",
            type=IntegrationType.WAZUH,
            description="Primary SIEM for Econet infrastructure",
            base_url="https://wazuh.econet.co.zw",
            auth_type="api_key",
            auth_config={"api_key": "encrypted_key_placeholder"},
            is_active=True,
            sync_status="healthy",
            config={"rules_version": "4.5.0", "agent_count": 150}
        ),
        SourceSystem(
            tenant_id=tenants[0].id,
            name="Econet IRIS",
            type=IntegrationType.IRIS,
            description="IRIS case management system",
            base_url="https://iris.econet.co.zw",
            auth_type="oauth2",
            auth_config={"client_id": "econet_client"},
            is_active=True,
            sync_status="healthy",
            config={"sync_interval": 300}
        ),
        # PostBank integrations
        SourceSystem(
            tenant_id=tenants[1].id,
            name="PostBank Wazuh",
            type=IntegrationType.WAZUH,
            description="PostBank Wazuh deployment",
            base_url="https://wazuh.postbank.co.zw",
            auth_type="api_key",
            auth_config={"api_key": "encrypted_key_placeholder"},
            is_active=True,
            sync_status="healthy",
            config={"rules_version": "4.5.2", "agent_count": 75}
        ),
        SourceSystem(
            tenant_id=tenants[1].id,
            name="PostBank Jira",
            type=IntegrationType.JIRA,
            description="Jira for incident tracking",
            base_url="https://jira.postbank.co.zw",
            auth_type="basic_auth",
            auth_config={"username": "api_user"},
            is_active=True,
            sync_status="healthy",
            config={"project_key": "SEC"}
        ),
        # TelOne integration
        SourceSystem(
            tenant_id=tenants[2].id,
            name="TelOne Wazuh",
            type=IntegrationType.WAZUH,
            description="TelOne security monitoring",
            base_url="https://wazuh.telone.co.zw",
            auth_type="api_key",
            auth_config={"api_key": "encrypted_key_placeholder"},
            is_active=True,
            sync_status="healthy",
            config={"rules_version": "4.4.5", "agent_count": 120}
        )
    ]

    for system in systems:
        session.add(system)

    session.commit()
    print(f"✅ Created {len(systems)} source systems")
    return systems


def seed_assets(session, tenants):
    """Create sample IT assets"""
    print("\n💻 Seeding assets...")

    assets = [
        # Econet assets
        Asset(
            tenant_id=tenants[0].id,
            hostname="econet-web-01",
            ip_address="192.168.10.10",
            mac_address="00:1A:2B:3C:4D:5E",
            asset_type=AssetType.SERVER,
            criticality=SeverityLevel.HIGH,
            os="Ubuntu 22.04 LTS",
            os_version="22.04.3",
            environment="production",
            owner="IT Operations",
            department="Infrastructure",
            location="Harare DC1",
            is_active=True,
            tags=["web", "public-facing", "critical"]
        ),
        Asset(
            tenant_id=tenants[0].id,
            hostname="econet-db-01",
            ip_address="192.168.10.20",
            asset_type=AssetType.DATABASE,
            criticality=SeverityLevel.CRITICAL,
            os="PostgreSQL 15",
            environment="production",
            owner="Database Team",
            department="Infrastructure",
            location="Harare DC1",
            is_active=True,
            tags=["database", "postgresql", "pci-scope"]
        ),
        # PostBank assets
        Asset(
            tenant_id=tenants[1].id,
            hostname="postbank-app-01",
            ip_address="10.50.1.10",
            asset_type=AssetType.APPLICATION,
            criticality=SeverityLevel.CRITICAL,
            os="Windows Server 2019",
            environment="production",
            owner="Application Team",
            department="IT",
            location="Bulawayo DC",
            is_active=True,
            tags=["banking", "core-banking", "critical"]
        ),
        # TelOne asset
        Asset(
            tenant_id=tenants[2].id,
            hostname="telone-fw-01",
            ip_address="172.16.1.1",
            asset_type=AssetType.NETWORK_DEVICE,
            criticality=SeverityLevel.HIGH,
            os="FortiOS 7.0",
            environment="production",
            owner="Network Team",
            department="Infrastructure",
            location="Main NOC",
            is_active=True,
            tags=["firewall", "perimeter", "critical"]
        )
    ]

    for asset in assets:
        session.add(asset)

    session.commit()
    print(f"✅ Created {len(assets)} assets")
    return assets


def seed_alerts(session, tenants, source_systems, assets):
    """Create sample security alerts"""
    print("\n🚨 Seeding alerts...")

    alert_templates = [
        {
            "rule_description": "Multiple failed SSH login attempts",
            "severity": SeverityLevel.HIGH,
            "category": "authentication",
            "event_type": "authentication_failed"
        },
        {
            "rule_description": "Malware detected - Trojan.GenericKD",
            "severity": SeverityLevel.CRITICAL,
            "category": "malware",
            "event_type": "malware_detected"
        },
        {
            "rule_description": "Suspicious PowerShell execution",
            "severity": SeverityLevel.MEDIUM,
            "category": "system",
            "event_type": "suspicious_process"
        },
        {
            "rule_description": "Possible data exfiltration detected",
            "severity": SeverityLevel.CRITICAL,
            "category": "intrusion",
            "event_type": "data_transfer"
        },
        {
            "rule_description": "Web application attack detected",
            "severity": SeverityLevel.HIGH,
            "category": "web",
            "event_type": "web_attack"
        }
    ]

    alerts = []
    for i in range(50):  # Create 50 sample alerts across tenants
        tenant = random.choice(tenants)
        tenant_systems = [s for s in source_systems if s.tenant_id == tenant.id and s.type == IntegrationType.WAZUH]
        tenant_assets = [a for a in assets if a.tenant_id == tenant.id]

        template = random.choice(alert_templates)
        timestamp = datetime.utcnow() - timedelta(hours=random.randint(1, 168))  # Last 7 days

        alert = Alert(
            tenant_id=tenant.id,
            source_system_id=tenant_systems[0].id if tenant_systems else None,
            asset_id=random.choice(tenant_assets).id if tenant_assets and random.random() > 0.3 else None,
            source_id=f"wazuh-{tenant.code.lower()}-{i+1000}",
            rule_id=f"{random.randint(1000, 9999)}",
            rule_description=template["rule_description"],
            severity=template["severity"],
            status=random.choice([AlertStatus.NEW, AlertStatus.TRIAGED, AlertStatus.IN_CASE]),
            event_type=template["event_type"],
            category=template["category"],
            timestamp=timestamp,
            src_ip=f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}",
            dst_ip=f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}",
            src_port=random.randint(1024, 65535),
            dst_port=random.choice([80, 443, 22, 3389, 3306]),
            protocol=random.choice(["TCP", "UDP"]),
            hostname=f"host-{random.randint(1, 100):03d}",
            agent_id=f"agent-{random.randint(1, 100):03d}",
            agent_name=f"agent-{tenant.code.lower()}-{random.randint(1, 50)}",
            raw_data={"sample": "alert_data", "tenant": tenant.code},
            normalized_data={"category": template["category"], "severity": template["severity"].value}
        )
        alerts.append(alert)
        session.add(alert)

    session.commit()
    print(f"✅ Created {len(alerts)} alerts across all tenants")
    return alerts


def seed_incidents_and_cases(session, tenants, source_systems, users, alerts, assets):
    """Create sample incidents and cases"""
    print("\n📋 Seeding incidents and cases...")

    incidents = []
    cases = []

    # Econet incident
    econet_incident = Incident(
        tenant_id=tenants[0].id,
        source_system_id=[s for s in source_systems if s.tenant_id == tenants[0].id][0].id,
        title="Ransomware Attack - Econet Infrastructure",
        description="Multiple systems showing signs of ransomware encryption",
        severity=SeverityLevel.CRITICAL,
        status=IncidentStatus.IN_PROGRESS,
        category="malware",
        incident_type="ransomware",
        assigned_to_id=users[1].id,  # Hubsec analyst
        detected_at=datetime.utcnow() - timedelta(hours=24),
        tags=["ransomware", "critical", "econet"]
    )
    session.add(econet_incident)
    session.flush()
    incidents.append(econet_incident)

    # Create case for Econet incident
    econet_case = Case(
        tenant_id=tenants[0].id,
        incident_id=econet_incident.id,
        title="Econet Ransomware Containment",
        description="Contain and eradicate ransomware infection",
        status=CaseStatus.IN_PROGRESS,
        priority=SeverityLevel.CRITICAL,
        tags=["containment", "forensics"]
    )
    econet_case.assigned_users.append(users[1])  # Hubsec analyst
    econet_case.assigned_users.append(users[3])  # Econet admin

    # Link alerts to case
    econet_alerts = [a for a in alerts if a.tenant_id == tenants[0].id and a.category == "malware"][:5]
    for alert in econet_alerts:
        econet_case.alerts.append(alert)
        alert.status = AlertStatus.IN_CASE

    session.add(econet_case)
    cases.append(econet_case)

    # PostBank incident
    postbank_incident = Incident(
        tenant_id=tenants[1].id,
        source_system_id=[s for s in source_systems if s.tenant_id == tenants[1].id][0].id,
        title="Brute Force Attack on Banking Portal",
        description="Multiple failed login attempts on online banking portal",
        severity=SeverityLevel.HIGH,
        status=IncidentStatus.OPEN,
        category="authentication",
        incident_type="brute_force",
        assigned_to_id=users[2].id,  # Hubsec analyst 2
        detected_at=datetime.utcnow() - timedelta(hours=6),
        tags=["brute-force", "banking", "postbank"]
    )
    session.add(postbank_incident)
    session.flush()
    incidents.append(postbank_incident)

    # Create case for PostBank incident
    postbank_case = Case(
        tenant_id=tenants[1].id,
        incident_id=postbank_incident.id,
        title="PostBank Portal Attack Investigation",
        description="Investigate and block brute force attack",
        status=CaseStatus.OPEN,
        priority=SeverityLevel.HIGH,
        tags=["investigation", "blocking"]
    )
    postbank_case.assigned_users.append(users[2])  # Hubsec analyst 2
    postbank_case.assigned_users.append(users[5])  # PostBank admin

    postbank_alerts = [a for a in alerts if a.tenant_id == tenants[1].id and a.category == "authentication"][:3]
    for alert in postbank_alerts:
        postbank_case.alerts.append(alert)
        alert.status = AlertStatus.IN_CASE

    session.add(postbank_case)
    session.flush()
    cases.append(postbank_case)

    # Add external reference (IRIS case for Econet)
    iris_ref = CaseExternalRef(
        case_id=econet_case.id,
        system_type="iris",
        external_id="IRIS-2024-0001",
        url="https://iris.econet.co.zw/cases/1",
        sync_status="synced"
    )
    session.add(iris_ref)

    # Add external reference (Jira ticket for PostBank)
    jira_ref = CaseExternalRef(
        case_id=postbank_case.id,
        system_type="jira",
        external_id="SEC-123",
        url="https://jira.postbank.co.zw/browse/SEC-123",
        sync_status="synced"
    )
    session.add(jira_ref)

    session.commit()
    print(f"✅ Created {len(incidents)} incidents and {len(cases)} cases with external references")
    return incidents, cases


def seed_playbooks(session, tenants):
    """Create sample playbooks"""
    print("\n📖 Seeding playbooks...")

    playbooks = [
        # Global playbook (available to all)
        Playbook(
            tenant_id=None,  # Global
            name="Ransomware Response Playbook",
            description="Standard operating procedure for ransomware incidents",
            incident_type="ransomware",
            version="1.0",
            is_active=True,
            tags=["ransomware", "malware", "critical"],
            definition={
                "steps": [
                    {"id": 1, "action": "Isolate infected systems", "type": "manual"},
                    {"id": 2, "action": "Identify ransomware variant", "type": "investigation"},
                    {"id": 3, "action": "Block C2 communication", "type": "automation"},
                    {"id": 4, "action": "Restore from backups", "type": "manual"},
                    {"id": 5, "action": "Verify system integrity", "type": "validation"}
                ]
            }
        ),
        # Tenant-specific playbook
        Playbook(
            tenant_id=tenants[1].id,  # PostBank
            name="Banking Portal Incident Response",
            description="PostBank-specific response to portal attacks",
            incident_type="brute_force",
            version="2.1",
            is_active=True,
            tags=["banking", "authentication", "portal"],
            definition={
                "steps": [
                    {"id": 1, "action": "Enable rate limiting", "type": "automation"},
                    {"id": 2, "action": "Block attacking IPs", "type": "automation"},
                    {"id": 3, "action": "Notify customers", "type": "manual"},
                    {"id": 4, "action": "Review access logs", "type": "investigation"}
                ]
            }
        )
    ]

    for playbook in playbooks:
        session.add(playbook)

    session.commit()
    print(f"✅ Created {len(playbooks)} playbooks")
    return playbooks


def seed_comments_and_activities(session, incidents, cases, users):
    """Create sample comments and activities"""
    print("\n💬 Seeding comments and activities...")

    comments = [
        Comment(
            content="Initial triage completed. Ransomware strain identified as LockBit 3.0.",
            case_id=cases[0].id,
            author_id=users[1].id
        ),
        Comment(
            content="Isolated affected systems from network. Beginning forensic analysis.",
            case_id=cases[0].id,
            author_id=users[3].id  # Econet admin
        ),
        Comment(
            content="Implemented IP blocking at firewall. No successful logins detected.",
            case_id=cases[1].id,
            author_id=users[2].id
        ),
        Comment(
            content="Escalating to management for customer notification.",
            incident_id=incidents[1].id,
            author_id=users[5].id  # PostBank admin
        )
    ]

    for comment in comments:
        session.add(comment)

    # Add activities
    activities = [
        Activity(
            case_id=cases[0].id,
            user_id=users[1].id,
            action="case_created",
            description="Case created and assigned to Hubsec analyst",
            meta_data={"priority": "critical", "automated": False}
        ),
        Activity(
            case_id=cases[0].id,
            user_id=users[1].id,
            action="status_updated",
            description="Case status changed to IN_PROGRESS",
            meta_data={"old_status": "open", "new_status": "in_progress"}
        ),
        Activity(
            case_id=cases[1].id,
            user_id=users[2].id,
            action="case_created",
            description="Case created for brute force investigation"
        ),
        Activity(
            case_id=cases[1].id,
            user_id=users[2].id,
            action="alert_added",
            description="3 alerts linked to case",
            meta_data={"alert_count": 3}
        )
    ]

    for activity in activities:
        session.add(activity)

    session.commit()
    print(f"✅ Created {len(comments)} comments and {len(activities)} activities")


def main():
    """Main initialization function"""
    import argparse

    parser = argparse.ArgumentParser(description="Initialize Hubsec multi-tenant PostgreSQL database")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", "postgresql://hubsec:hubsec@localhost/hubsec_multitenant"),
        help="PostgreSQL Database URL"
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed database with sample multi-tenant data"
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing tables before creating (WARNING: destroys data)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Hubsec SOC Platform - Multi-Tenant Database Initialization")
    print("=" * 70)
    print(f"\n📊 Database: {args.database_url}")

    # Validate PostgreSQL
    if "postgresql" not in args.database_url:
        print("\n❌ ERROR: This script requires PostgreSQL!")
        print("The multi-tenant schema uses PostgreSQL-specific types:")
        print("  - UUID, INET, ARRAY, JSONB, TIMESTAMPTZ")
        print("\nFor SQLite testing, use the original init_db.py script.")
        sys.exit(1)

    # Create engine
    engine = create_engine(args.database_url, echo=False)

    # Test connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
    except Exception as e:
        print(f"\n❌ Database connection failed: {e}")
        sys.exit(1)

    # Enable UUID extension
    enable_uuid_extension(engine)

    # Drop tables if requested
    if args.drop:
        print("\n⚠️  Dropping existing tables...")
        Base.metadata.drop_all(bind=engine)
        print("✅ Tables dropped")

    # Create tables
    create_tables(engine)

    # Seed data if requested
    if args.seed:
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        try:
            print("\n🌱 Seeding database with multi-tenant sample data...")

            tenants = seed_tenants(session)
            users = seed_users(session, tenants)
            source_systems = seed_source_systems(session, tenants)
            assets = seed_assets(session, tenants)
            alerts = seed_alerts(session, tenants, source_systems, assets)
            incidents, cases = seed_incidents_and_cases(session, tenants, source_systems, users, alerts, assets)
            playbooks = seed_playbooks(session, tenants)
            seed_comments_and_activities(session, incidents, cases, users)

            print("\n" + "=" * 70)
            print("✅ Multi-Tenant Database Initialization Complete!")
            print("=" * 70)
            print("\n📊 Summary:")
            print(f"  • Tenants: {len(tenants)}")
            print(f"  • Users: {len(users)}")
            print(f"  • Source Systems: {len(source_systems)}")
            print(f"  • Assets: {len(assets)}")
            print(f"  • Alerts: {len(alerts)}")
            print(f"  • Incidents: {len(incidents)}")
            print(f"  • Cases: {len(cases)}")
            print(f"  • Playbooks: {len(playbooks)}")

            print("\n🔐 Default Login Credentials:")
            print("  Hubsec Staff:")
            print("    • Super Admin:  superadmin / admin123")
            print("    • Analyst 1:    hubsec_analyst1 / analyst123")
            print("    • Analyst 2:    hubsec_analyst2 / analyst123")
            print("\n  Tenant Users:")
            print("    • Econet Admin: econet_admin / econet123")
            print("    • PostBank Admin: postbank_admin / postbank123")
            print("    • TelOne Viewer: telone_viewer / telone123")

            print("\n🏢 Tenants:")
            for tenant in tenants:
                print(f"    • {tenant.name} ({tenant.code}) - {tenant.subscription_tier}")

            print("\n🚀 Next Steps:")
            print("  1. Update backend/app/main.py to use models_multitenant")
            print("  2. Implement tenant-aware authentication middleware")
            print("  3. Update API endpoints to filter by tenant_id")
            print("  4. Start the API:")
            print("     uvicorn backend.app.main:app --reload")
            print("\n📝 API Documentation:")
            print("  http://localhost:8000/api/docs")
            print("=" * 70)

        except Exception as e:
            print(f"\n❌ Error during seeding: {e}")
            import traceback
            traceback.print_exc()
            session.rollback()
            sys.exit(1)
        finally:
            session.close()
    else:
        print("\n✅ Database initialized (no seed data)")
        print("Run with --seed to add sample multi-tenant data")


if __name__ == "__main__":
    main()
