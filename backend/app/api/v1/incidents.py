"""
Incidents API Endpoints (Multi-Tenant)
CRUD operations for security incidents with tenant isolation
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from backend.app.database_multitenant import get_db
from backend.app.models.models_multitenant import Incident, IncidentStatus, SeverityLevel, Comment
from backend.app.schemas.schemas_multitenant import (
    Incident as IncidentSchema,
    IncidentCreate,
    IncidentUpdate,
    Comment as CommentSchema,
    CommentCreate
)
from backend.app.middleware.tenant import (
    TenantContext,
    get_tenant_context,
    require_auth
)

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("/", response_model=List[IncidentSchema])
def list_incidents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: Optional[UUID] = None,
    status_filter: Optional[IncidentStatus] = Query(None, alias="status"),
    severity: Optional[SeverityLevel] = None,
    category: Optional[str] = None,
    assigned_to_id: Optional[UUID] = None,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    List all incidents with optional filtering (tenant-aware)

    Filters:
    - tenant_id: Filter by specific tenant (HubSec staff only)
    - status: Filter by incident status
    - severity: Filter by severity level
    - category: Filter by category
    - assigned_to_id: Filter by assigned user
    - skip/limit: Pagination

    Access Control:
    - Tenant users see only their tenant's incidents
    - HubSec staff can see all tenants or filter by tenant_id
    """
    query = db.query(Incident).filter(Incident.is_active == True)

    # Tenant filtering
    if context.user:
        if context.is_hubsec_staff():
            # HubSec staff can filter by specific tenant or see all
            if tenant_id:
                query = query.filter(Incident.tenant_id == tenant_id)
        else:
            # Regular users see only their tenant's incidents
            user_tenant_ids = [t.id for t in context.user.tenants]
            query = query.filter(Incident.tenant_id.in_(user_tenant_ids))

    # Apply filters
    if status_filter:
        query = query.filter(Incident.status == status_filter)
    if severity:
        query = query.filter(Incident.severity == severity)
    if category:
        query = query.filter(Incident.category == category)
    if assigned_to_id:
        query = query.filter(Incident.assigned_to_id == assigned_to_id)

    # Order by creation date (newest first)
    query = query.order_by(Incident.created_at.desc())

    # Pagination
    incidents = query.offset(skip).limit(limit).all()

    return incidents


@router.get("/{incident_id}", response_model=IncidentSchema)
def get_incident(
    incident_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get a specific incident by ID (tenant-aware)

    Access Control:
    - Users can only view incidents from their accessible tenants
    """
    incident = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.is_active == True
    ).first()

    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Check tenant access
    if context.user and not context.can_access_tenant(incident.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's incidents")

    return incident


@router.post("/", response_model=IncidentSchema, status_code=status.HTTP_201_CREATED)
def create_incident(
    incident: IncidentCreate,
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Create a new incident

    This endpoint allows manual creation of incidents.
    Incidents can also be auto-created from high-severity alerts.

    Access Control:
    - Users can only create incidents for their accessible tenants
    """
    from backend.app.middleware.tenant import get_tenant_context_from_user
    context = get_tenant_context_from_user(user, db)

    if not context.can_access_tenant(incident.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    db_incident = Incident(
        tenant_id=incident.tenant_id,
        title=incident.title,
        description=incident.description,
        severity=incident.severity,
        status=IncidentStatus.OPEN,
        source=incident.source,
        source_id=incident.source_id,
        category=incident.category,
        subcategory=incident.subcategory,
        assigned_to_id=incident.assigned_to_id,
        detected_at=incident.detected_at or datetime.utcnow(),
        tags=incident.tags or [],
        is_active=True
    )

    db.add(db_incident)
    db.commit()
    db.refresh(db_incident)

    return db_incident


@router.patch("/{incident_id}", response_model=IncidentSchema)
def update_incident(
    incident_id: UUID,
    incident_update: IncidentUpdate,
    context: TenantContext = Depends(get_tenant_context),
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Update an existing incident (tenant-aware)

    Allows updating:
    - Title, description
    - Status, severity
    - Assignment
    - Categories and tags

    Access Control:
    - Users can only update incidents from their accessible tenants
    """
    db_incident = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.is_active == True
    ).first()

    if not db_incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Check tenant access
    if not context.can_access_tenant(db_incident.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's incidents")

    # Update fields if provided
    update_data = incident_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_incident, field, value)

    # Auto-set resolved_at when status changes to resolved/closed
    if 'status' in update_data:
        if update_data['status'] in [IncidentStatus.RESOLVED, IncidentStatus.CLOSED]:
            if not db_incident.resolved_at:
                db_incident.resolved_at = datetime.utcnow()

    db_incident.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(db_incident)

    return db_incident


@router.delete("/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_incident(
    incident_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Delete an incident (soft delete, tenant-aware)

    Warning: This will also soft-delete all associated cases

    Access Control:
    - Users can only delete incidents from their accessible tenants
    """
    db_incident = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.is_active == True
    ).first()

    if not db_incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Check tenant access
    if not context.can_access_tenant(db_incident.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's incidents")

    # Soft delete
    db_incident.is_active = False
    db_incident.updated_at = datetime.utcnow()

    # Also soft delete associated cases
    from backend.app.models.models_multitenant import Case
    for case in db_incident.cases:
        if case.is_active:
            case.is_active = False
            case.updated_at = datetime.utcnow()

    db.commit()

    return None


@router.post("/{incident_id}/comments", response_model=CommentSchema, status_code=status.HTTP_201_CREATED)
def add_comment_to_incident(
    incident_id: UUID,
    comment: CommentCreate,
    context: TenantContext = Depends(get_tenant_context),
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Add a comment to an incident (tenant-aware)

    Access Control:
    - Users can only comment on incidents from their accessible tenants
    """
    # Verify incident exists and user has access
    incident = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.is_active == True
    ).first()

    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Check tenant access
    if not context.can_access_tenant(incident.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's incidents")

    # Create comment
    db_comment = Comment(
        content=comment.content,
        incident_id=incident_id,
        case_id=None,
        author_id=user.id,
        is_active=True
    )

    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)

    return db_comment


@router.get("/{incident_id}/timeline")
def get_incident_timeline(
    incident_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get timeline of all events related to an incident (tenant-aware)

    Includes:
    - Incident creation and updates
    - Case activities
    - Comments
    - Alert additions

    Access Control:
    - Users can only view timeline for incidents from their accessible tenants
    """
    from backend.app.models.models_multitenant import Case, Activity

    incident = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.is_active == True
    ).first()

    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Check tenant access
    if context.user and not context.can_access_tenant(incident.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's incidents")

    timeline = []

    # Add incident creation
    timeline.append({
        "timestamp": incident.created_at.isoformat(),
        "type": "incident_created",
        "description": f"Incident created: {incident.title}",
        "severity": incident.severity.value
    })

    # Add all case activities
    for case in incident.cases:
        if case.is_active:
            for activity in case.activities:
                if activity.is_active:
                    timeline.append({
                        "timestamp": activity.created_at.isoformat(),
                        "type": "case_activity",
                        "description": activity.description,
                        "case_id": str(case.id),
                        "case_title": case.title
                    })

    # Add comments
    for comment in incident.comments:
        if comment.is_active:
            timeline.append({
                "timestamp": comment.created_at.isoformat(),
                "type": "comment",
                "description": comment.content,
                "author_id": str(comment.author_id) if comment.author_id else None
            })

    # Sort by timestamp (newest first)
    timeline.sort(key=lambda x: x["timestamp"], reverse=True)

    return {
        "incident_id": str(incident_id),
        "incident_title": incident.title,
        "tenant_id": str(incident.tenant_id),
        "timeline": timeline
    }


@router.get("/{incident_id}/statistics")
def get_incident_statistics(
    incident_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get statistics for an incident (tenant-aware)

    Returns:
    - Number of cases
    - Number of alerts
    - Case status breakdown
    - Alert severity breakdown

    Access Control:
    - Users can only view statistics for incidents from their accessible tenants
    """
    from backend.app.models.models_multitenant import Case
    from sqlalchemy import func

    incident = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.is_active == True
    ).first()

    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Check tenant access
    if context.user and not context.can_access_tenant(incident.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's incidents")

    # Count cases
    total_cases = db.query(func.count(Case.id)).filter(
        Case.incident_id == incident_id,
        Case.is_active == True
    ).scalar()

    # Count alerts across all cases
    total_alerts = 0
    for case in incident.cases:
        if case.is_active:
            total_alerts += len([a for a in case.alerts if a.is_active])

    # Case status breakdown
    case_status_counts = {}
    for case in incident.cases:
        if case.is_active:
            status_value = case.status.value
            case_status_counts[status_value] = case_status_counts.get(status_value, 0) + 1

    return {
        "incident_id": str(incident_id),
        "tenant_id": str(incident.tenant_id),
        "total_cases": total_cases,
        "total_alerts": total_alerts,
        "case_status_breakdown": case_status_counts,
        "incident_status": incident.status.value,
        "incident_severity": incident.severity.value,
        "created_at": incident.created_at.isoformat(),
        "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None
    }
