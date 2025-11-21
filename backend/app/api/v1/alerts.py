"""
Alerts API Endpoints (Multi-Tenant)
CRUD operations and webhook for security alerts with tenant isolation
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID

from backend.app.database_multitenant import get_db
from backend.app.models.models_multitenant import Alert, AlertStatus, SeverityLevel, Asset
from backend.app.schemas.schemas_multitenant import (
    Alert as AlertSchema,
    AlertCreate,
    AlertUpdate
)
from backend.app.middleware.tenant import (
    TenantContext,
    get_tenant_context,
    require_auth
)
from backend.app.services.wazuh_normalizer import get_normalizer
from backend.app.services.case_engine import CaseEngine

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/", response_model=List[AlertSchema])
def list_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: Optional[UUID] = None,
    status_filter: Optional[AlertStatus] = Query(None, alias="status"),
    severity: Optional[SeverityLevel] = None,
    source: Optional[str] = None,
    src_ip: Optional[str] = None,
    hostname: Optional[str] = None,
    asset_id: Optional[UUID] = None,
    hours: Optional[int] = Query(None, description="Filter alerts from last N hours"),
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    List all alerts with optional filtering (tenant-aware)

    Filters:
    - tenant_id: Filter by specific tenant (HubSec staff only)
    - status: Filter by alert status
    - severity: Filter by severity level
    - source: Filter by alert source (e.g., 'Wazuh')
    - src_ip: Filter by source IP address
    - hostname: Filter by hostname
    - asset_id: Filter by asset ID
    - hours: Only show alerts from last N hours
    - skip/limit: Pagination

    Access Control:
    - Tenant users see only their tenant's alerts
    - HubSec staff can see all tenants or filter by tenant_id
    """
    query = db.query(Alert).filter(Alert.is_active == True)

    # Tenant filtering
    if context.user:
        if context.is_hubsec_staff():
            # HubSec staff can filter by specific tenant or see all
            if tenant_id:
                query = query.filter(Alert.tenant_id == tenant_id)
        else:
            # Regular users see only their tenant's alerts
            user_tenant_ids = [t.id for t in context.user.tenants]
            query = query.filter(Alert.tenant_id.in_(user_tenant_ids))

    # Apply filters
    if status_filter:
        query = query.filter(Alert.status == status_filter)
    if severity:
        query = query.filter(Alert.severity == severity)
    if source:
        query = query.filter(Alert.source == source)
    if src_ip:
        query = query.filter(Alert.src_ip == src_ip)
    if hostname:
        query = query.filter(Alert.hostname.ilike(f"%{hostname}%"))
    if asset_id:
        query = query.filter(Alert.asset_id == asset_id)
    if hours:
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(Alert.timestamp >= time_threshold)

    # Order by timestamp (newest first)
    query = query.order_by(Alert.timestamp.desc())

    # Pagination
    alerts = query.offset(skip).limit(limit).all()

    return alerts


@router.get("/{alert_id}", response_model=AlertSchema)
def get_alert(
    alert_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get a specific alert by ID (tenant-aware)

    Access Control:
    - Users can only view alerts from their accessible tenants
    """
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.is_active == True
    ).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Check tenant access
    if context.user and not context.can_access_tenant(alert.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's alerts")

    return alert


@router.post("/", response_model=AlertSchema, status_code=status.HTTP_201_CREATED)
def create_alert(
    alert: AlertCreate,
    background_tasks: BackgroundTasks,
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Create a new alert manually

    Note: Most alerts are created automatically via the Wazuh webhook

    Access Control:
    - Users can only create alerts for their accessible tenants
    - HubSec staff can create alerts for any tenant
    """
    # Verify tenant access
    from backend.app.middleware.tenant import get_tenant_context_from_user
    context = get_tenant_context_from_user(user, db)

    if not context.can_access_tenant(alert.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Create alert
    db_alert = Alert(
        tenant_id=alert.tenant_id,
        asset_id=alert.asset_id,
        source=alert.source,
        source_id=alert.source_id,
        rule_id=alert.rule_id,
        rule_description=alert.rule_description,
        severity=alert.severity,
        status=AlertStatus.NEW,
        event_type=alert.event_type,
        category=alert.category,
        timestamp=alert.timestamp or datetime.utcnow(),
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
        normalized_data=alert.normalized_data,
        is_active=True
    )

    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)

    # Process alert for case creation in background
    background_tasks.add_task(process_alert_for_case, db_alert.id, db)

    return db_alert


@router.patch("/{alert_id}", response_model=AlertSchema)
def update_alert(
    alert_id: UUID,
    alert_update: AlertUpdate,
    context: TenantContext = Depends(get_tenant_context),
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Update an alert (tenant-aware)

    Typically used to change status or severity

    Access Control:
    - Users can only update alerts from their accessible tenants
    """
    db_alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.is_active == True
    ).first()

    if not db_alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Check tenant access
    if not context.can_access_tenant(db_alert.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's alerts")

    # Update fields
    update_data = alert_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_alert, field, value)

    db_alert.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_alert)

    return db_alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
    alert_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Delete an alert (soft delete, tenant-aware)

    Access Control:
    - Users can only delete alerts from their accessible tenants
    """
    db_alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.is_active == True
    ).first()

    if not db_alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Check tenant access
    if not context.can_access_tenant(db_alert.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's alerts")

    # Soft delete
    db_alert.is_active = False
    db_alert.updated_at = datetime.utcnow()
    db.commit()

    return None


@router.post("/wazuh/webhook")
async def wazuh_webhook(
    webhook_data: dict,  # Generic dict to accept any Wazuh format
    background_tasks: BackgroundTasks,
    tenant_id: UUID = Query(..., description="Tenant ID for alert routing"),
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint for receiving Wazuh alerts (multi-tenant)

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

    Query Parameters:
    - tenant_id: Required - identifies which tenant this alert belongs to
    """
    normalizer = get_normalizer()
    created_alerts = []

    alerts_list = webhook_data.get("alerts", [webhook_data])

    for wazuh_alert in alerts_list:
        try:
            # Normalize the alert
            normalized = normalizer.normalize_alert(wazuh_alert)

            # Check if alert already exists (based on source_id)
            existing = db.query(Alert).filter(
                Alert.source_id == normalized['source_id'],
                Alert.tenant_id == tenant_id
            ).first()

            if existing:
                print(f"Alert {normalized['source_id']} already exists for tenant {tenant_id}, skipping")
                continue

            # Try to find matching asset by hostname or IP
            asset = None
            if normalized.get('hostname'):
                asset = db.query(Asset).filter(
                    Asset.tenant_id == tenant_id,
                    Asset.hostname == normalized['hostname'],
                    Asset.is_active == True
                ).first()

            if not asset and normalized.get('src_ip'):
                asset = db.query(Asset).filter(
                    Asset.tenant_id == tenant_id,
                    Asset.ip_address == normalized['src_ip'],
                    Asset.is_active == True
                ).first()

            # Create alert in database
            db_alert = Alert(
                tenant_id=tenant_id,
                asset_id=asset.id if asset else None,
                **normalized,
                is_active=True
            )
            db.add(db_alert)
            db.flush()

            created_alerts.append(str(db_alert.id))

            # Update asset last_seen if found
            if asset:
                asset.last_seen = datetime.utcnow()

            # Process alert for automatic case creation in background
            background_tasks.add_task(process_alert_for_case, db_alert.id, db)

        except Exception as e:
            print(f"Error processing alert: {e}")
            # Continue processing other alerts even if one fails
            continue

    db.commit()

    return {
        "status": "success",
        "message": f"Processed {len(alerts_list)} alerts",
        "created": len(created_alerts),
        "alert_ids": created_alerts,
        "tenant_id": str(tenant_id)
    }


def process_alert_for_case(alert_id: UUID, db: Session):
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
    alert_ids: List[UUID],
    new_status: AlertStatus,
    context: TenantContext = Depends(get_tenant_context),
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Bulk update status for multiple alerts (tenant-aware)

    Useful for triaging large numbers of alerts at once

    Access Control:
    - Only updates alerts from user's accessible tenants
    """
    updated_count = 0

    for alert_id in alert_ids:
        alert = db.query(Alert).filter(
            Alert.id == alert_id,
            Alert.is_active == True
        ).first()

        if alert and context.can_access_tenant(alert.tenant_id):
            alert.status = new_status
            alert.updated_at = datetime.utcnow()
            updated_count += 1

    db.commit()

    return {
        "message": f"Updated {updated_count} of {len(alert_ids)} alerts",
        "new_status": new_status.value
    }


@router.get("/search/ip/{ip_address}")
def search_alerts_by_ip(
    ip_address: str,
    days: int = Query(7, description="Search last N days"),
    tenant_id: Optional[UUID] = None,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Search for all alerts related to an IP address (tenant-aware)

    Searches both source and destination IP fields

    Access Control:
    - Tenant users see only their tenant's alerts
    - HubSec staff can filter by tenant_id or see all
    """
    time_threshold = datetime.utcnow() - timedelta(days=days)

    query = db.query(Alert).filter(
        (Alert.src_ip == ip_address) | (Alert.dst_ip == ip_address),
        Alert.timestamp >= time_threshold,
        Alert.is_active == True
    )

    # Tenant filtering
    if context.user:
        if context.is_hubsec_staff():
            if tenant_id:
                query = query.filter(Alert.tenant_id == tenant_id)
        else:
            user_tenant_ids = [t.id for t in context.user.tenants]
            query = query.filter(Alert.tenant_id.in_(user_tenant_ids))

    alerts = query.order_by(Alert.timestamp.desc()).all()

    return {
        "ip_address": ip_address,
        "period_days": days,
        "count": len(alerts),
        "alerts": [
            {
                "id": str(a.id),
                "tenant_id": str(a.tenant_id),
                "timestamp": a.timestamp.isoformat(),
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
    tenant_id: Optional[UUID] = None,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Search for all alerts related to a hostname (tenant-aware)

    Access Control:
    - Tenant users see only their tenant's alerts
    - HubSec staff can filter by tenant_id or see all
    """
    time_threshold = datetime.utcnow() - timedelta(days=days)

    query = db.query(Alert).filter(
        Alert.hostname.ilike(f"%{hostname}%"),
        Alert.timestamp >= time_threshold,
        Alert.is_active == True
    )

    # Tenant filtering
    if context.user:
        if context.is_hubsec_staff():
            if tenant_id:
                query = query.filter(Alert.tenant_id == tenant_id)
        else:
            user_tenant_ids = [t.id for t in context.user.tenants]
            query = query.filter(Alert.tenant_id.in_(user_tenant_ids))

    alerts = query.order_by(Alert.timestamp.desc()).all()

    return {
        "hostname": hostname,
        "period_days": days,
        "count": len(alerts),
        "alerts": [
            {
                "id": str(a.id),
                "tenant_id": str(a.tenant_id),
                "timestamp": a.timestamp.isoformat(),
                "severity": a.severity.value,
                "rule_description": a.rule_description,
                "src_ip": a.src_ip,
                "category": a.category
            }
            for a in alerts
        ]
    }
