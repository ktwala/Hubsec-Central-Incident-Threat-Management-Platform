"""
Tenant-aware middleware for multi-tenant request handling
"""
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from backend.app.database_multitenant import get_db
from backend.app.models.models_multitenant import Tenant, User, UserRole


class TenantContext:
    """Tenant context for the current request"""

    def __init__(self, tenant: Optional[Tenant] = None, user: Optional[User] = None):
        self.tenant = tenant
        self.user = user

    def can_access_tenant(self, tenant_id: UUID) -> bool:
        """Check if user can access the given tenant"""
        if not self.user:
            return False

        # Super admins and Hubsec analysts can access all tenants
        if self.user.role in [UserRole.SUPER_ADMIN, UserRole.HUBSEC_ANALYST]:
            return True

        # Check if user has access to this tenant
        user_tenant_ids = [t.id for t in self.user.tenants]
        return tenant_id in user_tenant_ids

    def is_super_admin(self) -> bool:
        """Check if user is super admin"""
        return self.user and self.user.role == UserRole.SUPER_ADMIN

    def is_hubsec_staff(self) -> bool:
        """Check if user is Hubsec staff (super admin or analyst)"""
        return self.user and self.user.role in [UserRole.SUPER_ADMIN, UserRole.HUBSEC_ANALYST]


def get_tenant_from_header(request: Request, db: Session = Depends(get_db)) -> Optional[Tenant]:
    """
    Extract tenant from request header
    Expects header: X-Tenant-ID or X-Tenant-Code
    """
    # Try UUID tenant ID first
    tenant_id_str = request.headers.get("X-Tenant-ID")
    if tenant_id_str:
        try:
            tenant_id = UUID(tenant_id_str)
            tenant = db.query(Tenant).filter(
                Tenant.id == tenant_id,
                Tenant.is_active == True
            ).first()
            if tenant:
                return tenant
        except ValueError:
            pass  # Invalid UUID format

    # Try tenant code
    tenant_code = request.headers.get("X-Tenant-Code")
    if tenant_code:
        tenant = db.query(Tenant).filter(
            Tenant.code == tenant_code.upper(),
            Tenant.is_active == True
        ).first()
        if tenant:
            return tenant

    return None


async def get_current_tenant(
    request: Request,
    db: Session = Depends(get_db),
    require_tenant: bool = True
) -> Optional[Tenant]:
    """
    Dependency to get current tenant from request

    Args:
        request: FastAPI request object
        db: Database session
        require_tenant: If True, raises 400 if no tenant specified

    Returns:
        Tenant object or None

    Raises:
        HTTPException: If tenant not found or invalid
    """
    tenant = get_tenant_from_header(request, db)

    if not tenant and require_tenant:
        raise HTTPException(
            status_code=400,
            detail="Tenant not specified. Include X-Tenant-ID or X-Tenant-Code header."
        )

    return tenant


async def get_current_user_mock(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """
    Mock user authentication - returns user from X-User-ID header

    TODO: Replace with real JWT authentication

    For testing, use headers:
        X-User-ID: <uuid>
        OR
        X-Username: <username>
    """
    # Try user ID first
    user_id_str = request.headers.get("X-User-ID")
    if user_id_str:
        try:
            user_id = UUID(user_id_str)
            user = db.query(User).filter(
                User.id == user_id,
                User.is_active == True
            ).first()
            if user:
                return user
        except ValueError:
            pass

    # Try username
    username = request.headers.get("X-Username")
    if username:
        user = db.query(User).filter(
            User.username == username,
            User.is_active == True
        ).first()
        if user:
            return user

    return None


async def get_tenant_context(
    request: Request,
    db: Session = Depends(get_db),
    require_tenant: bool = False,
    require_auth: bool = False
) -> TenantContext:
    """
    Get full tenant context (tenant + user) for the request

    Args:
        request: FastAPI request
        db: Database session
        require_tenant: If True, raises error if no tenant
        require_auth: If True, raises error if no authenticated user

    Returns:
        TenantContext object

    Raises:
        HTTPException: If requirements not met
    """
    tenant = get_tenant_from_header(request, db)
    user = await get_current_user_mock(request, db)

    # Validate requirements
    if require_tenant and not tenant:
        raise HTTPException(
            status_code=400,
            detail="Tenant required. Include X-Tenant-ID or X-Tenant-Code header."
        )

    if require_auth and not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Include X-User-ID or X-Username header."
        )

    # Create context
    context = TenantContext(tenant=tenant, user=user)

    # If both tenant and user specified, verify access
    if tenant and user and not context.can_access_tenant(tenant.id):
        raise HTTPException(
            status_code=403,
            detail=f"User '{user.username}' does not have access to tenant '{tenant.code}'"
        )

    return context


def require_tenant(context: TenantContext = Depends(get_tenant_context)) -> Tenant:
    """
    Dependency that requires a tenant to be specified
    """
    if not context.tenant:
        raise HTTPException(
            status_code=400,
            detail="Tenant required. Include X-Tenant-ID or X-Tenant-Code header."
        )
    return context.tenant


def require_auth(context: TenantContext = Depends(get_tenant_context)) -> User:
    """
    Dependency that requires user authentication
    """
    if not context.user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Include X-User-ID or X-Username header."
        )
    return context.user


def require_super_admin(context: TenantContext = Depends(get_tenant_context)) -> User:
    """
    Dependency that requires super admin privileges
    """
    if not context.user:
        raise HTTPException(status_code=401, detail="Authentication required")

    if not context.is_super_admin():
        raise HTTPException(
            status_code=403,
            detail="Super admin privileges required"
        )

    return context.user


def require_hubsec_staff(context: TenantContext = Depends(get_tenant_context)) -> User:
    """
    Dependency that requires Hubsec staff privileges (super admin or analyst)
    """
    if not context.user:
        raise HTTPException(status_code=401, detail="Authentication required")

    if not context.is_hubsec_staff():
        raise HTTPException(
            status_code=403,
            detail="Hubsec staff privileges required"
        )

    return context.user
