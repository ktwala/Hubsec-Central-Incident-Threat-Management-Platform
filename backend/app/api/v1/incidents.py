"""
Incidents API Endpoints
CRUD operations for security incidents
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from backend.app.main import get_db
from backend.app.models.models import Incident, IncidentStatus, SeverityLevel
from backend.app.schemas import schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.Incident])
def list_incidents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[IncidentStatus] = None,
    severity: Optional[SeverityLevel] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all incidents with optional filtering

    Filters:
    - status: Filter by incident status
    - severity: Filter by severity level
    - category: Filter by category
    - skip/limit: Pagination
    """
    query = db.query(Incident)

    # Apply filters
    if status:
        query = query.filter(Incident.status == status)
    if severity:
        query = query.filter(Incident.severity == severity)
    if category:
        query = query.filter(Incident.category == category)

    # Order by creation date (newest first)
    query = query.order_by(Incident.created_at.desc())

    # Pagination
    incidents = query.offset(skip).limit(limit).all()

    return incidents


@router.get("/{incident_id}", response_model=schemas.Incident)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    """Get a specific incident by ID"""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()

    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    return incident


@router.post("/", response_model=schemas.Incident, status_code=201)
def create_incident(
    incident: schemas.IncidentCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new incident

    This endpoint allows manual creation of incidents.
    Incidents can also be auto-created from high-severity alerts.
    """
    db_incident = Incident(
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
        tags=incident.tags
    )

    db.add(db_incident)
    db.commit()
    db.refresh(db_incident)

    return db_incident


@router.put("/{incident_id}", response_model=schemas.Incident)
def update_incident(
    incident_id: int,
    incident_update: schemas.IncidentUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing incident

    Allows updating:
    - Title, description
    - Status, severity
    - Assignment
    - Categories and tags
    """
    db_incident = db.query(Incident).filter(Incident.id == incident_id).first()

    if not db_incident:
        raise HTTPException(status_code=404, detail="Incident not found")

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


@router.delete("/{incident_id}", status_code=204)
def delete_incident(incident_id: int, db: Session = Depends(get_db)):
    """
    Delete an incident

    Warning: This will also delete all associated cases and their data
    due to cascade delete rules.
    """
    db_incident = db.query(Incident).filter(Incident.id == incident_id).first()

    if not db_incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    db.delete(db_incident)
    db.commit()

    return None


@router.post("/{incident_id}/comments", response_model=schemas.Comment)
def add_comment_to_incident(
    incident_id: int,
    comment: schemas.CommentCreate,
    db: Session = Depends(get_db)
):
    """Add a comment to an incident"""
    from backend.app.models.models import Comment

    # Verify incident exists
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Create comment (using user_id=1 as default - should be from auth)
    db_comment = Comment(
        content=comment.content,
        incident_id=incident_id,
        author_id=1  # TODO: Get from authenticated user
    )

    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)

    return db_comment


@router.get("/{incident_id}/timeline")
def get_incident_timeline(incident_id: int, db: Session = Depends(get_db)):
    """
    Get timeline of all events related to an incident

    Includes:
    - Incident creation and updates
    - Case activities
    - Comments
    - Alert additions
    """
    from backend.app.models.models import Case, Activity, Comment

    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    timeline = []

    # Add incident creation
    timeline.append({
        "timestamp": incident.created_at,
        "type": "incident_created",
        "description": f"Incident created: {incident.title}",
        "severity": incident.severity.value
    })

    # Add all case activities
    for case in incident.cases:
        for activity in case.activities:
            timeline.append({
                "timestamp": activity.created_at,
                "type": "case_activity",
                "description": activity.description,
                "case_id": case.id,
                "case_title": case.title
            })

    # Add comments
    for comment in incident.comments:
        timeline.append({
            "timestamp": comment.created_at,
            "type": "comment",
            "description": comment.content,
            "author_id": comment.author_id
        })

    # Sort by timestamp
    timeline.sort(key=lambda x: x["timestamp"], reverse=True)

    return {
        "incident_id": incident_id,
        "incident_title": incident.title,
        "timeline": timeline
    }
