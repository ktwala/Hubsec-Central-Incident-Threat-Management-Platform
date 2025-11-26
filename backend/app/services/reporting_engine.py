"""
Compliance Reporting Engine
Generates compliance reports for PCI DSS, GDPR, POPIA, and general SOC metrics
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from uuid import UUID

from backend.app.models.models_multitenant import (
    Tenant,
    Alert,
    Incident,
    Case,
    User,
    Asset,
    ThreatIntelIOC,
    SeverityLevel,
    IncidentStatus,
    CaseStatus,
    AlertStatus
)


class ReportingEngine:
    """
    Service for generating compliance and operational reports
    """

    def __init__(self, db: Session):
        self.db = db

    def generate_monthly_report(
        self,
        tenant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate monthly SOC activity report

        Args:
            tenant_id: Tenant UUID
            start_date: Report start date (defaults to 30 days ago)
            end_date: Report end date (defaults to now)

        Returns:
            Monthly report data
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Get tenant info
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Alert metrics
        alert_query = self.db.query(Alert).filter(
            Alert.tenant_id == tenant_id,
            Alert.created_at >= start_date,
            Alert.created_at <= end_date
        )

        total_alerts = alert_query.count()
        critical_alerts = alert_query.filter(Alert.severity == SeverityLevel.CRITICAL).count()
        high_alerts = alert_query.filter(Alert.severity == SeverityLevel.HIGH).count()
        ti_matched_alerts = alert_query.filter(Alert.ti_matched == True).count()

        # Alerts by status
        alerts_by_status = {
            status.value: alert_query.filter(Alert.status == status).count()
            for status in AlertStatus
        }

        # Top 10 alert sources
        top_sources = self.db.query(
            Alert.source,
            func.count(Alert.id).label('count')
        ).filter(
            Alert.tenant_id == tenant_id,
            Alert.created_at >= start_date,
            Alert.created_at <= end_date
        ).group_by(Alert.source).order_by(func.count(Alert.id).desc()).limit(10).all()

        # Incident metrics
        incident_query = self.db.query(Incident).filter(
            Incident.tenant_id == tenant_id,
            Incident.created_at >= start_date,
            Incident.created_at <= end_date
        )

        total_incidents = incident_query.count()
        open_incidents = incident_query.filter(
            Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS])
        ).count()
        resolved_incidents = incident_query.filter(
            Incident.status == IncidentStatus.RESOLVED
        ).count()

        # Case metrics
        case_query = self.db.query(Case).filter(
            Case.tenant_id == tenant_id,
            Case.created_at >= start_date,
            Case.created_at <= end_date
        )

        total_cases = case_query.count()
        open_cases = case_query.filter(
            Case.status.in_([CaseStatus.OPEN, CaseStatus.IN_PROGRESS])
        ).count()
        closed_cases = case_query.filter(Case.status == CaseStatus.CLOSED).count()

        # Calculate MTTR (Mean Time To Resolve) for closed cases
        closed_cases_with_times = case_query.filter(
            Case.status == CaseStatus.CLOSED,
            Case.closed_at != None
        ).all()

        mttr_hours = 0
        if closed_cases_with_times:
            total_resolution_time = sum(
                (case.closed_at - case.created_at).total_seconds() / 3600
                for case in closed_cases_with_times
            )
            mttr_hours = total_resolution_time / len(closed_cases_with_times)

        # Top 10 affected assets
        top_assets = self.db.query(
            Asset.hostname,
            Asset.criticality,
            func.count(Alert.id).label('alert_count')
        ).join(
            Alert, Alert.asset_id == Asset.id
        ).filter(
            Asset.tenant_id == tenant_id,
            Alert.created_at >= start_date,
            Alert.created_at <= end_date
        ).group_by(
            Asset.hostname,
            Asset.criticality
        ).order_by(
            func.count(Alert.id).desc()
        ).limit(10).all()

        # Build report
        return {
            "report_type": "monthly_summary",
            "tenant": {
                "id": str(tenant_id),
                "name": tenant.name,
                "code": tenant.code
            },
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": (end_date - start_date).days
            },
            "alerts": {
                "total": total_alerts,
                "by_severity": {
                    "critical": critical_alerts,
                    "high": high_alerts,
                    "medium": alert_query.filter(Alert.severity == SeverityLevel.MEDIUM).count(),
                    "low": alert_query.filter(Alert.severity == SeverityLevel.LOW).count(),
                    "info": alert_query.filter(Alert.severity == SeverityLevel.INFO).count()
                },
                "by_status": alerts_by_status,
                "threat_intel_matched": ti_matched_alerts,
                "top_sources": [
                    {"source": source, "count": count}
                    for source, count in top_sources
                ]
            },
            "incidents": {
                "total": total_incidents,
                "open": open_incidents,
                "resolved": resolved_incidents,
                "resolution_rate": (resolved_incidents / total_incidents * 100) if total_incidents > 0 else 0
            },
            "cases": {
                "total": total_cases,
                "open": open_cases,
                "closed": closed_cases,
                "mttr_hours": round(mttr_hours, 2)
            },
            "top_assets": [
                {
                    "hostname": asset.hostname,
                    "criticality": asset.criticality,
                    "alert_count": asset.alert_count
                }
                for asset in top_assets
            ],
            "generated_at": datetime.utcnow().isoformat()
        }

    def generate_pci_dss_report(
        self,
        tenant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate PCI DSS compliance monitoring report

        Focuses on:
        - Security incident tracking (Requirement 12.10)
        - Access monitoring (Requirement 10)
        - Vulnerability management (Requirement 6.2)
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=90)  # Quarterly

        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

        # PCI-relevant alerts
        pci_categories = ['authentication', 'access_control', 'data_breach', 'intrusion']
        pci_alerts = self.db.query(Alert).filter(
            Alert.tenant_id == tenant_id,
            Alert.created_at >= start_date,
            Alert.created_at <= end_date,
            Alert.category.in_(pci_categories)
        )

        # Critical incidents (must be tracked per PCI DSS 12.10)
        critical_incidents = self.db.query(Incident).filter(
            Incident.tenant_id == tenant_id,
            Incident.created_at >= start_date,
            Incident.created_at <= end_date,
            Incident.severity == SeverityLevel.CRITICAL
        ).all()

        # Authentication failures
        auth_failures = self.db.query(Alert).filter(
            Alert.tenant_id == tenant_id,
            Alert.created_at >= start_date,
            Alert.created_at <= end_date,
            Alert.category == 'authentication',
            Alert.rule_description.ilike('%failed%')
        ).count()

        return {
            "report_type": "pci_dss_compliance",
            "tenant": {"id": str(tenant_id), "name": tenant.name},
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "requirement_10_access_monitoring": {
                "total_access_events": pci_alerts.count(),
                "authentication_failures": auth_failures,
                "privileged_access_events": pci_alerts.filter(
                    Alert.rule_description.ilike('%admin%')
                ).count()
            },
            "requirement_12_10_incident_response": {
                "critical_incidents": len(critical_incidents),
                "incidents_detail": [
                    {
                        "id": str(inc.id),
                        "title": inc.title,
                        "severity": inc.severity.value,
                        "status": inc.status.value,
                        "created_at": inc.created_at.isoformat(),
                        "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None
                    }
                    for inc in critical_incidents
                ]
            },
            "requirement_6_2_vulnerability_management": {
                "vulnerability_alerts": pci_alerts.filter(
                    Alert.category == 'vulnerability'
                ).count(),
                "patching_events": 0  # Placeholder - would need patch management integration
            },
            "data_breach_indicators": {
                "potential_breaches": pci_alerts.filter(
                    Alert.category == 'data_breach'
                ).count(),
                "data_exfiltration_attempts": pci_alerts.filter(
                    or_(
                        Alert.rule_description.ilike('%exfiltration%'),
                        Alert.rule_description.ilike('%data transfer%')
                    )
                ).count()
            },
            "generated_at": datetime.utcnow().isoformat(),
            "compliance_notes": [
                "This report aids PCI DSS Requirements 10, 6.2, and 12.10",
                "Regular review of critical incidents is required quarterly",
                "Maintain logs for at least 1 year with 3 months online"
            ]
        }

    def generate_gdpr_report(
        self,
        tenant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate GDPR compliance report

        Focuses on:
        - Data breach detection and notification (Article 33)
        - Security incident monitoring
        - Access controls and monitoring
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

        # Potential data breaches (must notify within 72 hours)
        breach_alerts = self.db.query(Alert).filter(
            Alert.tenant_id == tenant_id,
            Alert.created_at >= start_date,
            Alert.created_at <= end_date,
            or_(
                Alert.category == 'data_breach',
                Alert.rule_description.ilike('%breach%'),
                Alert.rule_description.ilike('%unauthorized access%'),
                Alert.rule_description.ilike('%data exposure%')
            )
        )

        # Critical breaches requiring notification
        critical_breaches = breach_alerts.filter(
            Alert.severity.in_([SeverityLevel.CRITICAL, SeverityLevel.HIGH])
        ).all()

        # Access control events
        access_events = self.db.query(Alert).filter(
            Alert.tenant_id == tenant_id,
            Alert.created_at >= start_date,
            Alert.created_at <= end_date,
            Alert.category == 'access_control'
        ).count()

        # Unauthorized access attempts
        unauthorized_access = self.db.query(Alert).filter(
            Alert.tenant_id == tenant_id,
            Alert.created_at >= start_date,
            Alert.created_at <= end_date,
            or_(
                Alert.rule_description.ilike('%unauthorized%'),
                Alert.rule_description.ilike('%forbidden%'),
                Alert.rule_description.ilike('%access denied%')
            )
        ).count()

        return {
            "report_type": "gdpr_compliance",
            "tenant": {"id": str(tenant_id), "name": tenant.name},
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "article_33_breach_notification": {
                "potential_breaches": breach_alerts.count(),
                "critical_breaches_requiring_notification": len(critical_breaches),
                "breaches_detail": [
                    {
                        "id": str(alert.id),
                        "severity": alert.severity.value,
                        "description": alert.rule_description,
                        "detected_at": alert.timestamp.isoformat(),
                        "time_to_detect_hours": (alert.created_at - alert.timestamp).total_seconds() / 3600,
                        "notification_deadline": (alert.timestamp + timedelta(hours=72)).isoformat()
                    }
                    for alert in critical_breaches
                ]
            },
            "article_32_security_measures": {
                "total_security_events": access_events,
                "unauthorized_access_attempts": unauthorized_access,
                "encryption_failures": 0,  # Placeholder
                "authentication_failures": self.db.query(Alert).filter(
                    Alert.tenant_id == tenant_id,
                    Alert.created_at >= start_date,
                    Alert.created_at <= end_date,
                    Alert.category == 'authentication',
                    Alert.rule_description.ilike('%failed%')
                ).count()
            },
            "data_subject_impact": {
                "high_risk_incidents": len([b for b in critical_breaches if b.severity == SeverityLevel.CRITICAL]),
                "potentially_affected_systems": len(set(
                    alert.hostname for alert in critical_breaches if alert.hostname
                ))
            },
            "generated_at": datetime.utcnow().isoformat(),
            "compliance_notes": [
                "Data breaches must be reported to supervisory authority within 72 hours (Article 33)",
                "High-risk breaches must also be communicated to affected data subjects (Article 34)",
                "Maintain records of all personal data breaches (Article 33.5)"
            ]
        }

    def generate_popia_report(
        self,
        tenant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate POPIA (Protection of Personal Information Act) compliance report

        Focuses on:
        - Security safeguards (Section 19)
        - Data breach notifications (Section 22)
        - Access controls and monitoring
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

        # Security incidents affecting personal information
        popi_incidents = self.db.query(Incident).filter(
            Incident.tenant_id == tenant_id,
            Incident.created_at >= start_date,
            Incident.created_at <= end_date,
            Incident.severity.in_([SeverityLevel.HIGH, SeverityLevel.CRITICAL])
        ).all()

        # Access control violations
        access_violations = self.db.query(Alert).filter(
            Alert.tenant_id == tenant_id,
            Alert.created_at >= start_date,
            Alert.created_at <= end_date,
            or_(
                Alert.rule_description.ilike('%unauthorized%'),
                Alert.rule_description.ilike('%access violation%')
            )
        ).count()

        return {
            "report_type": "popia_compliance",
            "tenant": {"id": str(tenant_id), "name": tenant.name},
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "section_19_security_safeguards": {
                "security_incidents": len(popi_incidents),
                "access_violations": access_violations,
                "security_measures_active": True,  # Placeholder - verify from config
                "incidents_detail": [
                    {
                        "id": str(inc.id),
                        "title": inc.title,
                        "severity": inc.severity.value,
                        "created_at": inc.created_at.isoformat(),
                        "status": inc.status.value
                    }
                    for inc in popi_incidents
                ]
            },
            "section_22_data_breach_notification": {
                "breaches_requiring_notification": len([
                    inc for inc in popi_incidents
                    if inc.severity == SeverityLevel.CRITICAL
                ]),
                "regulator_notifications_required": True if any(
                    inc.severity == SeverityLevel.CRITICAL for inc in popi_incidents
                ) else False
            },
            "access_monitoring": {
                "total_access_events": self.db.query(Alert).filter(
                    Alert.tenant_id == tenant_id,
                    Alert.created_at >= start_date,
                    Alert.created_at <= end_date,
                    Alert.category == 'access_control'
                ).count(),
                "unauthorized_attempts": access_violations
            },
            "generated_at": datetime.utcnow().isoformat(),
            "compliance_notes": [
                "POPIA requires reasonable security safeguards (Section 19)",
                "Data breaches must be reported to Information Regulator (Section 22)",
                "Data subjects must be notified if breach causes harm (Section 22)",
                "Maintain audit trails of processing activities"
            ]
        }

    def generate_threat_intel_summary(
        self,
        tenant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate threat intelligence summary report

        Includes:
        - IOC matches and trends
        - Threat actor activity
        - MITRE ATT&CK technique coverage
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=7)  # Weekly

        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

        # TI-matched alerts
        ti_alerts = self.db.query(Alert).filter(
            Alert.tenant_id == tenant_id,
            Alert.created_at >= start_date,
            Alert.created_at <= end_date,
            Alert.ti_matched == True
        ).all()

        # Extract IOC matches
        ioc_types = {}
        threat_actors = set()
        mitre_techniques = set()

        for alert in ti_alerts:
            if alert.ioc_matches:
                for match in alert.ioc_matches:
                    ioc_type = match.get('ioc_type')
                    if ioc_type:
                        ioc_types[ioc_type] = ioc_types.get(ioc_type, 0) + 1

                    threat_actor = match.get('threat_actor')
                    if threat_actor:
                        threat_actors.add(threat_actor)

                    mitre_ids = match.get('mitre_attack_ids', [])
                    mitre_techniques.update(mitre_ids)

        return {
            "report_type": "threat_intelligence_summary",
            "tenant": {"id": str(tenant_id), "name": tenant.name},
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "total_ti_matched_alerts": len(ti_alerts),
                "unique_ioc_types_matched": len(ioc_types),
                "threat_actors_observed": list(threat_actors),
                "mitre_attack_techniques": list(mitre_techniques)
            },
            "ioc_matches_by_type": ioc_types,
            "top_matched_indicators": [
                {
                    "alert_id": str(alert.id),
                    "timestamp": alert.timestamp.isoformat(),
                    "severity": alert.severity.value,
                    "matches": len(alert.ioc_matches) if alert.ioc_matches else 0,
                    "description": alert.rule_description
                }
                for alert in sorted(ti_alerts, key=lambda a: len(a.ioc_matches or []), reverse=True)[:10]
            ],
            "generated_at": datetime.utcnow().isoformat()
        }


def generate_report(
    db: Session,
    report_type: str,
    tenant_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Convenience function to generate a report

    Args:
        db: Database session
        report_type: Type of report (monthly, pci_dss, gdpr, popia, threat_intel)
        tenant_id: Tenant UUID
        start_date: Report start date
        end_date: Report end date

    Returns:
        Report data dictionary
    """
    engine = ReportingEngine(db)

    if report_type == "monthly":
        return engine.generate_monthly_report(tenant_id, start_date, end_date)
    elif report_type == "pci_dss":
        return engine.generate_pci_dss_report(tenant_id, start_date, end_date)
    elif report_type == "gdpr":
        return engine.generate_gdpr_report(tenant_id, start_date, end_date)
    elif report_type == "popia":
        return engine.generate_popia_report(tenant_id, start_date, end_date)
    elif report_type == "threat_intel":
        return engine.generate_threat_intel_summary(tenant_id, start_date, end_date)
    else:
        raise ValueError(f"Unknown report type: {report_type}")
