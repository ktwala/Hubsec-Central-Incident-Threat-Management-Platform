"""
Users API Endpoints
User management and authentication
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import hashlib

from backend.app.main import get_db
from backend.app.models.models import User, UserRole
from backend.app.schemas import schemas

router = APIRouter()


def hash_password(password: str) -> str:
    """
    Hash a password for storage

    Note: This is a simple implementation for demo purposes.
    In production, use proper password hashing like bcrypt or Argon2
    """
    return hashlib.sha256(password.encode()).hexdigest()


@router.get("/", response_model=List[schemas.User])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    List all users with optional filtering

    Filters:
    - role: Filter by user role
    - is_active: Filter by active status
    - skip/limit: Pagination
    """
    query = db.query(User)

    # Apply filters
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == (1 if is_active else 0))

    # Order by username
    query = query.order_by(User.username)

    # Pagination
    users = query.offset(skip).limit(limit).all()

    return users


@router.get("/{user_id}", response_model=schemas.User)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get a specific user by ID"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.get("/username/{username}", response_model=schemas.User)
def get_user_by_username(username: str, db: Session = Depends(get_db)):
    """Get a user by username"""
    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.post("/", response_model=schemas.User, status_code=201)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new user

    Requirements:
    - Unique username
    - Unique email
    - Password minimum 8 characters
    """
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    db_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        hashed_password=hash_password(user.password),
        is_active=1
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@router.put("/{user_id}", response_model=schemas.User)
def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a user

    Allows updating:
    - Email
    - Full name
    - Role
    - Active status
    """
    db_user = db.query(User).filter(User.id == user_id).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update fields
    update_data = user_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == 'is_active':
            # Convert bool to int for SQLite
            setattr(db_user, field, 1 if value else 0)
        else:
            setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)

    return db_user


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """
    Delete a user

    Warning: This may fail if the user is referenced by incidents/cases
    Consider deactivating instead of deleting
    """
    db_user = db.query(User).filter(User.id == user_id).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        db.delete(db_user)
        db.commit()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete user: {str(e)}. Consider deactivating instead."
        )

    return None


@router.post("/{user_id}/deactivate")
def deactivate_user(user_id: int, db: Session = Depends(get_db)):
    """Deactivate a user account"""
    db_user = db.query(User).filter(User.id == user_id).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.is_active = 0
    db.commit()

    return {"message": f"User {db_user.username} deactivated"}


@router.post("/{user_id}/activate")
def activate_user(user_id: int, db: Session = Depends(get_db)):
    """Activate a user account"""
    db_user = db.query(User).filter(User.id == user_id).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.is_active = 1
    db.commit()

    return {"message": f"User {db_user.username} activated"}


@router.get("/{user_id}/workload")
def get_user_workload(user_id: int, db: Session = Depends(get_db)):
    """
    Get workload statistics for a user

    Returns:
    - Assigned incidents
    - Assigned cases
    - Case statistics
    """
    from backend.app.models.models import Incident, Case, IncidentStatus, CaseStatus

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get assigned incidents
    assigned_incidents = db.query(Incident).filter(
        Incident.assigned_to_id == user_id
    ).all()

    open_incidents = [i for i in assigned_incidents if i.status in [
        IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS
    ]]

    # Get assigned cases
    assigned_cases = user.assigned_cases
    open_cases = [c for c in assigned_cases if c.status in [
        CaseStatus.OPEN, CaseStatus.IN_PROGRESS
    ]]

    # Calculate workload metrics
    total_alerts_in_cases = sum(len(case.alerts) for case in open_cases)

    return {
        "user_id": user_id,
        "username": user.username,
        "total_incidents": len(assigned_incidents),
        "open_incidents": len(open_incidents),
        "total_cases": len(assigned_cases),
        "open_cases": len(open_cases),
        "total_alerts_in_open_cases": total_alerts_in_cases,
        "incidents": [
            {
                "id": i.id,
                "title": i.title,
                "severity": i.severity.value,
                "status": i.status.value,
                "created_at": i.created_at.isoformat()
            }
            for i in open_incidents
        ],
        "cases": [
            {
                "id": c.id,
                "title": c.title,
                "priority": c.priority.value,
                "status": c.status.value,
                "alert_count": len(c.alerts),
                "created_at": c.created_at.isoformat()
            }
            for c in open_cases
        ]
    }


@router.get("/{user_id}/activity")
def get_user_activity(
    user_id: int,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get recent activity for a user

    Returns all activities performed by the user
    """
    from backend.app.models.models import Activity

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    activities = db.query(Activity).filter(
        Activity.user_id == user_id
    ).order_by(Activity.created_at.desc()).limit(limit).all()

    return {
        "user_id": user_id,
        "username": user.username,
        "activity_count": len(activities),
        "activities": [
            {
                "id": a.id,
                "action": a.action,
                "description": a.description,
                "case_id": a.case_id,
                "created_at": a.created_at.isoformat(),
                "metadata": a.metadata
            }
            for a in activities
        ]
    }
