"""
Threat Intelligence API Endpoints
Manage threat intelligence feeds and IOCs in the multi-tenant platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from backend.app.database_multitenant import get_db
from backend.app.models.models_multitenant import (
    ThreatIntelFeed,
    ThreatIntelIOC,
    Alert,
    IOCType,
    SeverityLevel
)
from backend.app.schemas.schemas_multitenant import (
    ThreatIntelFeed as ThreatIntelFeedSchema,
    ThreatIntelFeedCreate,
    ThreatIntelFeedUpdate,
    ThreatIntelFeedSyncRequest,
    ThreatIntelFeedSyncResponse,
    ThreatIntelIOC as ThreatIntelIOCSchema,
    ThreatIntelIOCCreate,
    ThreatIntelIOCUpdate,
    ThreatIntelIOCBulkCreate,
    IOCSearchResult,
    IOCMatch
)
from backend.app.middleware.tenant import (
    require_auth,
    require_super_admin,
    require_hubsec_staff,
    get_tenant_context,
    TenantContext
)

router = APIRouter(prefix="/threat-intel", tags=["threat-intelligence"])


# ============================================================================
# THREAT INTEL FEED ENDPOINTS
# ============================================================================

@router.get("/feeds", response_model=List[ThreatIntelFeedSchema])
def list_ti_feeds(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: Optional[UUID] = Query(None, description="Filter by tenant"),
    enabled_only: bool = Query(True, description="Show only enabled feeds"),
    include_global: bool = Query(True, description="Include global feeds"),
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    List threat intelligence feeds

    **Access**:
    - Hubsec staff can see all feeds or filter by tenant
    - Tenant users see their tenant's feeds + global feeds

    **Query params**:
    - tenant_id: Filter by specific tenant (Hubsec staff only)
    - enabled_only: Only show enabled feeds (default: true)
    - include_global: Include global feeds in results (default: true)
    """
    query = db.query(ThreatIntelFeed)

    # Apply tenant filtering
    if context.user and not context.is_hubsec_staff():
        # Tenant users see their own feeds + global feeds
        user_tenant_ids = [t.id for t in context.user.tenants]
        if include_global:
            query = query.filter(
                or_(
                    ThreatIntelFeed.tenant_id.in_(user_tenant_ids),
                    ThreatIntelFeed.is_global == True
                )
            )
        else:
            query = query.filter(ThreatIntelFeed.tenant_id.in_(user_tenant_ids))
    elif tenant_id:
        # Hubsec staff filtering by specific tenant
        if include_global:
            query = query.filter(
                or_(
                    ThreatIntelFeed.tenant_id == tenant_id,
                    ThreatIntelFeed.is_global == True
                )
            )
        else:
            query = query.filter(ThreatIntelFeed.tenant_id == tenant_id)
    elif not include_global:
        # Exclude global feeds
        query = query.filter(ThreatIntelFeed.is_global == False)

    # Apply additional filters
    if enabled_only:
        query = query.filter(ThreatIntelFeed.is_enabled == True)

    # Order by last sync time (most recent first)
    query = query.order_by(ThreatIntelFeed.last_sync_at.desc().nullslast())

    return query.offset(skip).limit(limit).all()


@router.post("/feeds", response_model=ThreatIntelFeedSchema, status_code=status.HTTP_201_CREATED)
def create_ti_feed(
    feed: ThreatIntelFeedCreate,
    context: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Create a new threat intelligence feed

    **Permissions**:
    - Global feeds: Super admin only
    - Tenant feeds: Tenant admin or above

    **Note**: API keys and passwords should be encrypted in production
    """
    # Validate access
    if feed.is_global:
        # Only super admin can create global feeds
        if not context.is_super_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admins can create global threat intelligence feeds"
            )
    elif feed.tenant_id:
        # Validate tenant access
        if not context.can_access_tenant(feed.tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either tenant_id must be specified or is_global must be true"
        )

    # Check for duplicate feed name
    existing = db.query(ThreatIntelFeed).filter(
        ThreatIntelFeed.name == feed.name,
        or_(
            ThreatIntelFeed.tenant_id == feed.tenant_id,
            ThreatIntelFeed.is_global == True
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Feed with name '{feed.name}' already exists"
        )

    # Create feed
    db_feed = ThreatIntelFeed(**feed.model_dump())
    db.add(db_feed)
    db.commit()
    db.refresh(db_feed)

    return db_feed


@router.get("/feeds/{feed_id}", response_model=ThreatIntelFeedSchema)
def get_ti_feed(
    feed_id: UUID,
    context: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get threat intelligence feed by ID"""
    feed = db.query(ThreatIntelFeed).filter(ThreatIntelFeed.id == feed_id).first()

    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Threat intelligence feed {feed_id} not found"
        )

    # Validate access
    if feed.tenant_id and not feed.is_global:
        if not context.can_access_tenant(feed.tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )

    return feed


@router.patch("/feeds/{feed_id}", response_model=ThreatIntelFeedSchema)
def update_ti_feed(
    feed_id: UUID,
    feed_update: ThreatIntelFeedUpdate,
    context: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Update threat intelligence feed"""
    feed = db.query(ThreatIntelFeed).filter(ThreatIntelFeed.id == feed_id).first()

    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Threat intelligence feed {feed_id} not found"
        )

    # Validate access
    if feed.is_global and not context.is_super_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can modify global feeds"
        )
    elif feed.tenant_id and not context.can_access_tenant(feed.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
        )

    # Apply updates
    update_data = feed_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(feed, field, value)

    feed.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(feed)

    return feed


@router.delete("/feeds/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ti_feed(
    feed_id: UUID,
    context: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Delete threat intelligence feed (and all its IOCs)

    **Warning**: This will cascade delete all IOCs from this feed
    """
    feed = db.query(ThreatIntelFeed).filter(ThreatIntelFeed.id == feed_id).first()

    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Threat intelligence feed {feed_id} not found"
        )

    # Validate access
    if feed.is_global and not context.is_super_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can delete global feeds"
        )
    elif feed.tenant_id and not context.can_access_tenant(feed.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
        )

    db.delete(feed)
    db.commit()
    return None


@router.post("/feeds/{feed_id}/sync", response_model=ThreatIntelFeedSyncResponse)
def trigger_feed_sync(
    feed_id: UUID,
    force: bool = Query(False, description="Force sync even if recently synced"),
    context: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Trigger a manual sync of threat intelligence feed

    **Note**: In production, this should queue a background job
    Currently returns a placeholder response
    """
    feed = db.query(ThreatIntelFeed).filter(ThreatIntelFeed.id == feed_id).first()

    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Threat intelligence feed {feed_id} not found"
        )

    # Validate access
    if feed.tenant_id and not feed.is_global:
        if not context.can_access_tenant(feed.tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )

    if not feed.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot sync disabled feed"
        )

    # Check if recently synced
    if not force and feed.last_sync_at:
        time_since_sync = datetime.utcnow() - feed.last_sync_at
        if time_since_sync.total_seconds() < 300:  # 5 minutes
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Feed was synced {int(time_since_sync.total_seconds())} seconds ago. Use force=true to override"
            )

    # Update feed status
    feed.last_sync_at = datetime.utcnow()
    feed.last_sync_status = "in_progress"
    db.commit()

    # Return sync response
    # TODO: In production, queue background job for actual sync
    return ThreatIntelFeedSyncResponse(
        feed_id=feed_id,
        status="started",
        message=f"Sync started for feed '{feed.name}'. This is a placeholder - implement actual sync logic.",
        sync_started_at=datetime.utcnow()
    )


# ============================================================================
# IOC ENDPOINTS
# ============================================================================

@router.get("/iocs", response_model=List[ThreatIntelIOCSchema])
def list_iocs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: Optional[UUID] = Query(None, description="Filter by tenant"),
    feed_id: Optional[UUID] = Query(None, description="Filter by feed"),
    ioc_type: Optional[IOCType] = Query(None, description="Filter by IOC type"),
    severity: Optional[SeverityLevel] = Query(None, description="Filter by severity"),
    active_only: bool = Query(True, description="Only active IOCs"),
    include_global: bool = Query(True, description="Include global IOCs"),
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    List threat intelligence IOCs

    **Filtering**:
    - Hubsec staff can see all IOCs or filter by tenant
    - Tenant users see their tenant's IOCs + global IOCs
    """
    query = db.query(ThreatIntelIOC)

    # Apply tenant filtering
    if context.user and not context.is_hubsec_staff():
        user_tenant_ids = [t.id for t in context.user.tenants]
        if include_global:
            query = query.filter(
                or_(
                    ThreatIntelIOC.tenant_id.in_(user_tenant_ids),
                    ThreatIntelIOC.tenant_id == None  # Global IOCs
                )
            )
        else:
            query = query.filter(ThreatIntelIOC.tenant_id.in_(user_tenant_ids))
    elif tenant_id:
        if include_global:
            query = query.filter(
                or_(
                    ThreatIntelIOC.tenant_id == tenant_id,
                    ThreatIntelIOC.tenant_id == None
                )
            )
        else:
            query = query.filter(ThreatIntelIOC.tenant_id == tenant_id)

    # Apply additional filters
    if feed_id:
        query = query.filter(ThreatIntelIOC.feed_id == feed_id)
    if ioc_type:
        query = query.filter(ThreatIntelIOC.ioc_type == ioc_type)
    if severity:
        query = query.filter(ThreatIntelIOC.severity == severity)
    if active_only:
        query = query.filter(
            and_(
                ThreatIntelIOC.is_active == True,
                or_(
                    ThreatIntelIOC.expiration_date == None,
                    ThreatIntelIOC.expiration_date > datetime.utcnow()
                )
            )
        )

    # Order by severity (critical first) and last seen
    query = query.order_by(
        ThreatIntelIOC.severity.desc(),
        ThreatIntelIOC.last_seen.desc()
    )

    return query.offset(skip).limit(limit).all()


@router.post("/iocs", response_model=ThreatIntelIOCSchema, status_code=status.HTTP_201_CREATED)
def create_ioc(
    ioc: ThreatIntelIOCCreate,
    context: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Create a new IOC

    **Permissions**:
    - Global IOCs: Super admin only
    - Tenant IOCs: Tenant admin or above
    """
    # Validate feed exists and access
    feed = db.query(ThreatIntelFeed).filter(ThreatIntelFeed.id == ioc.feed_id).first()
    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed {ioc.feed_id} not found"
        )

    # Validate tenant access
    if ioc.tenant_id:
        if not context.can_access_tenant(ioc.tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
    elif not context.is_super_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can create global IOCs"
        )

    # Check for duplicate IOC
    existing = db.query(ThreatIntelIOC).filter(
        ThreatIntelIOC.value == ioc.value,
        ThreatIntelIOC.ioc_type == ioc.ioc_type,
        ThreatIntelIOC.feed_id == ioc.feed_id,
        ThreatIntelIOC.is_active == True
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Active IOC with value '{ioc.value}' already exists in this feed"
        )

    # Create IOC
    db_ioc = ThreatIntelIOC(**ioc.model_dump())
    db.add(db_ioc)

    # Update feed IOC count
    feed.ioc_count = db.query(func.count(ThreatIntelIOC.id)).filter(
        ThreatIntelIOC.feed_id == feed.id,
        ThreatIntelIOC.is_active == True
    ).scalar() + 1

    db.commit()
    db.refresh(db_ioc)

    return db_ioc


@router.post("/iocs/bulk", response_model=dict, status_code=status.HTTP_201_CREATED)
def bulk_create_iocs(
    bulk_data: ThreatIntelIOCBulkCreate,
    context: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Bulk create IOCs from a feed

    **Returns**: Count of created and updated IOCs
    """
    # Validate feed exists
    feed = db.query(ThreatIntelFeed).filter(ThreatIntelFeed.id == bulk_data.feed_id).first()
    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed {bulk_data.feed_id} not found"
        )

    # Validate access
    if bulk_data.tenant_id:
        if not context.can_access_tenant(bulk_data.tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
    elif not context.is_super_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can create global IOCs"
        )

    created_count = 0
    updated_count = 0
    errors = []

    for ioc_data in bulk_data.iocs:
        try:
            # Check if IOC exists
            existing = db.query(ThreatIntelIOC).filter(
                ThreatIntelIOC.value == ioc_data.value,
                ThreatIntelIOC.ioc_type == ioc_data.ioc_type,
                ThreatIntelIOC.feed_id == bulk_data.feed_id
            ).first()

            if existing:
                # Update existing
                existing.last_seen = datetime.utcnow()
                existing.severity = ioc_data.severity
                existing.confidence = ioc_data.confidence
                existing.is_active = True
                updated_count += 1
            else:
                # Create new
                db_ioc = ThreatIntelIOC(
                    tenant_id=bulk_data.tenant_id,
                    feed_id=bulk_data.feed_id,
                    **ioc_data.model_dump()
                )
                db.add(db_ioc)
                created_count += 1

        except Exception as e:
            errors.append({"value": ioc_data.value, "error": str(e)})

    # Update feed IOC count
    feed.ioc_count = db.query(func.count(ThreatIntelIOC.id)).filter(
        ThreatIntelIOC.feed_id == feed.id,
        ThreatIntelIOC.is_active == True
    ).scalar()

    db.commit()

    return {
        "feed_id": str(bulk_data.feed_id),
        "created": created_count,
        "updated": updated_count,
        "errors": len(errors),
        "error_details": errors[:10]  # Limit error details
    }


@router.get("/iocs/{ioc_id}", response_model=ThreatIntelIOCSchema)
def get_ioc(
    ioc_id: UUID,
    context: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get IOC by ID"""
    ioc = db.query(ThreatIntelIOC).filter(ThreatIntelIOC.id == ioc_id).first()

    if not ioc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IOC {ioc_id} not found"
        )

    # Validate access
    if ioc.tenant_id and not context.can_access_tenant(ioc.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
        )

    return ioc


@router.patch("/iocs/{ioc_id}", response_model=ThreatIntelIOCSchema)
def update_ioc(
    ioc_id: UUID,
    ioc_update: ThreatIntelIOCUpdate,
    context: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Update IOC"""
    ioc = db.query(ThreatIntelIOC).filter(ThreatIntelIOC.id == ioc_id).first()

    if not ioc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IOC {ioc_id} not found"
        )

    # Validate access
    if ioc.tenant_id:
        if not context.can_access_tenant(ioc.tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
    elif not context.is_super_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can modify global IOCs"
        )

    # Apply updates
    update_data = ioc_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ioc, field, value)

    ioc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ioc)

    return ioc


@router.delete("/iocs/{ioc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ioc(
    ioc_id: UUID,
    context: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Delete (deactivate) IOC"""
    ioc = db.query(ThreatIntelIOC).filter(ThreatIntelIOC.id == ioc_id).first()

    if not ioc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IOC {ioc_id} not found"
        )

    # Validate access
    if ioc.tenant_id:
        if not context.can_access_tenant(ioc.tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
    elif not context.is_super_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can delete global IOCs"
        )

    # Soft delete
    ioc.is_active = False
    ioc.updated_at = datetime.utcnow()

    # Update feed IOC count
    feed = db.query(ThreatIntelFeed).filter(ThreatIntelFeed.id == ioc.feed_id).first()
    if feed:
        feed.ioc_count = db.query(func.count(ThreatIntelIOC.id)).filter(
            ThreatIntelIOC.feed_id == feed.id,
            ThreatIntelIOC.is_active == True
        ).scalar()

    db.commit()
    return None


@router.get("/iocs/search/{value}", response_model=IOCSearchResult)
def search_ioc(
    value: str,
    ioc_type: Optional[IOCType] = Query(None, description="Filter by IOC type"),
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Search for IOCs by value

    **Use cases**:
    - Check if an IP/domain/hash is known malicious
    - Enrich alerts with threat intelligence
    """
    query = db.query(ThreatIntelIOC).filter(
        ThreatIntelIOC.value.ilike(f"%{value}%"),
        ThreatIntelIOC.is_active == True
    )

    if ioc_type:
        query = query.filter(ThreatIntelIOC.ioc_type == ioc_type)

    # Apply tenant filtering
    if context.user and not context.is_hubsec_staff():
        user_tenant_ids = [t.id for t in context.user.tenants]
        query = query.filter(
            or_(
                ThreatIntelIOC.tenant_id.in_(user_tenant_ids),
                ThreatIntelIOC.tenant_id == None  # Global IOCs
            )
        )

    # Filter expired IOCs
    query = query.filter(
        or_(
            ThreatIntelIOC.expiration_date == None,
            ThreatIntelIOC.expiration_date > datetime.utcnow()
        )
    )

    matches = query.limit(100).all()

    return IOCSearchResult(
        query=value,
        query_type=ioc_type,
        matches=matches,
        match_count=len(matches)
    )


@router.get("/stats", response_model=dict)
def get_ti_stats(
    tenant_id: Optional[UUID] = Query(None, description="Filter by tenant"),
    context: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get threat intelligence statistics

    **Returns**:
    - Total feeds and IOCs
    - IOCs by type and severity
    - Recent matches
    - Feed health status
    """
    # Build base query
    ioc_query = db.query(ThreatIntelIOC).filter(ThreatIntelIOC.is_active == True)
    feed_query = db.query(ThreatIntelFeed)

    # Apply tenant filtering
    if context.user and not context.is_hubsec_staff():
        user_tenant_ids = [t.id for t in context.user.tenants]
        ioc_query = ioc_query.filter(
            or_(
                ThreatIntelIOC.tenant_id.in_(user_tenant_ids),
                ThreatIntelIOC.tenant_id == None
            )
        )
        feed_query = feed_query.filter(
            or_(
                ThreatIntelFeed.tenant_id.in_(user_tenant_ids),
                ThreatIntelFeed.is_global == True
            )
        )
    elif tenant_id:
        ioc_query = ioc_query.filter(
            or_(
                ThreatIntelIOC.tenant_id == tenant_id,
                ThreatIntelIOC.tenant_id == None
            )
        )
        feed_query = feed_query.filter(
            or_(
                ThreatIntelFeed.tenant_id == tenant_id,
                ThreatIntelFeed.is_global == True
            )
        )

    # Get counts
    total_feeds = feed_query.count()
    enabled_feeds = feed_query.filter(ThreatIntelFeed.is_enabled == True).count()
    total_iocs = ioc_query.count()

    # IOCs by type
    iocs_by_type = {}
    for ioc_type in IOCType:
        count = ioc_query.filter(ThreatIntelIOC.ioc_type == ioc_type).count()
        iocs_by_type[ioc_type.value] = count

    # IOCs by severity
    iocs_by_severity = {}
    for severity in SeverityLevel:
        count = ioc_query.filter(ThreatIntelIOC.severity == severity).count()
        iocs_by_severity[severity.value] = count

    # Recent matches (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_matches = ioc_query.filter(
        ThreatIntelIOC.last_match_at >= yesterday
    ).count()

    # Top matched IOCs
    top_matched = ioc_query.filter(
        ThreatIntelIOC.match_count > 0
    ).order_by(
        ThreatIntelIOC.match_count.desc()
    ).limit(10).all()

    return {
        "feeds": {
            "total": total_feeds,
            "enabled": enabled_feeds,
            "disabled": total_feeds - enabled_feeds
        },
        "iocs": {
            "total": total_iocs,
            "by_type": iocs_by_type,
            "by_severity": iocs_by_severity
        },
        "matches": {
            "recent_24h": recent_matches,
            "top_matched_iocs": [
                {
                    "id": str(ioc.id),
                    "type": ioc.ioc_type,
                    "value": ioc.value[:50],
                    "match_count": ioc.match_count,
                    "severity": ioc.severity
                }
                for ioc in top_matched
            ]
        }
    }
