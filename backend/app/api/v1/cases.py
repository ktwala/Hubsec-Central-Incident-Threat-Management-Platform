"""
Cases API Endpoints (Multi-Tenant)
CRUD operations for investigation cases with tenant isolation, playbooks, and external references
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from backend.app.database_multitenant import get_db
from backend.app.models.models_multitenant import (
    Case, CaseStatus, SeverityLevel, Alert, User, Activity,
    CasePlaybook, CaseExternalRef, Playbook, ExternalSystem
)
from backend.app.schemas.schemas_multitenant import (
    Case as CaseSchema,
    CaseCreate,
    CaseUpdate,
    CaseAddAlerts,
    Comment as CommentSchema,
    CommentCreate,
    CaseExternalRef as CaseExternalRefSchema,
    CaseExternalRefCreate
)
from backend.app.middleware.tenant import (
    TenantContext,
    get_tenant_context,
    require_auth
)
from backend.app.services.case_engine import CaseEngine

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("/", response_model=List[CaseSchema])
def list_cases(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: Optional[UUID] = None,
    status_filter: Optional[CaseStatus] = Query(None, alias="status"),
    priority: Optional[SeverityLevel] = None,
    incident_id: Optional[UUID] = None,
    assigned_to_id: Optional[UUID] = None,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    List all cases with optional filtering (tenant-aware)

    Filters:
    - tenant_id: Filter by specific tenant (HubSec staff only)
    - status: Filter by case status
    - priority: Filter by priority level
    - incident_id: Filter by parent incident
    - assigned_to_id: Filter by assigned user
    - skip/limit: Pagination

    Access Control:
    - Tenant users see only their tenant's cases
    - HubSec staff can see all tenants or filter by tenant_id
    """
    query = db.query(Case).filter(Case.is_active == True)

    # Tenant filtering
    if context.user:
        if context.is_hubsec_staff():
            # HubSec staff can filter by specific tenant or see all
            if tenant_id:
                query = query.filter(Case.tenant_id == tenant_id)
        else:
            # Regular users see only their tenant's cases
            user_tenant_ids = [t.id for t in context.user.tenants]
            query = query.filter(Case.tenant_id.in_(user_tenant_ids))

    # Apply filters
    if status_filter:
        query = query.filter(Case.status == status_filter)
    if priority:
        query = query.filter(Case.priority == priority)
    if incident_id:
        query = query.filter(Case.incident_id == incident_id)
    if assigned_to_id:
        # Check if user is assigned to case
        query = query.join(Case.assigned_users).filter(User.id == assigned_to_id)

    # Order by creation date (newest first)
    query = query.order_by(Case.created_at.desc())

    # Pagination
    cases = query.offset(skip).limit(limit).all()

    return cases


@router.get("/{case_id}", response_model=CaseSchema)
def get_case(
    case_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get a specific case by ID with all related data (tenant-aware)

    Access Control:
    - Users can only view cases from their accessible tenants
    """
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.is_active == True
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Check tenant access
    if context.user and not context.can_access_tenant(case.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's cases")

    return case


@router.post("/", response_model=CaseSchema, status_code=status.HTTP_201_CREATED)
def create_case(
    case: CaseCreate,
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Create a new investigation case

    Cases are linked to incidents and can have multiple alerts

    Access Control:
    - Users can only create cases for their accessible tenants
    """
    from backend.app.middleware.tenant import get_tenant_context_from_user
    from backend.app.models.models_multitenant import Incident

    context = get_tenant_context_from_user(user, db)

    if not context.can_access_tenant(case.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Verify incident exists if provided
    if case.incident_id:
        incident = db.query(Incident).filter(
            Incident.id == case.incident_id,
            Incident.tenant_id == case.tenant_id,
            Incident.is_active == True
        ).first()
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found for this tenant")

    # Create case
    db_case = Case(
        tenant_id=case.tenant_id,
        title=case.title,
        description=case.description,
        priority=case.priority,
        status=CaseStatus.OPEN,
        incident_id=case.incident_id,
        tags=case.tags or [],
        is_active=True
    )

    db.add(db_case)
    db.flush()  # Get the case ID

    # Assign users if provided
    if case.assigned_user_ids:
        for user_id in case.assigned_user_ids:
            assigned_user = db.query(User).filter(
                User.id == user_id,
                User.is_active == True
            ).first()
            if assigned_user:
                # Verify user has access to this tenant
                user_tenant_ids = [t.id for t in assigned_user.tenants]
                if case.tenant_id in user_tenant_ids:
                    db_case.assigned_users.append(assigned_user)

    # Log activity
    activity = Activity(
        case_id=db_case.id,
        user_id=user.id,
        action="case_created",
        description=f"Case '{case.title}' created",
        is_active=True
    )
    db.add(activity)

    db.commit()
    db.refresh(db_case)

    return db_case


@router.patch("/{case_id}", response_model=CaseSchema)
def update_case(
    case_id: UUID,
    case_update: CaseUpdate,
    context: TenantContext = Depends(get_tenant_context),
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Update an existing case (tenant-aware)

    Allows updating:
    - Title, description
    - Status, priority
    - Assignments
    - Resolution notes
    - Tags

    Access Control:
    - Users can only update cases from their accessible tenants
    """
    db_case = db.query(Case).filter(
        Case.id == case_id,
        Case.is_active == True
    ).first()

    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Check tenant access
    if not context.can_access_tenant(db_case.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's cases")

    # Track what changed for activity log
    changes = []

    # Update fields
    update_data = case_update.model_dump(exclude_unset=True, exclude={'assigned_user_ids'})

    for field, value in update_data.items():
        old_value = getattr(db_case, field)
        if old_value != value:
            setattr(db_case, field, value)
            changes.append(f"{field}: {old_value} → {value}")

    # Update assigned users if provided
    if case_update.assigned_user_ids is not None:
        db_case.assigned_users.clear()
        for user_id in case_update.assigned_user_ids:
            assigned_user = db.query(User).filter(
                User.id == user_id,
                User.is_active == True
            ).first()
            if assigned_user:
                # Verify user has access to this tenant
                user_tenant_ids = [t.id for t in assigned_user.tenants]
                if db_case.tenant_id in user_tenant_ids:
                    db_case.assigned_users.append(assigned_user)
        changes.append(f"Assigned to {len(case_update.assigned_user_ids)} users")

    # Auto-set closed_at when status changes to closed
    if 'status' in update_data:
        if update_data['status'] == CaseStatus.CLOSED and not db_case.closed_at:
            db_case.closed_at = datetime.utcnow()
            changes.append("Case closed")

    db_case.updated_at = datetime.utcnow()

    # Log activity
    if changes:
        activity = Activity(
            case_id=case_id,
            user_id=user.id,
            action="case_updated",
            description=f"Case updated: {', '.join(changes)}",
            is_active=True
        )
        db.add(activity)

    db.commit()
    db.refresh(db_case)

    return db_case


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(
    case_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Delete a case (soft delete, tenant-aware)

    Access Control:
    - Users can only delete cases from their accessible tenants
    """
    db_case = db.query(Case).filter(
        Case.id == case_id,
        Case.is_active == True
    ).first()

    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Check tenant access
    if not context.can_access_tenant(db_case.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's cases")

    # Soft delete
    db_case.is_active = False
    db_case.updated_at = datetime.utcnow()
    db.commit()

    return None


@router.post("/{case_id}/alerts")
def add_alerts_to_case(
    case_id: UUID,
    alert_data: CaseAddAlerts,
    context: TenantContext = Depends(get_tenant_context),
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Add one or more alerts to a case (tenant-aware)

    This endpoint allows analysts to manually correlate alerts to cases

    Access Control:
    - Users can only add alerts to cases from their accessible tenants
    - Alerts must be from the same tenant as the case
    """
    db_case = db.query(Case).filter(
        Case.id == case_id,
        Case.is_active == True
    ).first()

    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Check tenant access
    if not context.can_access_tenant(db_case.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's cases")

    added_count = 0
    for alert_id in alert_data.alert_ids:
        alert = db.query(Alert).filter(
            Alert.id == alert_id,
            Alert.tenant_id == db_case.tenant_id,  # Must be same tenant
            Alert.is_active == True
        ).first()

        if alert and alert not in db_case.alerts:
            db_case.alerts.append(alert)
            from backend.app.models.models_multitenant import AlertStatus
            alert.status = AlertStatus.IN_CASE
            added_count += 1

            # Log activity
            activity = Activity(
                case_id=case_id,
                user_id=user.id,
                action="alert_added",
                description=f"Alert {alert_id} added to case",
                metadata={'alert_id': str(alert_id)},
                is_active=True
            )
            db.add(activity)

    db_case.updated_at = datetime.utcnow()
    db.commit()

    return {
        "message": f"Added {added_count} alert(s) to case",
        "case_id": str(case_id),
        "total_alerts": len(db_case.alerts)
    }


@router.delete("/{case_id}/alerts/{alert_id}")
def remove_alert_from_case(
    case_id: UUID,
    alert_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Remove an alert from a case (tenant-aware)

    Access Control:
    - Users can only modify cases from their accessible tenants
    """
    db_case = db.query(Case).filter(
        Case.id == case_id,
        Case.is_active == True
    ).first()

    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Check tenant access
    if not context.can_access_tenant(db_case.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's cases")

    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.is_active == True
    ).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert in db_case.alerts:
        db_case.alerts.remove(alert)
        from backend.app.models.models_multitenant import AlertStatus
        alert.status = AlertStatus.TRIAGED

        # Log activity
        activity = Activity(
            case_id=case_id,
            user_id=user.id,
            action="alert_removed",
            description=f"Alert {alert_id} removed from case",
            is_active=True
        )
        db.add(activity)

        db_case.updated_at = datetime.utcnow()
        db.commit()

        return {"message": "Alert removed from case"}
    else:
        raise HTTPException(status_code=400, detail="Alert not in this case")


@router.post("/{case_id}/comments", response_model=CommentSchema, status_code=status.HTTP_201_CREATED)
def add_comment_to_case(
    case_id: UUID,
    comment: CommentCreate,
    context: TenantContext = Depends(get_tenant_context),
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Add a comment to a case (tenant-aware)

    Access Control:
    - Users can only comment on cases from their accessible tenants
    """
    from backend.app.models.models_multitenant import Comment

    # Verify case exists and user has access
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.is_active == True
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Check tenant access
    if not context.can_access_tenant(case.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's cases")

    # Create comment
    db_comment = Comment(
        content=comment.content,
        case_id=case_id,
        incident_id=None,
        author_id=user.id,
        is_active=True
    )

    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)

    return db_comment


@router.get("/{case_id}/statistics")
def get_case_statistics(
    case_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get detailed statistics and metrics for a case (tenant-aware)

    Returns:
    - Alert counts and breakdowns
    - Timeline information
    - Unique indicators
    - Case health metrics
    - Playbook execution status

    Access Control:
    - Users can only view statistics for cases from their accessible tenants
    """
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.is_active == True
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Check tenant access
    if context.user and not context.can_access_tenant(case.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's cases")

    engine = CaseEngine(db)
    stats = engine.get_case_statistics(case)

    # Add playbook execution statistics
    playbook_stats = []
    for case_playbook in case.playbooks:
        playbook_stats.append({
            "playbook_id": str(case_playbook.playbook_id),
            "playbook_name": case_playbook.playbook.name if case_playbook.playbook else "Unknown",
            "status": case_playbook.status,
            "current_step": case_playbook.current_step,
            "total_steps": len(case_playbook.playbook.steps) if case_playbook.playbook else 0,
            "started_at": case_playbook.started_at.isoformat() if case_playbook.started_at else None,
            "completed_at": case_playbook.completed_at.isoformat() if case_playbook.completed_at else None
        })

    stats["playbook_executions"] = playbook_stats

    # Add external references
    external_refs = []
    for ref in case.external_refs:
        if ref.is_active:
            external_refs.append({
                "system": ref.system.value,
                "external_id": ref.external_id,
                "url": ref.url,
                "synced_at": ref.synced_at.isoformat() if ref.synced_at else None
            })

    stats["external_references"] = external_refs

    return stats


@router.post("/{case_id}/escalate")
def escalate_case(
    case_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Manually escalate a case (tenant-aware)

    Changes status to IN_PROGRESS and logs the escalation

    Access Control:
    - Users can only escalate cases from their accessible tenants
    """
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.is_active == True
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Check tenant access
    if not context.can_access_tenant(case.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's cases")

    if case.status == CaseStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Cannot escalate closed case")

    case.status = CaseStatus.IN_PROGRESS
    case.updated_at = datetime.utcnow()

    # Log activity
    activity = Activity(
        case_id=case_id,
        user_id=user.id,
        action="case_escalated",
        description="Case manually escalated",
        is_active=True
    )
    db.add(activity)

    db.commit()

    return {"message": "Case escalated", "status": case.status.value}


@router.post("/{case_id}/playbooks/{playbook_id}/attach")
def attach_playbook_to_case(
    case_id: UUID,
    playbook_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Attach a playbook to a case and start execution (tenant-aware)

    Access Control:
    - Users can only attach playbooks to cases from their accessible tenants
    - Can attach global playbooks or tenant-specific playbooks
    """
    # Verify case exists and user has access
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.is_active == True
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if not context.can_access_tenant(case.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's cases")

    # Verify playbook exists
    playbook = db.query(Playbook).filter(
        Playbook.id == playbook_id,
        Playbook.is_active == True
    ).first()

    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")

    # Check if playbook is accessible (global or same tenant)
    if playbook.tenant_id is not None and playbook.tenant_id != case.tenant_id:
        raise HTTPException(status_code=403, detail="Playbook not accessible for this tenant")

    # Check if already attached
    existing = db.query(CasePlaybook).filter(
        CasePlaybook.case_id == case_id,
        CasePlaybook.playbook_id == playbook_id,
        CasePlaybook.is_active == True
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Playbook already attached to this case")

    # Create case playbook execution
    case_playbook = CasePlaybook(
        case_id=case_id,
        playbook_id=playbook_id,
        status="pending",
        current_step=0,
        completed_steps=[],
        started_at=datetime.utcnow(),
        is_active=True
    )

    db.add(case_playbook)

    # Log activity
    activity = Activity(
        case_id=case_id,
        user_id=user.id,
        action="playbook_attached",
        description=f"Playbook '{playbook.name}' attached to case",
        metadata={"playbook_id": str(playbook_id)},
        is_active=True
    )
    db.add(activity)

    db.commit()
    db.refresh(case_playbook)

    return {
        "message": "Playbook attached successfully",
        "case_playbook_id": str(case_playbook.id),
        "playbook_name": playbook.name,
        "total_steps": len(playbook.steps)
    }


@router.get("/{case_id}/playbooks")
def get_case_playbooks(
    case_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get all playbooks attached to a case (tenant-aware)

    Access Control:
    - Users can only view playbooks for cases from their accessible tenants
    """
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.is_active == True
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if context.user and not context.can_access_tenant(case.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's cases")

    playbooks = []
    for case_playbook in case.playbooks:
        if case_playbook.is_active:
            playbooks.append({
                "id": str(case_playbook.id),
                "playbook_id": str(case_playbook.playbook_id),
                "playbook_name": case_playbook.playbook.name if case_playbook.playbook else "Unknown",
                "status": case_playbook.status,
                "current_step": case_playbook.current_step,
                "total_steps": len(case_playbook.playbook.steps) if case_playbook.playbook else 0,
                "completed_steps": case_playbook.completed_steps,
                "started_at": case_playbook.started_at.isoformat() if case_playbook.started_at else None,
                "completed_at": case_playbook.completed_at.isoformat() if case_playbook.completed_at else None
            })

    return {"case_id": str(case_id), "playbooks": playbooks}


@router.post("/{case_id}/external-refs", response_model=CaseExternalRefSchema, status_code=status.HTTP_201_CREATED)
def create_external_reference(
    case_id: UUID,
    external_ref: CaseExternalRefCreate,
    context: TenantContext = Depends(get_tenant_context),
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Create an external system reference for a case (IRIS, Jira, etc.)

    Access Control:
    - Users can only create references for cases from their accessible tenants
    """
    # Verify case exists and user has access
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.is_active == True
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if not context.can_access_tenant(case.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's cases")

    # Create external reference
    db_ref = CaseExternalRef(
        case_id=case_id,
        system=external_ref.system,
        external_id=external_ref.external_id,
        url=external_ref.url,
        metadata=external_ref.metadata,
        is_active=True
    )

    db.add(db_ref)

    # Log activity
    activity = Activity(
        case_id=case_id,
        user_id=user.id,
        action="external_ref_created",
        description=f"External reference created: {external_ref.system.value} #{external_ref.external_id}",
        metadata={"system": external_ref.system.value, "external_id": external_ref.external_id},
        is_active=True
    )
    db.add(activity)

    db.commit()
    db.refresh(db_ref)

    return db_ref


@router.get("/{case_id}/external-refs")
def list_external_references(
    case_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    List all external system references for a case

    Access Control:
    - Users can only view references for cases from their accessible tenants
    """
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.is_active == True
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if context.user and not context.can_access_tenant(case.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied to this tenant's cases")

    external_refs = []
    for ref in case.external_refs:
        if ref.is_active:
            external_refs.append({
                "id": str(ref.id),
                "system": ref.system.value,
                "external_id": ref.external_id,
                "url": ref.url,
                "metadata": ref.metadata,
                "synced_at": ref.synced_at.isoformat() if ref.synced_at else None,
                "created_at": ref.created_at.isoformat()
            })

    return {"case_id": str(case_id), "external_references": external_refs}
