"""
Alerts API Endpoints
CRUD operations and webhook for security alerts
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from backend.app.database import get_db
from backend.app.models.models import Alert, AlertStatus, SeverityLevel
from backend.app.schemas import schemas
from backend.app.services.wazuh_normalizer import get_normalizer
from backend.app.services.case_engine import CaseEngine

router = APIRouter()


@router.get("/", response_model=List[schemas.Alert])
def list_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[AlertStatus] = None,
    severity: Optional[SeverityLevel] = None,
    source: Optional[str] = None,
    src_ip: Optional[str] = None,
    hostname: Optional[str] = None,
    hours: Optional[int] = Query(None, description="Filter alerts from last N hours"),
    db: Session = Depends(get_db)
):
    """
    List all alerts with optional filtering

    Filters:
    - status: Filter by alert status
    - severity: Filter by severity level
    - source: Filter by alert source (e.g., 'Wazuh')
    - src_ip: Filter by source IP address
    - hostname: Filter by hostname
    - hours: Only show alerts from last N hours
    - skip/limit: Pagination
    """
    query = db.query(Alert)

    # Apply filters
    if status:
        query = query.filter(Alert.status == status)
    if severity:
        query = query.filter(Alert.severity == severity)
    if source:
        query = query.filter(Alert.source == source)
    if src_ip:
        query = query.filter(Alert.src_ip == src_ip)
    if hostname:
        query = query.filter(Alert.hostname == hostname)
    if hours:
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(Alert.timestamp >= time_threshold)

    # Order by timestamp (newest first)
    query = query.order_by(Alert.timestamp.desc())

    # Pagination
    alerts = query.offset(skip).limit(limit).all()

    return alerts


@router.get("/{alert_id}", response_model=schemas.Alert)
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    """Get a specific alert by ID"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert


@router.post("/", response_model=schemas.Alert, status_code=201)
def create_alert(
    alert: schemas.AlertCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a new alert manually

    Note: Most alerts are created automatically via the Wazuh webhook
    """
    db_alert = Alert(
        source=alert.source,
        source_id=alert.source_id,
        rule_id=alert.rule_id,
        rule_description=alert.rule_description,
        severity=alert.severity,
        status=AlertStatus.NEW,
        event_type=alert.event_type,
        category=alert.category,
        timestamp=alert.timestamp,
        src_ip=alert.src_ip,
        dst_ip=alert.dst_ip,
        src_port=alert.src_port,
        dst_port=alert.dst_port,
        protocol=alert.protocol,
        hostname=alert.hostname,
        agent_id=alert.agent_id,
        agent_name=alert.agent_name,
        username=alert.username,
        filename=alert.filename,
        file_path=alert.file_path,
        file_hash=alert.file_hash,
        raw_data=alert.raw_data,
        normalized_data=alert.normalized_data
    )

    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)

    # Process alert for case creation in background
    background_tasks.add_task(process_alert_for_case, db_alert.id, db)

    return db_alert


@router.put("/{alert_id}", response_model=schemas.Alert)
def update_alert(
    alert_id: int,
    alert_update: schemas.AlertUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an alert

    Typically used to change status or severity
    """
    db_alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if not db_alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Update fields
    update_data = alert_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_alert, field, value)

    db.commit()
    db.refresh(db_alert)

    return db_alert


@router.delete("/{alert_id}", status_code=204)
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    """Delete an alert"""
    db_alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if not db_alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    db.delete(db_alert)
    db.commit()

    return None


@router.post("/wazuh/webhook")
async def wazuh_webhook(
    webhook_data: schemas.WazuhWebhook,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint for receiving Wazuh alerts

    This is the main entry point for alerts from Wazuh.
    Alerts are normalized, stored, and automatically processed for case creation.

    Expected payload format:
    {
        "alerts": [
            {
                "timestamp": "2024-01-15T10:30:45.123+0000",
                "rule": {...},
                "agent": {...},
                "data": {...},
                ...
            }
        ]
    }
    """
    normalizer = get_normalizer()
    created_alerts = []

    for wazuh_alert in webhook_data.alerts:
        try:
            # Convert to dict
            alert_dict = wazuh_alert.model_dump()

            # Normalize the alert
            normalized = normalizer.normalize_alert(alert_dict)

            # Check if alert already exists (based on source_id)
            existing = db.query(Alert).filter(
                Alert.source_id == normalized['source_id']
            ).first()

            if existing:
                print(f"Alert {normalized['source_id']} already exists, skipping")
                continue

            # Create alert in database
            db_alert = Alert(**normalized)
            db.add(db_alert)
            db.flush()

            created_alerts.append(db_alert.id)

            # Process alert for automatic case creation in background
            background_tasks.add_task(process_alert_for_case, db_alert.id, db)

        except Exception as e:
            print(f"Error processing alert: {e}")
            # Continue processing other alerts even if one fails
            continue

    db.commit()

    return {
        "status": "success",
        "message": f"Processed {len(webhook_data.alerts)} alerts",
        "created": len(created_alerts),
        "alert_ids": created_alerts
    }


def process_alert_for_case(alert_id: int, db: Session):
    """
    Background task to process an alert for automatic case creation

    This runs the case engine logic to determine if a case should be created
    """
    try:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return

        engine = CaseEngine(db)
        case = engine.process_new_alert(alert)

        if case:
            print(f"Alert {alert_id} created/added to case {case.id}")
        else:
            print(f"Alert {alert_id} did not trigger case creation")

    except Exception as e:
        print(f"Error processing alert {alert_id} for case: {e}")


@router.post("/bulk-triage")
def bulk_triage_alerts(
    alert_ids: List[int],
    new_status: AlertStatus,
    db: Session = Depends(get_db)
):
    """
    Bulk update status for multiple alerts

    Useful for triaging large numbers of alerts at once
    """
    updated_count = 0

    for alert_id in alert_ids:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.status = new_status
            updated_count += 1

    db.commit()

    return {
        "message": f"Updated {updated_count} alerts",
        "new_status": new_status.value
    }


@router.get("/search/ip/{ip_address}")
def search_alerts_by_ip(
    ip_address: str,
    days: int = Query(7, description="Search last N days"),
    db: Session = Depends(get_db)
):
    """
    Search for all alerts related to an IP address

    Searches both source and destination IP fields
    """
    time_threshold = datetime.utcnow() - timedelta(days=days)

    alerts = db.query(Alert).filter(
        (Alert.src_ip == ip_address) | (Alert.dst_ip == ip_address),
        Alert.timestamp >= time_threshold
    ).order_by(Alert.timestamp.desc()).all()

    return {
        "ip_address": ip_address,
        "period_days": days,
        "count": len(alerts),
        "alerts": [
            {
                "id": a.id,
                "timestamp": a.timestamp,
                "severity": a.severity.value,
                "rule_description": a.rule_description,
                "src_ip": a.src_ip,
                "dst_ip": a.dst_ip,
                "hostname": a.hostname
            }
            for a in alerts
        ]
    }


@router.get("/search/hostname/{hostname}")
def search_alerts_by_hostname(
    hostname: str,
    days: int = Query(7, description="Search last N days"),
    db: Session = Depends(get_db)
):
    """Search for all alerts related to a hostname"""
    time_threshold = datetime.utcnow() - timedelta(days=days)

    alerts = db.query(Alert).filter(
        Alert.hostname == hostname,
        Alert.timestamp >= time_threshold
    ).order_by(Alert.timestamp.desc()).all()

    return {
        "hostname": hostname,
        "period_days": days,
        "count": len(alerts),
        "alerts": [
            {
                "id": a.id,
                "timestamp": a.timestamp,
                "severity": a.severity.value,
                "rule_description": a.rule_description,
                "src_ip": a.src_ip,
                "category": a.category
            }
            for a in alerts
        ]
    }
