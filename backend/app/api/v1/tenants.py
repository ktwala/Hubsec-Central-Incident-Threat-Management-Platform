"""
Tenants API Endpoints
Manage organizations in the multi-tenant platform
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from backend.app.database_multitenant import get_db
from backend.app.models.models_multitenant import Tenant
from backend.app.schemas.schemas_multitenant import (
    Tenant as TenantSchema,
    TenantCreate,
    TenantUpdate
)
from backend.app.middleware.tenant import require_super_admin, require_hubsec_staff, TenantContext, get_tenant_context

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/", response_model=List[TenantSchema])
def list_tenants(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    List all tenants

    **Access**: Hubsec staff see all tenants, tenant users see only their assigned tenants
    """
    # Build query
    query = db.query(Tenant)

    # Filter by active status
    if active_only:
        query = query.filter(Tenant.is_active == True)

    # Apply tenant filtering based on user role
    if context.user:
        if not context.is_hubsec_staff():
            # Regular users only see their assigned tenants
            user_tenant_ids = [t.id for t in context.user.tenants]
            query = query.filter(Tenant.id.in_(user_tenant_ids))
    else:
        # No auth - only return active tenants (limited info)
        query = query.filter(Tenant.is_active == True)

    # Pagination
    tenants = query.offset(skip).limit(limit).all()

    return tenants


@router.get("/{tenant_id}", response_model=TenantSchema)
def get_tenant(
    tenant_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get tenant by ID

    **Access**: Hubsec staff or users assigned to the tenant
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found"
        )

    # Check access
    if context.user and not context.can_access_tenant(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
        )

    return tenant


@router.post("/", response_model=TenantSchema, status_code=status.HTTP_201_CREATED)
def create_tenant(
    tenant_data: TenantCreate,
    user = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new tenant

    **Access**: Super admin only
    """
    # Check if tenant code already exists
    existing = db.query(Tenant).filter(Tenant.code == tenant_data.code.upper()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with code '{tenant_data.code}' already exists"
        )

    # Check if tenant name already exists
    existing = db.query(Tenant).filter(Tenant.name == tenant_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with name '{tenant_data.name}' already exists"
        )

    # Create tenant
    tenant = Tenant(
        name=tenant_data.name,
        code=tenant_data.code.upper(),  # Always uppercase
        industry=tenant_data.industry,
        region=tenant_data.region,
        contact_name=tenant_data.contact_name,
        contact_email=tenant_data.contact_email,
        contact_phone=tenant_data.contact_phone,
        is_active=tenant_data.is_active,
        subscription_tier=tenant_data.subscription_tier,
        settings=tenant_data.settings or {}
    )

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant


@router.patch("/{tenant_id}", response_model=TenantSchema)
def update_tenant(
    tenant_id: UUID,
    tenant_update: TenantUpdate,
    user = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Update tenant

    **Access**: Super admin only
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found"
        )

    # Update fields
    update_data = tenant_update.model_dump(exclude_unset=True)

    # Uppercase code if provided
    if "code" in update_data:
        update_data["code"] = update_data["code"].upper()

    # Check for conflicts
    if "code" in update_data and update_data["code"] != tenant.code:
        existing = db.query(Tenant).filter(Tenant.code == update_data["code"]).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tenant code '{update_data['code']}' already in use"
            )

    if "name" in update_data and update_data["name"] != tenant.name:
        existing = db.query(Tenant).filter(Tenant.name == update_data["name"]).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tenant name '{update_data['name']}' already in use"
            )

    # Apply updates
    for key, value in update_data.items():
        setattr(tenant, key, value)

    db.commit()
    db.refresh(tenant)

    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(
    tenant_id: UUID,
    user = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Delete tenant (soft delete - sets is_active=False)

    **Access**: Super admin only
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found"
        )

    # Soft delete
    tenant.is_active = False
    db.commit()

    return None


@router.get("/{tenant_id}/stats")
def get_tenant_stats(
    tenant_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get statistics for a specific tenant

    **Access**: Hubsec staff or users assigned to the tenant
    """
    from backend.app.models.models_multitenant import Alert, Incident, Case, SourceSystem, Asset

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Check access
    if context.user and not context.can_access_tenant(tenant_id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Gather stats
    stats = {
        "tenant_id": str(tenant_id),
        "tenant_name": tenant.name,
        "tenant_code": tenant.code,
        "total_alerts": db.query(Alert).filter(Alert.tenant_id == tenant_id).count(),
        "total_incidents": db.query(Incident).filter(Incident.tenant_id == tenant_id).count(),
        "total_cases": db.query(Case).filter(Case.tenant_id == tenant_id).count(),
        "total_source_systems": db.query(SourceSystem).filter(SourceSystem.tenant_id == tenant_id).count(),
        "active_source_systems": db.query(SourceSystem).filter(
            SourceSystem.tenant_id == tenant_id,
            SourceSystem.is_active == True
        ).count(),
        "total_assets": db.query(Asset).filter(Asset.tenant_id == tenant_id).count(),
        "active_assets": db.query(Asset).filter(
            Asset.tenant_id == tenant_id,
            Asset.is_active == True
        ).count(),
    }

    return stats
