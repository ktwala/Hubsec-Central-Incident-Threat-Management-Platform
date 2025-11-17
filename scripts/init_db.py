#!/usr/bin/env python3
"""
Database Initialization Script
Creates tables and optionally seeds with sample data
"""
import sys
import os
from datetime import datetime, timedelta
import random

# Add parent directory to path to import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.models.models import (
    Base, User, Incident, Case, Alert, Comment, Activity,
    UserRole, IncidentStatus, CaseStatus, AlertStatus, SeverityLevel
)
import hashlib


def hash_password(password: str) -> str:
    """Simple password hashing (same as in users.py)"""
    return hashlib.sha256(password.encode()).hexdigest()


def create_tables(engine):
    """Create all database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully")


def seed_users(session):
    """Create sample users"""
    print("\n📝 Seeding users...")

    users = [
        User(
            username="admin",
            email="admin@hubsec.local",
            full_name="System Administrator",
            role=UserRole.ADMIN,
            hashed_password=hash_password("admin123"),
            is_active=1
        ),
        User(
            username="analyst1",
            email="analyst1@hubsec.local",
            full_name="John Analyst",
            role=UserRole.ANALYST,
            hashed_password=hash_password("analyst123"),
            is_active=1
        ),
        User(
            username="analyst2",
            email="analyst2@hubsec.local",
            full_name="Jane Security",
            role=UserRole.ANALYST,
            hashed_password=hash_password("analyst123"),
            is_active=1
        ),
        User(
            username="manager",
            email="manager@hubsec.local",
            full_name="SOC Manager",
            role=UserRole.SOC_MANAGER,
            hashed_password=hash_password("manager123"),
            is_active=1
        ),
        User(
            username="viewer",
            email="viewer@hubsec.local",
            full_name="Read Only User",
            role=UserRole.VIEWER,
            hashed_password=hash_password("viewer123"),
            is_active=1
        )
    ]

    for user in users:
        session.add(user)

    session.commit()
    print(f"✅ Created {len(users)} users")
    return users


def seed_alerts(session):
    """Create sample alerts"""
    print("\n🚨 Seeding alerts...")

    sample_ips = [
        "192.168.1.100", "192.168.1.101", "192.168.1.102",
        "10.0.0.50", "10.0.0.51", "172.16.0.10"
    ]

    sample_hostnames = [
        "web-server-01", "db-server-01", "app-server-01",
        "workstation-05", "workstation-12"
    ]

    alert_templates = [
        {
            "rule_description": "Multiple failed login attempts detected",
            "severity": SeverityLevel.HIGH,
            "category": "authentication",
            "event_type": "authentication_failed"
        },
        {
            "rule_description": "Suspicious network connection detected",
            "severity": SeverityLevel.MEDIUM,
            "category": "network",
            "event_type": "network_connection"
        },
        {
            "rule_description": "Malware detected on endpoint",
            "severity": SeverityLevel.CRITICAL,
            "category": "malware",
            "event_type": "malware_detected"
        },
        {
            "rule_description": "Unauthorized file access attempt",
            "severity": SeverityLevel.MEDIUM,
            "category": "system",
            "event_type": "file_access"
        },
        {
            "rule_description": "SQL injection attempt detected",
            "severity": SeverityLevel.HIGH,
            "category": "web",
            "event_type": "web_attack"
        },
        {
            "rule_description": "Possible data exfiltration detected",
            "severity": SeverityLevel.CRITICAL,
            "category": "intrusion",
            "event_type": "data_transfer"
        },
        {
            "rule_description": "Service stopped unexpectedly",
            "severity": SeverityLevel.LOW,
            "category": "system",
            "event_type": "service_stopped"
        },
        {
            "rule_description": "New user account created",
            "severity": SeverityLevel.INFO,
            "category": "authentication",
            "event_type": "user_created"
        }
    ]

    alerts = []
    for i in range(30):  # Create 30 sample alerts
        template = random.choice(alert_templates)
        timestamp = datetime.utcnow() - timedelta(hours=random.randint(1, 72))

        alert = Alert(
            source="Wazuh",
            source_id=f"wazuh-{i+1000}",
            rule_id=f"{random.randint(1000, 9999)}",
            rule_description=template["rule_description"],
            severity=template["severity"],
            status=random.choice([AlertStatus.NEW, AlertStatus.TRIAGED, AlertStatus.IN_CASE]),
            event_type=template["event_type"],
            category=template["category"],
            timestamp=timestamp,
            src_ip=random.choice(sample_ips),
            dst_ip=random.choice(sample_ips),
            src_port=random.randint(1024, 65535),
            dst_port=random.choice([80, 443, 22, 3389, 3306]),
            protocol=random.choice(["TCP", "UDP", "ICMP"]),
            hostname=random.choice(sample_hostnames),
            agent_id=f"agent-{random.randint(1, 100):03d}",
            agent_name=random.choice(sample_hostnames),
            raw_data={"sample": "data"}
        )
        alerts.append(alert)
        session.add(alert)

    session.commit()
    print(f"✅ Created {len(alerts)} alerts")
    return alerts


def seed_incidents(session, users, alerts):
    """Create sample incidents"""
    print("\n📋 Seeding incidents...")

    incidents = [
        Incident(
            title="Malware Outbreak on Network Segment",
            description="Multiple endpoints reporting malware detections",
            severity=SeverityLevel.CRITICAL,
            status=IncidentStatus.IN_PROGRESS,
            source="Wazuh",
            category="malware",
            assigned_to_id=users[1].id,  # analyst1
            detected_at=datetime.utcnow() - timedelta(hours=12)
        ),
        Incident(
            title="Brute Force Attack Against Web Server",
            description="Multiple failed login attempts from suspicious IPs",
            severity=SeverityLevel.HIGH,
            status=IncidentStatus.OPEN,
            source="Wazuh",
            category="authentication",
            assigned_to_id=users[2].id,  # analyst2
            detected_at=datetime.utcnow() - timedelta(hours=6)
        ),
        Incident(
            title="Suspicious Network Traffic",
            description="Unusual outbound connections detected",
            severity=SeverityLevel.MEDIUM,
            status=IncidentStatus.INVESTIGATING,
            source="Manual",
            category="network",
            assigned_to_id=users[1].id,
            detected_at=datetime.utcnow() - timedelta(hours=24)
        ),
        Incident(
            title="Policy Violation - Unauthorized Software",
            description="Prohibited software detected on user workstation",
            severity=SeverityLevel.LOW,
            status=IncidentStatus.RESOLVED,
            source="Wazuh",
            category="policy_violation",
            resolved_at=datetime.utcnow() - timedelta(hours=2),
            detected_at=datetime.utcnow() - timedelta(hours=48)
        )
    ]

    for incident in incidents:
        session.add(incident)

    session.commit()
    print(f"✅ Created {len(incidents)} incidents")
    return incidents


def seed_cases(session, incidents, users, alerts):
    """Create sample cases"""
    print("\n💼 Seeding cases...")

    # Case 1: Linked to malware incident
    case1 = Case(
        title="Investigate Malware Detection on web-server-01",
        description="Analyze malware sample and determine scope",
        priority=SeverityLevel.CRITICAL,
        status=CaseStatus.IN_PROGRESS,
        incident_id=incidents[0].id
    )
    case1.assigned_users.append(users[1])  # analyst1
    # Add related alerts
    malware_alerts = [a for a in alerts if a.category == "malware"][:5]
    for alert in malware_alerts:
        case1.alerts.append(alert)
        alert.status = AlertStatus.IN_CASE

    # Case 2: Linked to brute force incident
    case2 = Case(
        title="Analyze Brute Force Attack Patterns",
        description="Identify attack source and implement countermeasures",
        priority=SeverityLevel.HIGH,
        status=CaseStatus.OPEN,
        incident_id=incidents[1].id
    )
    case2.assigned_users.append(users[2])  # analyst2
    auth_alerts = [a for a in alerts if a.category == "authentication"][:3]
    for alert in auth_alerts:
        case2.alerts.append(alert)
        alert.status = AlertStatus.IN_CASE

    # Case 3: Network investigation
    case3 = Case(
        title="Network Traffic Analysis",
        description="Review network logs for data exfiltration",
        priority=SeverityLevel.MEDIUM,
        status=CaseStatus.PENDING,
        incident_id=incidents[2].id
    )
    case3.assigned_users.extend([users[1], users[2]])  # Both analysts
    network_alerts = [a for a in alerts if a.category == "network"][:4]
    for alert in network_alerts:
        case3.alerts.append(alert)
        alert.status = AlertStatus.IN_CASE

    cases = [case1, case2, case3]

    for case in cases:
        session.add(case)

    session.flush()  # Get case IDs

    # Add activities to cases
    for case in cases:
        activity = Activity(
            case_id=case.id,
            user_id=users[1].id,
            action="case_created",
            description=f"Case '{case.title}' created and assigned"
        )
        session.add(activity)

    session.commit()
    print(f"✅ Created {len(cases)} cases")
    return cases


def seed_comments(session, incidents, cases, users):
    """Create sample comments"""
    print("\n💬 Seeding comments...")

    comments = [
        Comment(
            content="Initial triage completed. This appears to be a targeted attack.",
            incident_id=incidents[0].id,
            author_id=users[1].id
        ),
        Comment(
            content="Blocked the attacking IP at firewall level. Monitoring for additional attempts.",
            case_id=cases[1].id,
            author_id=users[2].id
        ),
        Comment(
            content="Escalating to SOC manager for review.",
            case_id=cases[0].id,
            author_id=users[1].id
        ),
        Comment(
            content="Collected memory dump for forensic analysis.",
            case_id=cases[0].id,
            author_id=users[1].id
        )
    ]

    for comment in comments:
        session.add(comment)

    session.commit()
    print(f"✅ Created {len(comments)} comments")


def main():
    """Main initialization function"""
    import argparse

    parser = argparse.ArgumentParser(description="Initialize Hubsec database")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", "sqlite:///./hubsec.db"),
        help="Database URL (default: sqlite:///./hubsec.db)"
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed database with sample data"
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing tables before creating (WARNING: destroys data)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Hubsec SOC Platform - Database Initialization")
    print("=" * 60)
    print(f"\n📊 Database: {args.database_url}")

    # Create engine
    engine = create_engine(
        args.database_url,
        connect_args={"check_same_thread": False} if "sqlite" in args.database_url else {}
    )

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
            print("\n🌱 Seeding database with sample data...")

            users = seed_users(session)
            alerts = seed_alerts(session)
            incidents = seed_incidents(session, users, alerts)
            cases = seed_cases(session, incidents, users, alerts)
            seed_comments(session, incidents, cases, users)

            print("\n" + "=" * 60)
            print("✅ Database initialization complete!")
            print("=" * 60)
            print("\n📊 Summary:")
            print(f"  • Users: {len(users)}")
            print(f"  • Alerts: {len(alerts)}")
            print(f"  • Incidents: {len(incidents)}")
            print(f"  • Cases: {len(cases)}")
            print("\n🔐 Default Login Credentials:")
            print("  • Admin:    admin / admin123")
            print("  • Analyst:  analyst1 / analyst123")
            print("  • Manager:  manager / manager123")
            print("\n🚀 Start the API with:")
            print("  uvicorn backend.app.main:app --reload")
            print("\n📝 API Documentation:")
            print("  http://localhost:8000/api/docs")
            print("=" * 60)

        except Exception as e:
            print(f"\n❌ Error during seeding: {e}")
            session.rollback()
            sys.exit(1)
        finally:
            session.close()
    else:
        print("\n✅ Database initialized (no seed data)")
        print("Run with --seed to add sample data")


if __name__ == "__main__":
    main()
