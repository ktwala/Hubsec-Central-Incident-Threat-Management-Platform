"""
Cases API Endpoints
CRUD operations for investigation cases
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from backend.app.database import get_db
from backend.app.models.models import Case, CaseStatus, SeverityLevel, Alert, User, Activity
from backend.app.schemas import schemas
from backend.app.services.case_engine import CaseEngine

router = APIRouter()


@router.get("/", response_model=List[schemas.Case])
def list_cases(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[CaseStatus] = None,
    priority: Optional[SeverityLevel] = None,
    incident_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    List all cases with optional filtering

    Filters:
    - status: Filter by case status
    - priority: Filter by priority level
    - incident_id: Filter by parent incident
    - skip/limit: Pagination
    """
    query = db.query(Case)

    # Apply filters
    if status:
        query = query.filter(Case.status == status)
    if priority:
        query = query.filter(Case.priority == priority)
    if incident_id:
        query = query.filter(Case.incident_id == incident_id)

    # Order by creation date (newest first)
    query = query.order_by(Case.created_at.desc())

    # Pagination
    cases = query.offset(skip).limit(limit).all()

    return cases


@router.get("/{case_id}", response_model=schemas.Case)
def get_case(case_id: int, db: Session = Depends(get_db)):
    """Get a specific case by ID with all related data"""
    case = db.query(Case).filter(Case.id == case_id).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    return case


@router.post("/", response_model=schemas.Case, status_code=201)
def create_case(
    case: schemas.CaseCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new investigation case

    Cases are linked to incidents and can have multiple alerts
    """
    # Verify incident exists
    from backend.app.models.models import Incident
    incident = db.query(Incident).filter(Incident.id == case.incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Create case
    db_case = Case(
        title=case.title,
        description=case.description,
        priority=case.priority,
        status=CaseStatus.OPEN,
        incident_id=case.incident_id,
        tags=case.tags
    )

    db.add(db_case)
    db.flush()  # Get the case ID

    # Assign users if provided
    if case.assigned_user_ids:
        for user_id in case.assigned_user_ids:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                db_case.assigned_users.append(user)

    # Log activity
    activity = Activity(
        case_id=db_case.id,
        user_id=1,  # TODO: Get from authenticated user
        action="case_created",
        description=f"Case '{case.title}' created"
    )
    db.add(activity)

    db.commit()
    db.refresh(db_case)

    return db_case


@router.put("/{case_id}", response_model=schemas.Case)
def update_case(
    case_id: int,
    case_update: schemas.CaseUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing case

    Allows updating:
    - Title, description
    - Status, priority
    - Assignments
    - Resolution notes
    - Tags
    """
    db_case = db.query(Case).filter(Case.id == case_id).first()

    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")

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
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                db_case.assigned_users.append(user)
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
            user_id=1,  # TODO: Get from authenticated user
            action="case_updated",
            description=f"Case updated: {', '.join(changes)}"
        )
        db.add(activity)

    db.commit()
    db.refresh(db_case)

    return db_case


@router.delete("/{case_id}", status_code=204)
def delete_case(case_id: int, db: Session = Depends(get_db)):
    """Delete a case"""
    db_case = db.query(Case).filter(Case.id == case_id).first()

    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")

    db.delete(db_case)
    db.commit()

    return None


@router.post("/{case_id}/alerts")
def add_alerts_to_case(
    case_id: int,
    alert_data: schemas.CaseAddAlerts,
    db: Session = Depends(get_db)
):
    """
    Add one or more alerts to a case

    This endpoint allows analysts to manually correlate alerts to cases
    """
    db_case = db.query(Case).filter(Case.id == case_id).first()

    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")

    added_count = 0
    for alert_id in alert_data.alert_ids:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert and alert not in db_case.alerts:
            db_case.alerts.append(alert)
            alert.status = schemas.AlertStatus.IN_CASE
            added_count += 1

            # Log activity
            activity = Activity(
                case_id=case_id,
                user_id=1,  # TODO: Get from authenticated user
                action="alert_added",
                description=f"Alert {alert_id} added to case",
                metadata={'alert_id': alert_id}
            )
            db.add(activity)

    db_case.updated_at = datetime.utcnow()
    db.commit()

    return {
        "message": f"Added {added_count} alert(s) to case",
        "case_id": case_id,
        "total_alerts": len(db_case.alerts)
    }


@router.delete("/{case_id}/alerts/{alert_id}")
def remove_alert_from_case(
    case_id: int,
    alert_id: int,
    db: Session = Depends(get_db)
):
    """Remove an alert from a case"""
    db_case = db.query(Case).filter(Case.id == case_id).first()

    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")

    alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert in db_case.alerts:
        db_case.alerts.remove(alert)
        alert.status = schemas.AlertStatus.TRIAGED

        # Log activity
        activity = Activity(
            case_id=case_id,
            user_id=1,  # TODO: Get from authenticated user
            action="alert_removed",
            description=f"Alert {alert_id} removed from case"
        )
        db.add(activity)

        db_case.updated_at = datetime.utcnow()
        db.commit()

        return {"message": "Alert removed from case"}
    else:
        raise HTTPException(status_code=400, detail="Alert not in this case")


@router.post("/{case_id}/comments", response_model=schemas.Comment)
def add_comment_to_case(
    case_id: int,
    comment: schemas.CommentCreate,
    db: Session = Depends(get_db)
):
    """Add a comment to a case"""
    from backend.app.models.models import Comment

    # Verify case exists
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Create comment
    db_comment = Comment(
        content=comment.content,
        case_id=case_id,
        author_id=1  # TODO: Get from authenticated user
    )

    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)

    return db_comment


@router.get("/{case_id}/statistics")
def get_case_statistics(case_id: int, db: Session = Depends(get_db)):
    """
    Get detailed statistics and metrics for a case

    Returns:
    - Alert counts and breakdowns
    - Timeline information
    - Unique indicators
    - Case health metrics
    """
    case = db.query(Case).filter(Case.id == case_id).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    engine = CaseEngine(db)
    stats = engine.get_case_statistics(case)

    return stats


@router.post("/{case_id}/escalate")
def escalate_case(case_id: int, db: Session = Depends(get_db)):
    """
    Manually escalate a case

    Changes status to IN_PROGRESS and logs the escalation
    """
    case = db.query(Case).filter(Case.id == case_id).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if case.status == CaseStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Cannot escalate closed case")

    case.status = CaseStatus.IN_PROGRESS

    # Log activity
    activity = Activity(
        case_id=case_id,
        user_id=1,  # TODO: Get from authenticated user
        action="case_escalated",
        description="Case manually escalated"
    )
    db.add(activity)

    db.commit()

    return {"message": "Case escalated", "status": case.status.value}
