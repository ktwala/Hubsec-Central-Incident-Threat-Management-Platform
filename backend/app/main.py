"""
Hubsec SOC Platform - Main FastAPI Application
Central Incident & Threat Management Platform
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import os

from backend.app.models.models import Base
from backend.app.database import engine, get_db, DATABASE_URL
from backend.app.api.v1 import incidents, cases, alerts, users

# Create all tables
Base.metadata.create_all(bind=engine)


# Create FastAPI application
app = FastAPI(
    title="Hubsec SOC Platform",
    description="Central Incident & Threat Management Platform for Security Operations Centers",
    version="1.0.0",
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
app.include_router(
    incidents.router,
    prefix="/api/v1/incidents",
    tags=["incidents"]
)

app.include_router(
    cases.router,
    prefix="/api/v1/cases",
    tags=["cases"]
)

app.include_router(
    alerts.router,
    prefix="/api/v1/alerts",
    tags=["alerts"]
)

app.include_router(
    users.router,
    prefix="/api/v1/users",
    tags=["users"]
)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "Hubsec SOC Platform",
        "version": "1.0.0",
        "description": "Central Incident & Threat Management Platform",
        "docs": "/api/docs",
        "endpoints": {
            "incidents": "/api/v1/incidents",
            "cases": "/api/v1/cases",
            "alerts": "/api/v1/alerts",
            "users": "/api/v1/users",
            "health": "/health",
            "stats": "/api/v1/stats"
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
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )


# Dashboard statistics endpoint
@app.get("/api/v1/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Get dashboard statistics and overview
    Returns counts and recent items for all entities
    """
    from backend.app.models.models import (
        Incident, Case, Alert,
        IncidentStatus, CaseStatus, AlertStatus, SeverityLevel
    )
    from sqlalchemy import func

    # Get counts
    total_incidents = db.query(func.count(Incident.id)).scalar()
    open_incidents = db.query(func.count(Incident.id)).filter(
        Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS])
    ).scalar()

    total_cases = db.query(func.count(Case.id)).scalar()
    open_cases = db.query(func.count(Case.id)).filter(
        Case.status.in_([CaseStatus.OPEN, CaseStatus.IN_PROGRESS])
    ).scalar()

    total_alerts = db.query(func.count(Alert.id)).scalar()
    new_alerts = db.query(func.count(Alert.id)).filter(
        Alert.status == AlertStatus.NEW
    ).scalar()

    # Alerts by severity
    alerts_by_severity = {}
    for severity in SeverityLevel:
        count = db.query(func.count(Alert.id)).filter(
            Alert.severity == severity
        ).scalar()
        alerts_by_severity[severity.value] = count

    # Incidents by status
    incidents_by_status = {}
    for status in IncidentStatus:
        count = db.query(func.count(Incident.id)).filter(
            Incident.status == status
        ).scalar()
        incidents_by_status[status.value] = count

    # Cases by status
    cases_by_status = {}
    for status in CaseStatus:
        count = db.query(func.count(Case.id)).filter(
            Case.status == status
        ).scalar()
        cases_by_status[status.value] = count

    # Get recent items
    recent_incidents = db.query(Incident).order_by(
        Incident.created_at.desc()
    ).limit(5).all()

    recent_cases = db.query(Case).order_by(
        Case.created_at.desc()
    ).limit(5).all()

    recent_alerts = db.query(Alert).order_by(
        Alert.timestamp.desc()
    ).limit(10).all()

    return {
        "total_incidents": total_incidents,
        "open_incidents": open_incidents,
        "total_cases": total_cases,
        "open_cases": open_cases,
        "total_alerts": total_alerts,
        "new_alerts": new_alerts,
        "alerts_by_severity": alerts_by_severity,
        "incidents_by_status": incidents_by_status,
        "cases_by_status": cases_by_status,
        "recent_incidents": [
            {
                "id": i.id,
                "title": i.title,
                "severity": i.severity.value,
                "status": i.status.value,
                "created_at": i.created_at.isoformat()
            }
            for i in recent_incidents
        ],
        "recent_cases": [
            {
                "id": c.id,
                "title": c.title,
                "priority": c.priority.value,
                "status": c.status.value,
                "alert_count": len(c.alerts),
                "created_at": c.created_at.isoformat()
            }
            for c in recent_cases
        ],
        "recent_alerts": [
            {
                "id": a.id,
                "source": a.source,
                "severity": a.severity.value,
                "rule_description": a.rule_description,
                "timestamp": a.timestamp.isoformat()
            }
            for a in recent_alerts
        ]
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    print("=" * 50)
    print("🚀 Hubsec SOC Platform Starting...")
    print("=" * 50)
    print(f"📊 Database: {DATABASE_URL}")
    print(f"📝 API Docs: http://localhost:8000/api/docs")
    print(f"🏥 Health Check: http://localhost:8000/health")
    print("=" * 50)


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks"""
    print("🛑 Hubsec SOC Platform Shutting Down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
