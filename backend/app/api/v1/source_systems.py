"""
Source Systems API Endpoints
Manage integrations (Wazuh, IRIS, Jira, etc.) in the multi-tenant platform
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from backend.app.database_multitenant import get_db
from backend.app.models.models_multitenant import SourceSystem, Tenant, IntegrationType
from backend.app.schemas.schemas_multitenant import (
    SourceSystem as SourceSystemSchema,
    SourceSystemCreate,
    SourceSystemUpdate
)
from backend.app.middleware.tenant import (
    require_tenant,
    require_auth,
    get_tenant_context,
    TenantContext
)

router = APIRouter(prefix="/source-systems", tags=["source-systems"])


@router.get("/", response_model=List[SourceSystemSchema])
def list_source_systems(
    skip: int = 0,
    limit: int = 100,
    tenant_id: Optional[UUID] = None,
    integration_type: Optional[IntegrationType] = None,
    active_only: bool = True,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    List source systems

    **Filtering**:
    - Hubsec staff can see all systems or filter by tenant
    - Tenant users only see their tenant's systems

    **Query params**:
    - tenant_id: Filter by specific tenant (Hubsec staff only)
    - integration_type: Filter by integration type (wazuh, iris, jira, etc.)
    - active_only: Only show active systems (default: true)
    """
    # Build query
    query = db.query(SourceSystem)

    # Apply tenant filtering
    if context.user and not context.is_hubsec_staff():
        # Tenant users can only see their own source systems
        user_tenant_ids = [t.id for t in context.user.tenants]
        query = query.filter(SourceSystem.tenant_id.in_(user_tenant_ids))
    elif tenant_id:
        # Hubsec staff can filter by specific tenant
        query = query.filter(SourceSystem.tenant_id == tenant_id)

    # Apply other filters
    if integration_type:
        query = query.filter(SourceSystem.type == integration_type)

    if active_only:
        query = query.filter(SourceSystem.is_active == True)

    # Order by tenant and name
    query = query.order_by(SourceSystem.tenant_id, SourceSystem.name)

    # Pagination
    systems = query.offset(skip).limit(limit).all()

    return systems


@router.get("/{source_system_id}", response_model=SourceSystemSchema)
def get_source_system(
    source_system_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get source system by ID

    **Access**: Hubsec staff or users assigned to the source system's tenant
    """
    system = db.query(SourceSystem).filter(SourceSystem.id == source_system_id).first()

    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source system {source_system_id} not found"
        )

    # Check access
    if context.user and not context.can_access_tenant(system.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this source system"
        )

    return system


@router.post("/", response_model=SourceSystemSchema, status_code=status.HTTP_201_CREATED)
def create_source_system(
    system_data: SourceSystemCreate,
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Create a new source system

    **Access**: Authenticated users with access to the specified tenant
    """
    # Verify tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == system_data.tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {system_data.tenant_id} not found"
        )

    # Check if user has access to this tenant
    context = TenantContext(tenant=tenant, user=user)
    if not context.can_access_tenant(system_data.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No access to tenant {tenant.code}"
        )

    # Check if system with same name exists for this tenant
    existing = db.query(SourceSystem).filter(
        SourceSystem.tenant_id == system_data.tenant_id,
        SourceSystem.name == system_data.name
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source system '{system_data.name}' already exists for this tenant"
        )

    # Create source system
    system = SourceSystem(
        tenant_id=system_data.tenant_id,
        name=system_data.name,
        type=system_data.type,
        description=system_data.description,
        base_url=system_data.base_url,
        auth_type=system_data.auth_type,
        auth_config=system_data.auth_config or {},
        is_active=system_data.is_active,
        config=system_data.config or {}
    )

    db.add(system)
    db.commit()
    db.refresh(system)

    return system


@router.patch("/{source_system_id}", response_model=SourceSystemSchema)
def update_source_system(
    source_system_id: UUID,
    system_update: SourceSystemUpdate,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Update source system

    **Access**: Authenticated users with access to the source system's tenant
    """
    if not context.user:
        raise HTTPException(status_code=401, detail="Authentication required")

    system = db.query(SourceSystem).filter(SourceSystem.id == source_system_id).first()

    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source system {source_system_id} not found"
        )

    # Check access
    if not context.can_access_tenant(system.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this source system"
        )

    # Update fields
    update_data = system_update.model_dump(exclude_unset=True)

    # Check for name conflict if name is being changed
    if "name" in update_data and update_data["name"] != system.name:
        existing = db.query(SourceSystem).filter(
            SourceSystem.tenant_id == system.tenant_id,
            SourceSystem.name == update_data["name"]
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Source system name '{update_data['name']}' already in use for this tenant"
            )

    # Apply updates
    for key, value in update_data.items():
        setattr(system, key, value)

    db.commit()
    db.refresh(system)

    return system


@router.delete("/{source_system_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source_system(
    source_system_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Delete source system (soft delete - sets is_active=False)

    **Access**: Authenticated users with access to the source system's tenant
    """
    if not context.user:
        raise HTTPException(status_code=401, detail="Authentication required")

    system = db.query(SourceSystem).filter(SourceSystem.id == source_system_id).first()

    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source system {source_system_id} not found"
        )

    # Check access
    if not context.can_access_tenant(system.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this source system"
        )

    # Soft delete
    system.is_active = False
    db.commit()

    return None


@router.post("/{source_system_id}/sync", status_code=status.HTTP_200_OK)
def trigger_sync(
    source_system_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Trigger manual sync for a source system

    **Access**: Authenticated users with access to the source system's tenant

    **Note**: This is a placeholder. Actual sync implementation depends on integration type.
    """
    if not context.user:
        raise HTTPException(status_code=401, detail="Authentication required")

    system = db.query(SourceSystem).filter(SourceSystem.id == source_system_id).first()

    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source system {source_system_id} not found"
        )

    # Check access
    if not context.can_access_tenant(system.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this source system"
        )

    if not system.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot sync inactive source system"
        )

    # Update last sync timestamp
    system.last_sync_at = datetime.utcnow()
    system.sync_status = "in_progress"
    db.commit()

    # TODO: Implement actual sync logic based on integration type
    # - For Wazuh: Fetch recent alerts
    # - For IRIS: Sync case status
    # - For Jira: Update ticket information

    return {
        "message": f"Sync triggered for {system.name}",
        "source_system_id": str(source_system_id),
        "type": system.type,
        "status": "in_progress"
    }


@router.get("/{source_system_id}/health")
def check_source_system_health(
    source_system_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Check health/connectivity of a source system

    **Access**: Authenticated users with access to the source system's tenant
    """
    if not context.user:
        raise HTTPException(status_code=401, detail="Authentication required")

    system = db.query(SourceSystem).filter(SourceSystem.id == source_system_id).first()

    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source system {source_system_id} not found"
        )

    # Check access
    if not context.can_access_tenant(system.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this source system"
        )

    # TODO: Implement actual health checks based on integration type
    # - Ping the base_url
    # - Verify authentication
    # - Check API version compatibility

    return {
        "source_system_id": str(source_system_id),
        "name": system.name,
        "type": system.type,
        "is_active": system.is_active,
        "sync_status": system.sync_status,
        "last_sync_at": system.last_sync_at,
        "health": "unknown",  # Placeholder
        "message": "Health check not yet implemented for this integration type"
    }
