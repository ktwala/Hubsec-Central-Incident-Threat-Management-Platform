"""
Assets API Endpoints
Manage IT assets/endpoints in the multi-tenant platform
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from backend.app.database_multitenant import get_db
from backend.app.models.models_multitenant import Asset, Tenant, AssetType, SeverityLevel
from backend.app.schemas.schemas_multitenant import (
    Asset as AssetSchema,
    AssetCreate,
    AssetUpdate
)
from backend.app.middleware.tenant import (
    require_tenant,
    require_auth,
    get_tenant_context,
    TenantContext
)

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/", response_model=List[AssetSchema])
def list_assets(
    skip: int = 0,
    limit: int = 100,
    tenant_id: Optional[UUID] = None,
    asset_type: Optional[AssetType] = None,
    criticality: Optional[SeverityLevel] = None,
    environment: Optional[str] = None,
    active_only: bool = True,
    search: Optional[str] = None,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    List assets

    **Filtering**:
    - Hubsec staff can see all assets or filter by tenant
    - Tenant users only see their tenant's assets

    **Query params**:
    - tenant_id: Filter by specific tenant (Hubsec staff only)
    - asset_type: Filter by asset type (server, workstation, etc.)
    - criticality: Filter by criticality level
    - environment: Filter by environment (production, staging, etc.)
    - active_only: Only show active assets (default: true)
    - search: Search in hostname or IP address
    """
    # Build query
    query = db.query(Asset)

    # Apply tenant filtering
    if context.user and not context.is_hubsec_staff():
        # Tenant users can only see their own assets
        user_tenant_ids = [t.id for t in context.user.tenants]
        query = query.filter(Asset.tenant_id.in_(user_tenant_ids))
    elif tenant_id:
        # Hubsec staff can filter by specific tenant
        query = query.filter(Asset.tenant_id == tenant_id)

    # Apply other filters
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)

    if criticality:
        query = query.filter(Asset.criticality == criticality)

    if environment:
        query = query.filter(Asset.environment == environment)

    if active_only:
        query = query.filter(Asset.is_active == True)

    # Search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Asset.hostname.ilike(search_pattern)) |
            (Asset.ip_address.cast(db.String).ilike(search_pattern))
        )

    # Order by criticality (descending) and hostname
    criticality_order = {
        SeverityLevel.CRITICAL: 0,
        SeverityLevel.HIGH: 1,
        SeverityLevel.MEDIUM: 2,
        SeverityLevel.LOW: 3,
        SeverityLevel.INFO: 4
    }

    # Order by tenant, criticality, and hostname
    query = query.order_by(Asset.tenant_id, Asset.criticality, Asset.hostname)

    # Pagination
    assets = query.offset(skip).limit(limit).all()

    return assets


@router.get("/{asset_id}", response_model=AssetSchema)
def get_asset(
    asset_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get asset by ID

    **Access**: Hubsec staff or users assigned to the asset's tenant
    """
    asset = db.query(Asset).filter(Asset.id == asset_id).first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {asset_id} not found"
        )

    # Check access
    if context.user and not context.can_access_tenant(asset.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this asset"
        )

    return asset


@router.post("/", response_model=AssetSchema, status_code=status.HTTP_201_CREATED)
def create_asset(
    asset_data: AssetCreate,
    user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Create a new asset

    **Access**: Authenticated users with access to the specified tenant
    """
    # Verify tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == asset_data.tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {asset_data.tenant_id} not found"
        )

    # Check if user has access to this tenant
    context = TenantContext(tenant=tenant, user=user)
    if not context.can_access_tenant(asset_data.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No access to tenant {tenant.code}"
        )

    # Check for duplicate hostname within tenant
    if asset_data.hostname:
        existing = db.query(Asset).filter(
            Asset.tenant_id == asset_data.tenant_id,
            Asset.hostname == asset_data.hostname
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset with hostname '{asset_data.hostname}' already exists for this tenant"
            )

    # Check for duplicate IP address within tenant
    if asset_data.ip_address:
        existing = db.query(Asset).filter(
            Asset.tenant_id == asset_data.tenant_id,
            Asset.ip_address == asset_data.ip_address
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset with IP '{asset_data.ip_address}' already exists for this tenant"
            )

    # Create asset
    asset = Asset(
        tenant_id=asset_data.tenant_id,
        hostname=asset_data.hostname,
        ip_address=asset_data.ip_address,
        mac_address=asset_data.mac_address,
        asset_type=asset_data.asset_type,
        criticality=asset_data.criticality,
        os=asset_data.os,
        os_version=asset_data.os_version,
        environment=asset_data.environment,
        owner=asset_data.owner,
        department=asset_data.department,
        location=asset_data.location,
        is_active=asset_data.is_active,
        tags=asset_data.tags or [],
        meta_data=asset_data.meta_data or {}
    )

    db.add(asset)
    db.commit()
    db.refresh(asset)

    return asset


@router.patch("/{asset_id}", response_model=AssetSchema)
def update_asset(
    asset_id: UUID,
    asset_update: AssetUpdate,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Update asset

    **Access**: Authenticated users with access to the asset's tenant
    """
    if not context.user:
        raise HTTPException(status_code=401, detail="Authentication required")

    asset = db.query(Asset).filter(Asset.id == asset_id).first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {asset_id} not found"
        )

    # Check access
    if not context.can_access_tenant(asset.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this asset"
        )

    # Update fields
    update_data = asset_update.model_dump(exclude_unset=True)

    # Check for hostname conflict if hostname is being changed
    if "hostname" in update_data and update_data["hostname"] != asset.hostname:
        existing = db.query(Asset).filter(
            Asset.tenant_id == asset.tenant_id,
            Asset.hostname == update_data["hostname"]
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset hostname '{update_data['hostname']}' already in use for this tenant"
            )

    # Check for IP conflict if IP is being changed
    if "ip_address" in update_data and update_data["ip_address"] != asset.ip_address:
        existing = db.query(Asset).filter(
            Asset.tenant_id == asset.tenant_id,
            Asset.ip_address == update_data["ip_address"]
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset IP '{update_data['ip_address']}' already in use for this tenant"
            )

    # Apply updates
    for key, value in update_data.items():
        setattr(asset, key, value)

    db.commit()
    db.refresh(asset)

    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Delete asset (soft delete - sets is_active=False)

    **Access**: Authenticated users with access to the asset's tenant
    """
    if not context.user:
        raise HTTPException(status_code=401, detail="Authentication required")

    asset = db.query(Asset).filter(Asset.id == asset_id).first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {asset_id} not found"
        )

    # Check access
    if not context.can_access_tenant(asset.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this asset"
        )

    # Soft delete
    asset.is_active = False
    db.commit()

    return None


@router.post("/{asset_id}/heartbeat", status_code=status.HTTP_200_OK)
def update_asset_heartbeat(
    asset_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Update asset last_seen timestamp (heartbeat)

    **Access**: Authenticated users with access to the asset's tenant

    **Use case**: Called by agents or monitoring systems to indicate asset is online
    """
    if not context.user:
        raise HTTPException(status_code=401, detail="Authentication required")

    asset = db.query(Asset).filter(Asset.id == asset_id).first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {asset_id} not found"
        )

    # Check access
    if not context.can_access_tenant(asset.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this asset"
        )

    # Update last_seen
    asset.last_seen = datetime.utcnow()
    db.commit()

    return {
        "asset_id": str(asset_id),
        "hostname": asset.hostname,
        "last_seen": asset.last_seen,
        "message": "Heartbeat recorded"
    }


@router.get("/{asset_id}/alerts")
def get_asset_alerts(
    asset_id: UUID,
    skip: int = 0,
    limit: int = 50,
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get alerts associated with this asset

    **Access**: Hubsec staff or users assigned to the asset's tenant
    """
    from backend.app.models.models_multitenant import Alert

    asset = db.query(Asset).filter(Asset.id == asset_id).first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {asset_id} not found"
        )

    # Check access
    if context.user and not context.can_access_tenant(asset.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this asset"
        )

    # Get alerts for this asset
    alerts = db.query(Alert).filter(
        Alert.asset_id == asset_id
    ).order_by(Alert.timestamp.desc()).offset(skip).limit(limit).all()

    return {
        "asset_id": str(asset_id),
        "hostname": asset.hostname,
        "total_alerts": db.query(Alert).filter(Alert.asset_id == asset_id).count(),
        "alerts": alerts
    }
