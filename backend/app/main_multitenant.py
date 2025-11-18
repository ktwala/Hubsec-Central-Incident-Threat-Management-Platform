"""
Hubsec SOC Platform - Multi-Tenant FastAPI Application
Central Incident & Threat Management Platform with Multi-Tenant Support

IMPORTANT: This version requires PostgreSQL
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import os

from backend.app.models.models_multitenant import Base
from backend.app.database_multitenant import engine, get_db, DATABASE_URL, test_connection, enable_uuid_extension
from backend.app.api.v1 import tenants, source_systems, assets, playbooks

# Test database connection and enable UUID extension
print("=" * 70)
print("Hubsec SOC Platform - Multi-Tenant Mode")
print("=" * 70)
if not test_connection():
    print("\n❌ Database connection failed!")
    print("Make sure PostgreSQL is running and DATABASE_URL is correct.")
    print(f"Current DATABASE_URL: {DATABASE_URL}")
    exit(1)

# Ensure UUID extension is enabled
try:
    enable_uuid_extension()
except Exception as e:
    print(f"⚠️  Warning: Could not enable UUID extension: {e}")

# Create all tables
print("\nCreating database tables...")
Base.metadata.create_all(bind=engine)
print("✅ Tables created\n")


# Create FastAPI application
app = FastAPI(
    title="Hubsec SOC Platform (Multi-Tenant)",
    description="Central Incident & Threat Management Platform for Security Operations Centers - Multi-Tenant Edition",
    version="2.0.0-multitenant",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(tenants.router, prefix="/api/v1")
app.include_router(source_systems.router, prefix="/api/v1")
app.include_router(assets.router, prefix="/api/v1")
app.include_router(playbooks.router, prefix="/api/v1")

# TODO: Include updated routers for alerts, incidents, cases, users
# These need to be updated to support tenant filtering
# app.include_router(incidents_multitenant.router, prefix="/api/v1")
# app.include_router(cases_multitenant.router, prefix="/api/v1")
# app.include_router(alerts_multitenant.router, prefix="/api/v1")
# app.include_router(users_multitenant.router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "Hubsec SOC Platform (Multi-Tenant)",
        "version": "2.0.0-multitenant",
        "description": "Central Incident & Threat Management Platform - Multi-Tenant Edition",
        "database": "PostgreSQL (required)",
        "features": [
            "Multi-tenant organization support",
            "Source system integrations (Wazuh, IRIS, Jira)",
            "Asset management",
            "Playbook automation",
            "UUID primary keys",
            "PostgreSQL-optimized (INET, JSONB, ARRAY)"
        ],
        "docs": "/api/docs",
        "endpoints": {
            "tenants": "/api/v1/tenants",
            "source_systems": "/api/v1/source-systems",
            "assets": "/api/v1/assets",
            "playbooks": "/api/v1/playbooks",
            "health": "/health",
            "database_info": "/api/v1/info/database"
        },
        "authentication": {
            "method": "header-based (testing)",
            "headers": {
                "X-Tenant-ID": "UUID of tenant (optional for some endpoints)",
                "X-Tenant-Code": "Tenant code (alternative to X-Tenant-ID)",
                "X-User-ID": "UUID of user (for authentication)",
                "X-Username": "Username (alternative to X-User-ID)"
            },
            "note": "JWT authentication coming soon"
        }
    }


# Health check endpoint
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint
    Verifies API and database connectivity
    """
    try:
        # Test database connection
        result = db.execute(text("SELECT version();"))
        pg_version = result.scalar()

        # Check UUID extension
        result = db.execute(
            text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp');")
        )
        uuid_enabled = result.scalar()

        return {
            "status": "healthy",
            "database": "connected",
            "postgresql_version": pg_version,
            "uuid_extension": "enabled" if uuid_enabled else "disabled",
            "version": "2.0.0-multitenant"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database health check failed: {str(e)}"
        )


# Database info endpoint
@app.get("/api/v1/info/database")
async def database_info(db: Session = Depends(get_db)):
    """Get database information and table counts"""
    from backend.app.models.models_multitenant import (
        Tenant, User, SourceSystem, Asset, Alert, Incident, Case, Playbook
    )

    try:
        stats = {
            "database_url": DATABASE_URL.split("@")[1] if "@" in DATABASE_URL else DATABASE_URL,
            "tables": {
                "tenants": db.query(Tenant).count(),
                "users": db.query(User).count(),
                "source_systems": db.query(SourceSystem).count(),
                "assets": db.query(Asset).count(),
                "alerts": db.query(Alert).count(),
                "incidents": db.query(Incident).count(),
                "cases": db.query(Case).count(),
                "playbooks": db.query(Playbook).count(),
            }
        }
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get database info: {str(e)}"
        )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    print("🚀 Hubsec SOC Platform (Multi-Tenant) started successfully!")
    print(f"📊 Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")
    print(f"📖 API Documentation: http://localhost:8000/api/docs")
    print("=" * 70)


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    print("\n👋 Hubsec SOC Platform shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main_multitenant:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
