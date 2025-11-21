"""
Users API Endpoints (Multi-Tenant)
User management with multi-tenant access and role-based access control
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from uuid import UUID
import hashlib

from backend.app.database_multitenant import get_db
from backend.app.models.models_multitenant import User, UserRole, Tenant, Incident, Case, IncidentStatus, CaseStatus, Activity
from backend.app.schemas.schemas_multitenant import (
    User as UserSchema,
    UserCreate,
    UserUpdate
)
from backend.app.middleware.tenant import (
    TenantContext,
    get_tenant_context,
    require_auth,
    require_super_admin,
    require_hubsec_staff
)

router = APIRouter(prefix="/users", tags=["users"])


def hash_password(password: str) -> str:
    """
    Hash a password for storage

    Note: This is a simple implementation for demo purposes.
    In production, use proper password hashing like bcrypt or Argon2
    """
    return hashlib.sha256(password.encode()).hexdigest()


@router.get("/", response_model=List[UserSchema])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: Optional[UUID] = None,
    role: Optional[UserRole] = None,
    active_only: bool = True,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    List all users with optional filtering (tenant-aware)

    Filters:
    - tenant_id: Filter by tenant membership (HubSec staff only)
    - role: Filter by user role
    - active_only: Show only active users (default True)
    - skip/limit: Pagination

    Access Control:
    - HubSec staff can see all users or filter by tenant
    - Tenant admins see users from their tenants
    - Regular users see users from their tenants
    """
    query = db.query(User)

    if active_only:
        query = query.filter(User.is_active == True)

    # Tenant filtering
    if context.user:
        if context.is_hubsec_staff():
            # HubSec staff can filter by specific tenant or see all
            if tenant_id:
                query = query.join(User.tenants).filter(Tenant.id == tenant_id)
        else:
            # Regular users see only users from their tenants
            user_tenant_ids = [t.id for t in context.user.tenants]
            query = query.join(User.tenants).filter(Tenant.id.in_(user_tenant_ids))

    # Apply filters
    if role:
        query = query.filter(User.role == role)

    # Order by username
    query = query.order_by(User.username)

    # Pagination (use distinct to handle many-to-many join duplicates)
    users = query.distinct().offset(skip).limit(limit).all()

    return users


@router.get("/{user_id}", response_model=UserSchema)
def get_user(
    user_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get a specific user by ID (tenant-aware)

    Access Control:
    - HubSec staff can view any user
    - Tenant users can view users from their tenants
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check access
    if context.user and not context.is_hubsec_staff():
        # Check if the requested user shares any tenant with current user
        current_user_tenant_ids = {t.id for t in context.user.tenants}
        target_user_tenant_ids = {t.id for t in user.tenants}

        if not current_user_tenant_ids.intersection(target_user_tenant_ids):
            raise HTTPException(status_code=403, detail="Access denied to this user")

    return user


@router.get("/username/{username}", response_model=UserSchema)
def get_user_by_username(
    username: str,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get a user by username (tenant-aware)

    Access Control:
    - HubSec staff can view any user
    - Tenant users can view users from their tenants
    """
    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check access
    if context.user and not context.is_hubsec_staff():
        # Check if the requested user shares any tenant with current user
        current_user_tenant_ids = {t.id for t in context.user.tenants}
        target_user_tenant_ids = {t.id for t in user.tenants}

        if not current_user_tenant_ids.intersection(target_user_tenant_ids):
            raise HTTPException(status_code=403, detail="Access denied to this user")

    return user


@router.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    admin = Depends(require_hubsec_staff),
    db: Session = Depends(get_db)
):
    """
    Create a new user

    Requirements:
    - Unique username
    - Unique email
    - Password minimum 8 characters

    Access Control:
    - Only HubSec staff can create users
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
        is_active=True
    )

    db.add(db_user)
    db.flush()  # Get user ID

    # Assign to tenants if provided
    if user.tenant_ids:
        for tenant_id in user.tenant_ids:
            tenant = db.query(Tenant).filter(
                Tenant.id == tenant_id,
                Tenant.is_active == True
            ).first()
            if tenant:
                db_user.tenants.append(tenant)

    db.commit()
    db.refresh(db_user)

    return db_user


@router.patch("/{user_id}", response_model=UserSchema)
def update_user(
    user_id: UUID,
    user_update: UserUpdate,
    context: TenantContext = Depends(get_tenant_context),
    admin = Depends(require_hubsec_staff),
    db: Session = Depends(get_db)
):
    """
    Update a user

    Allows updating:
    - Email
    - Full name
    - Role
    - Active status
    - Tenant assignments

    Access Control:
    - Only HubSec staff can update users
    """
    db_user = db.query(User).filter(User.id == user_id).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update fields
    update_data = user_update.model_dump(exclude_unset=True, exclude={'tenant_ids'})

    for field, value in update_data.items():
        setattr(db_user, field, value)

    # Update tenant assignments if provided
    if user_update.tenant_ids is not None:
        db_user.tenants.clear()
        for tenant_id in user_update.tenant_ids:
            tenant = db.query(Tenant).filter(
                Tenant.id == tenant_id,
                Tenant.is_active == True
            ).first()
            if tenant:
                db_user.tenants.append(tenant)

    db_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_user)

    return db_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    admin = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a user (soft delete)

    Access Control:
    - Only super admins can delete users
    """
    db_user = db.query(User).filter(User.id == user_id).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Soft delete
    db_user.is_active = False
    db_user.updated_at = datetime.utcnow()
    db.commit()

    return None


@router.post("/{user_id}/deactivate")
def deactivate_user(
    user_id: UUID,
    admin = Depends(require_hubsec_staff),
    db: Session = Depends(get_db)
):
    """
    Deactivate a user account

    Access Control:
    - Only HubSec staff can deactivate users
    """
    db_user = db.query(User).filter(User.id == user_id).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.is_active = False
    db_user.updated_at = datetime.utcnow()
    db.commit()

    return {"message": f"User {db_user.username} deactivated"}


@router.post("/{user_id}/activate")
def activate_user(
    user_id: UUID,
    admin = Depends(require_hubsec_staff),
    db: Session = Depends(get_db)
):
    """
    Activate a user account

    Access Control:
    - Only HubSec staff can activate users
    """
    db_user = db.query(User).filter(User.id == user_id).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.is_active = True
    db_user.updated_at = datetime.utcnow()
    db.commit()

    return {"message": f"User {db_user.username} activated"}


@router.post("/{user_id}/tenants/{tenant_id}/assign")
def assign_user_to_tenant(
    user_id: UUID,
    tenant_id: UUID,
    admin = Depends(require_hubsec_staff),
    db: Session = Depends(get_db)
):
    """
    Assign a user to a tenant

    Access Control:
    - Only HubSec staff can assign users to tenants
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tenant = db.query(Tenant).filter(
        Tenant.id == tenant_id,
        Tenant.is_active == True
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Check if already assigned
    if tenant in user.tenants:
        raise HTTPException(status_code=400, detail="User already assigned to this tenant")

    user.tenants.append(tenant)
    db.commit()

    return {
        "message": f"User {user.username} assigned to tenant {tenant.name}",
        "user_id": str(user_id),
        "tenant_id": str(tenant_id)
    }


@router.delete("/{user_id}/tenants/{tenant_id}/unassign")
def unassign_user_from_tenant(
    user_id: UUID,
    tenant_id: UUID,
    admin = Depends(require_hubsec_staff),
    db: Session = Depends(get_db)
):
    """
    Unassign a user from a tenant

    Access Control:
    - Only HubSec staff can unassign users from tenants
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Check if assigned
    if tenant not in user.tenants:
        raise HTTPException(status_code=400, detail="User not assigned to this tenant")

    user.tenants.remove(tenant)
    db.commit()

    return {
        "message": f"User {user.username} unassigned from tenant {tenant.name}",
        "user_id": str(user_id),
        "tenant_id": str(tenant_id)
    }


@router.get("/{user_id}/tenants")
def get_user_tenants(
    user_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get all tenants a user has access to

    Access Control:
    - HubSec staff can view any user's tenants
    - Users can view their own tenants
    - Tenant admins can view tenants for users in their tenants
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check access
    if context.user and not context.is_hubsec_staff():
        if context.user.id != user_id:
            # Check if users share at least one tenant
            current_user_tenant_ids = {t.id for t in context.user.tenants}
            target_user_tenant_ids = {t.id for t in user.tenants}

            if not current_user_tenant_ids.intersection(target_user_tenant_ids):
                raise HTTPException(status_code=403, detail="Access denied to this user's tenant information")

    tenants = []
    for tenant in user.tenants:
        if tenant.is_active:
            tenants.append({
                "id": str(tenant.id),
                "name": tenant.name,
                "code": tenant.code,
                "industry": tenant.industry
            })

    return {
        "user_id": str(user_id),
        "username": user.username,
        "tenants": tenants
    }


@router.get("/{user_id}/workload")
def get_user_workload(
    user_id: UUID,
    tenant_id: Optional[UUID] = None,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get workload statistics for a user (tenant-aware)

    Returns:
    - Assigned incidents
    - Assigned cases
    - Case statistics

    Access Control:
    - HubSec staff can view any user's workload
    - Users can view their own workload
    - Filters by accessible tenants
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check access
    if context.user and not context.is_hubsec_staff():
        if context.user.id != user_id:
            raise HTTPException(status_code=403, detail="Access denied to this user's workload")

    # Get accessible tenant IDs
    accessible_tenant_ids = [t.id for t in user.tenants]

    # Filter by specific tenant if provided and accessible
    if tenant_id:
        if tenant_id not in accessible_tenant_ids:
            raise HTTPException(status_code=403, detail="User does not have access to this tenant")
        accessible_tenant_ids = [tenant_id]

    # Get assigned incidents
    assigned_incidents_query = db.query(Incident).filter(
        Incident.assigned_to_id == user_id,
        Incident.tenant_id.in_(accessible_tenant_ids),
        Incident.is_active == True
    )
    assigned_incidents = assigned_incidents_query.all()

    open_incidents = [i for i in assigned_incidents if i.status in [
        IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS
    ]]

    # Get assigned cases
    assigned_cases_query = db.query(Case).join(Case.assigned_users).filter(
        User.id == user_id,
        Case.tenant_id.in_(accessible_tenant_ids),
        Case.is_active == True
    )
    assigned_cases = assigned_cases_query.all()

    open_cases = [c for c in assigned_cases if c.status in [
        CaseStatus.OPEN, CaseStatus.IN_PROGRESS
    ]]

    # Calculate workload metrics
    total_alerts_in_cases = sum(len([a for a in case.alerts if a.is_active]) for case in open_cases)

    return {
        "user_id": str(user_id),
        "username": user.username,
        "tenant_filter": str(tenant_id) if tenant_id else "all",
        "total_incidents": len(assigned_incidents),
        "open_incidents": len(open_incidents),
        "total_cases": len(assigned_cases),
        "open_cases": len(open_cases),
        "total_alerts_in_open_cases": total_alerts_in_cases,
        "incidents": [
            {
                "id": str(i.id),
                "tenant_id": str(i.tenant_id),
                "title": i.title,
                "severity": i.severity.value,
                "status": i.status.value,
                "created_at": i.created_at.isoformat()
            }
            for i in open_incidents
        ],
        "cases": [
            {
                "id": str(c.id),
                "tenant_id": str(c.tenant_id),
                "title": c.title,
                "priority": c.priority.value,
                "status": c.status.value,
                "alert_count": len([a for a in c.alerts if a.is_active]),
                "created_at": c.created_at.isoformat()
            }
            for c in open_cases
        ]
    }


@router.get("/{user_id}/activity")
def get_user_activity(
    user_id: UUID,
    tenant_id: Optional[UUID] = None,
    limit: int = Query(50, ge=1, le=500),
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get recent activity for a user (tenant-aware)

    Returns all activities performed by the user, filtered by accessible tenants

    Access Control:
    - HubSec staff can view any user's activity
    - Users can view their own activity
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check access
    if context.user and not context.is_hubsec_staff():
        if context.user.id != user_id:
            raise HTTPException(status_code=403, detail="Access denied to this user's activity")

    # Get accessible tenant IDs
    accessible_tenant_ids = [t.id for t in user.tenants]

    # Filter by specific tenant if provided
    if tenant_id:
        if tenant_id not in accessible_tenant_ids:
            raise HTTPException(status_code=403, detail="User does not have access to this tenant")
        accessible_tenant_ids = [tenant_id]

    # Get activities for cases in accessible tenants
    activities_query = db.query(Activity).join(Case).filter(
        Activity.user_id == user_id,
        Case.tenant_id.in_(accessible_tenant_ids),
        Activity.is_active == True
    ).order_by(Activity.created_at.desc()).limit(limit)

    activities = activities_query.all()

    return {
        "user_id": str(user_id),
        "username": user.username,
        "tenant_filter": str(tenant_id) if tenant_id else "all",
        "activity_count": len(activities),
        "activities": [
            {
                "id": str(a.id),
                "action": a.action,
                "description": a.description,
                "case_id": str(a.case_id) if a.case_id else None,
                "created_at": a.created_at.isoformat(),
                "metadata": a.metadata
            }
            for a in activities
        ]
    }
