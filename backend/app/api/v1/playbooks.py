"""
Playbooks API Endpoints
Manage incident response playbooks/runbooks in the multi-tenant platform
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from backend.app.database_multitenant import get_db
from backend.app.models.models_multitenant import (
    Playbook, CasePlaybook, Case, Tenant, PlaybookStatus
)
from backend.app.schemas.schemas_multitenant import (
    Playbook as PlaybookSchema,
    PlaybookCreate,
    PlaybookUpdate,
    CasePlaybook as CasePlaybookSchema,
    CasePlaybookCreate,
    CasePlaybookUpdate
)
from backend.app.middleware.tenant import (
    require_auth,
    get_tenant_context,
    TenantContext
)

router = APIRouter(prefix="/playbooks", tags=["playbooks"])


@router.get("/", response_model=List[PlaybookSchema])
def list_playbooks(
    skip: int = 0,
    limit: int = 100,
    tenant_id: Optional[UUID] = None,
    incident_type: Optional[str] = None,
    active_only: bool = True,
    include_global: bool = True,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    List playbooks

    **Filtering**:
    - Global playbooks (tenant_id=NULL) are available to all
    - Tenant-specific playbooks only visible to that tenant's users
    - Hubsec staff can see all playbooks

    **Query params**:
    - tenant_id: Filter by specific tenant (or global if null)
    - incident_type: Filter by incident type
    - active_only: Only show active playbooks (default: true)
    - include_global: Include global playbooks in results (default: true)
    """
    # Build query
    query = db.query(Playbook)

    # Apply tenant filtering
    if context.user and not context.is_hubsec_staff():
        # Tenant users see global playbooks + their tenant's playbooks
        user_tenant_ids = [t.id for t in context.user.tenants]

        if include_global:
            # Include both global and tenant-specific
            query = query.filter(
                (Playbook.tenant_id.in_(user_tenant_ids)) |
                (Playbook.tenant_id == None)
            )
        else:
            # Only tenant-specific
            query = query.filter(Playbook.tenant_id.in_(user_tenant_ids))
    elif tenant_id:
        # Filter by specific tenant
        query = query.filter(Playbook.tenant_id == tenant_id)
    elif not include_global:
        # Exclude global playbooks
        query = query.filter(Playbook.tenant_id != None)

    # Apply other filters
    if incident_type:
        query = query.filter(Playbook.incident_type == incident_type)

    if active_only:
        query = query.filter(Playbook.is_active == True)

    # Order by tenant (global first), then name
    query = query.order_by(Playbook.tenant_id.nullsfirst(), Playbook.name)

    # Pagination
    playbooks = query.offset(skip).limit(limit).all()

    return playbooks


@router.get("/{playbook_id}", response_model=PlaybookSchema)
def get_playbook(
    playbook_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get playbook by ID

    **Access**:
    - Global playbooks: Anyone can view
    - Tenant playbooks: Only users with access to that tenant
    """
    playbook = db.query(Playbook).filter(Playbook.id == playbook_id).first()

    if not playbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found"
        )

    # Check access for tenant-specific playbooks
    if playbook.tenant_id:
        if context.user and not context.can_access_tenant(playbook.tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this playbook"
            )

    return playbook


@router.post("/", response_model=PlaybookSchema, status_code=status.HTTP_201_CREATED)
def create_playbook(
    playbook_data: PlaybookCreate,
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Create a new playbook

    **Access**:
    - Global playbooks (tenant_id=null): Only super admins
    - Tenant playbooks: Users with access to that tenant
    """
    # If creating a global playbook, require super admin
    if playbook_data.tenant_id is None:
        context = TenantContext(user=user)
        if not context.is_super_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admins can create global playbooks"
            )
    else:
        # Verify tenant exists
        tenant = db.query(Tenant).filter(Tenant.id == playbook_data.tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {playbook_data.tenant_id} not found"
            )

        # Check if user has access to this tenant
        context = TenantContext(tenant=tenant, user=user)
        if not context.can_access_tenant(playbook_data.tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No access to tenant {tenant.code}"
            )

    # Check for duplicate name within scope (global or tenant)
    existing = db.query(Playbook).filter(
        Playbook.tenant_id == playbook_data.tenant_id,
        Playbook.name == playbook_data.name
    ).first()

    if existing:
        scope = "global" if playbook_data.tenant_id is None else "this tenant"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Playbook '{playbook_data.name}' already exists in {scope}"
        )

    # Create playbook
    playbook = Playbook(
        tenant_id=playbook_data.tenant_id,
        name=playbook_data.name,
        description=playbook_data.description,
        incident_type=playbook_data.incident_type,
        definition=playbook_data.definition,
        version=playbook_data.version,
        is_active=playbook_data.is_active,
        tags=playbook_data.tags or [],
        created_by=playbook_data.created_by or user.id
    )

    db.add(playbook)
    db.commit()
    db.refresh(playbook)

    return playbook


@router.patch("/{playbook_id}", response_model=PlaybookSchema)
def update_playbook(
    playbook_id: UUID,
    playbook_update: PlaybookUpdate,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Update playbook

    **Access**:
    - Global playbooks: Only super admins
    - Tenant playbooks: Users with access to that tenant
    """
    if not context.user:
        raise HTTPException(status_code=401, detail="Authentication required")

    playbook = db.query(Playbook).filter(Playbook.id == playbook_id).first()

    if not playbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found"
        )

    # Check access
    if playbook.tenant_id is None:
        # Global playbook - requires super admin
        if not context.is_super_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admins can update global playbooks"
            )
    else:
        # Tenant playbook
        if not context.can_access_tenant(playbook.tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this playbook"
            )

    # Update fields
    update_data = playbook_update.model_dump(exclude_unset=True)

    # Check for name conflict if name is being changed
    if "name" in update_data and update_data["name"] != playbook.name:
        existing = db.query(Playbook).filter(
            Playbook.tenant_id == playbook.tenant_id,
            Playbook.name == update_data["name"]
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Playbook name '{update_data['name']}' already in use"
            )

    # Apply updates
    for key, value in update_data.items():
        setattr(playbook, key, value)

    db.commit()
    db.refresh(playbook)

    return playbook


@router.delete("/{playbook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_playbook(
    playbook_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Delete playbook (soft delete - sets is_active=False)

    **Access**:
    - Global playbooks: Only super admins
    - Tenant playbooks: Users with access to that tenant
    """
    if not context.user:
        raise HTTPException(status_code=401, detail="Authentication required")

    playbook = db.query(Playbook).filter(Playbook.id == playbook_id).first()

    if not playbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found"
        )

    # Check access
    if playbook.tenant_id is None:
        if not context.is_super_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admins can delete global playbooks"
            )
    else:
        if not context.can_access_tenant(playbook.tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this playbook"
            )

    # Soft delete
    playbook.is_active = False
    db.commit()

    return None


# ============================================================================
# CASE PLAYBOOK ENDPOINTS (Playbook Execution)
# ============================================================================

@router.post("/execute", response_model=CasePlaybookSchema, status_code=status.HTTP_201_CREATED)
def attach_playbook_to_case(
    case_playbook_data: CasePlaybookCreate,
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Attach a playbook to a case (start playbook execution)

    **Access**: Users with access to the case's tenant
    """
    # Verify case exists
    case = db.query(Case).filter(Case.id == case_playbook_data.case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_playbook_data.case_id} not found"
        )

    # Check access to case
    context = TenantContext(user=user)
    if not context.can_access_tenant(case.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this case"
        )

    # Verify playbook exists
    playbook = db.query(Playbook).filter(Playbook.id == case_playbook_data.playbook_id).first()
    if not playbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {case_playbook_data.playbook_id} not found"
        )

    # Check if playbook is accessible
    if playbook.tenant_id and not context.can_access_tenant(playbook.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this playbook"
        )

    if not playbook.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot execute inactive playbook"
        )

    # Check if playbook already attached to this case
    existing = db.query(CasePlaybook).filter(
        CasePlaybook.case_id == case_playbook_data.case_id,
        CasePlaybook.playbook_id == case_playbook_data.playbook_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Playbook already attached to this case"
        )

    # Count total steps from playbook definition
    total_steps = len(playbook.definition.get("steps", [])) if playbook.definition else 0

    # Create case playbook
    case_playbook = CasePlaybook(
        case_id=case_playbook_data.case_id,
        playbook_id=case_playbook_data.playbook_id,
        status=case_playbook_data.status,
        started_by=case_playbook_data.started_by or user.id,
        started_at=datetime.utcnow() if case_playbook_data.status != PlaybookStatus.NOT_STARTED else None,
        current_step=case_playbook_data.current_step,
        total_steps=total_steps,
        completed_steps=case_playbook_data.completed_steps or {},
        meta_data=case_playbook_data.meta_data or {}
    )

    db.add(case_playbook)
    db.commit()
    db.refresh(case_playbook)

    # Load the playbook relationship
    db.refresh(case_playbook)

    return case_playbook


@router.patch("/executions/{case_playbook_id}", response_model=CasePlaybookSchema)
def update_case_playbook(
    case_playbook_id: UUID,
    case_playbook_update: CasePlaybookUpdate,
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Update playbook execution status

    **Access**: Users with access to the case's tenant
    """
    case_playbook = db.query(CasePlaybook).filter(CasePlaybook.id == case_playbook_id).first()

    if not case_playbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case playbook {case_playbook_id} not found"
        )

    # Get case to check access
    case = db.query(Case).filter(Case.id == case_playbook.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Associated case not found")

    # Check access
    context = TenantContext(user=user)
    if not context.can_access_tenant(case.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this case playbook"
        )

    # Update fields
    update_data = case_playbook_update.model_dump(exclude_unset=True)

    # Set timestamps based on status changes
    if "status" in update_data:
        if update_data["status"] == PlaybookStatus.IN_PROGRESS and not case_playbook.started_at:
            case_playbook.started_at = datetime.utcnow()
        elif update_data["status"] in [PlaybookStatus.COMPLETED, PlaybookStatus.FAILED, PlaybookStatus.CANCELLED]:
            case_playbook.completed_at = datetime.utcnow()

    # Apply updates
    for key, value in update_data.items():
        setattr(case_playbook, key, value)

    db.commit()
    db.refresh(case_playbook)

    return case_playbook


@router.get("/executions/case/{case_id}", response_model=List[CasePlaybookSchema])
def get_case_playbooks(
    case_id: UUID,
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Get all playbook executions for a case

    **Access**: Users with access to the case's tenant
    """
    # Get case to check access
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Check access
    context = TenantContext(user=user)
    if not context.can_access_tenant(case.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this case"
        )

    # Get playbook executions
    case_playbooks = db.query(CasePlaybook).filter(
        CasePlaybook.case_id == case_id
    ).all()

    return case_playbooks
