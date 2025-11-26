"""
Compliance Reporting API Endpoints
Generate compliance and operational reports
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta

from backend.app.database_multitenant import get_db
from backend.app.services.reporting_engine import generate_report
from backend.app.middleware.tenant import (
    require_auth,
    get_tenant_context,
    TenantContext
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{tenant_id}/monthly")
def get_monthly_report(
    tenant_id: UUID,
    start_date: Optional[datetime] = Query(None, description="Report start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Report end date (ISO format)"),
    context: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Generate monthly SOC activity report

    **Includes**:
    - Alert statistics (total, by severity, by status)
    - Incident and case metrics
    - Mean Time To Resolve (MTTR)
    - Top affected assets
    - Top alert sources
    - Threat intelligence matches

    **Default Period**: Last 30 days
    """
    # Validate access
    if not context.can_access_tenant(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
        )

    try:
        report = generate_report(
            db=db,
            report_type="monthly",
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date
        )
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating report: {str(e)}"
        )


@router.get("/{tenant_id}/pci-dss")
def get_pci_dss_report(
    tenant_id: UUID,
    start_date: Optional[datetime] = Query(None, description="Report start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Report end date (ISO format)"),
    context: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Generate PCI DSS compliance monitoring report

    **Covers**:
    - Requirement 10: Access monitoring and logging
    - Requirement 6.2: Vulnerability management
    - Requirement 12.10: Incident response

    **Default Period**: Last 90 days (quarterly)

    **Note**: This report aids compliance but does not guarantee PCI DSS certification
    """
    # Validate access
    if not context.can_access_tenant(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
        )

    try:
        report = generate_report(
            db=db,
            report_type="pci_dss",
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date
        )
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating report: {str(e)}"
        )


@router.get("/{tenant_id}/gdpr")
def get_gdpr_report(
    tenant_id: UUID,
    start_date: Optional[datetime] = Query(None, description="Report start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Report end date (ISO format)"),
    context: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Generate GDPR compliance report

    **Covers**:
    - Article 32: Security of processing
    - Article 33: Data breach notification (72-hour rule)
    - Article 34: Communication to data subjects

    **Default Period**: Last 30 days

    **Critical**: Data breaches must be reported within 72 hours to supervisory authority
    """
    # Validate access
    if not context.can_access_tenant(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
        )

    try:
        report = generate_report(
            db=db,
            report_type="gdpr",
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date
        )
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating report: {str(e)}"
        )


@router.get("/{tenant_id}/popia")
def get_popia_report(
    tenant_id: UUID,
    start_date: Optional[datetime] = Query(None, description="Report start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Report end date (ISO format)"),
    context: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Generate POPIA (Protection of Personal Information Act) compliance report

    **Covers**:
    - Section 19: Security safeguards
    - Section 22: Notification of security compromises
    - Access control monitoring

    **Default Period**: Last 30 days

    **Applicable**: South African organizations processing personal information
    """
    # Validate access
    if not context.can_access_tenant(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
        )

    try:
        report = generate_report(
            db=db,
            report_type="popia",
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date
        )
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating report: {str(e)}"
        )


@router.get("/{tenant_id}/threat-intel")
def get_threat_intel_report(
    tenant_id: UUID,
    start_date: Optional[datetime] = Query(None, description="Report start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Report end date (ISO format)"),
    context: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Generate threat intelligence summary report

    **Includes**:
    - IOC matches and trends
    - Threat actor activity
    - MITRE ATT&CK technique coverage
    - Top matched indicators

    **Default Period**: Last 7 days (weekly)
    """
    # Validate access
    if not context.can_access_tenant(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
        )

    try:
        report = generate_report(
            db=db,
            report_type="threat_intel",
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date
        )
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating report: {str(e)}"
        )


@router.get("/{tenant_id}/custom")
def get_custom_report(
    tenant_id: UUID,
    report_type: str = Query(..., description="Report type: monthly, pci_dss, gdpr, popia, threat_intel"),
    start_date: Optional[datetime] = Query(None, description="Report start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Report end date (ISO format)"),
    format: str = Query("json", description="Output format: json, html (future)"),
    context: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Generate custom report with flexible parameters

    **Supported Types**:
    - monthly: Monthly SOC activity
    - pci_dss: PCI DSS compliance
    - gdpr: GDPR compliance
    - popia: POPIA compliance
    - threat_intel: Threat intelligence summary

    **Future**: Support for HTML/PDF export
    """
    # Validate access
    if not context.can_access_tenant(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
        )

    # Validate report type
    valid_types = ["monthly", "pci_dss", "gdpr", "popia", "threat_intel"]
    if report_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid report type. Must be one of: {', '.join(valid_types)}"
        )

    # Validate format
    if format not in ["json", "html"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format. Must be 'json' or 'html'"
        )

    if format == "html":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="HTML export not yet implemented. Use format=json"
        )

    try:
        report = generate_report(
            db=db,
            report_type=report_type,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date
        )
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating report: {str(e)}"
        )


@router.get("/available-types")
def get_available_report_types(
    context: TenantContext = Depends(require_auth)
):
    """
    Get list of available report types and their descriptions
    """
    return {
        "report_types": [
            {
                "type": "monthly",
                "name": "Monthly SOC Activity Report",
                "description": "Comprehensive monthly summary of alerts, incidents, and cases",
                "default_period_days": 30,
                "categories": ["operational", "metrics"]
            },
            {
                "type": "pci_dss",
                "name": "PCI DSS Compliance Report",
                "description": "Payment Card Industry Data Security Standard compliance monitoring",
                "default_period_days": 90,
                "categories": ["compliance", "security"],
                "covers": ["Requirement 10", "Requirement 6.2", "Requirement 12.10"]
            },
            {
                "type": "gdpr",
                "name": "GDPR Compliance Report",
                "description": "General Data Protection Regulation compliance and breach monitoring",
                "default_period_days": 30,
                "categories": ["compliance", "privacy"],
                "covers": ["Article 32", "Article 33", "Article 34"]
            },
            {
                "type": "popia",
                "name": "POPIA Compliance Report",
                "description": "Protection of Personal Information Act (South Africa) compliance",
                "default_period_days": 30,
                "categories": ["compliance", "privacy"],
                "covers": ["Section 19", "Section 22"]
            },
            {
                "type": "threat_intel",
                "name": "Threat Intelligence Summary",
                "description": "IOC matches, threat actors, and MITRE ATT&CK coverage",
                "default_period_days": 7,
                "categories": ["threat-intelligence", "security"]
            }
        ]
    }
