"""
Case Management Engine
Handles automatic case creation, alert correlation, and case lifecycle
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from backend.app.models.models import (
    Alert, Case, Incident, Activity, User,
    CaseStatus, IncidentStatus, SeverityLevel, AlertStatus
)
from backend.app.schemas.schemas import CaseCreate, IncidentCreate


class CaseEngine:
    """
    Intelligent case management engine

    Features:
    - Automatic case creation from high-severity alerts
    - Alert correlation and grouping
    - Case priority calculation
    - Automatic incident escalation
    """

    def __init__(self, db: Session):
        """Initialize the case engine with database session"""
        self.db = db

    def process_new_alert(self, alert: Alert) -> Optional[Case]:
        """
        Process a new alert and determine if it should create/update a case

        Logic:
        1. Check if alert should create a new case (high severity)
        2. Try to correlate with existing open cases
        3. Create new case or add to existing case
        4. Check if case should be escalated to incident

        Args:
            alert: The new alert to process

        Returns:
            Case object if a case was created or updated, None otherwise
        """
        # Only process alerts that aren't already in a case
        if alert.status == AlertStatus.IN_CASE:
            return None

        # Check if alert meets criteria for case creation
        if not self._should_create_case(alert):
            return None

        # Try to find related open cases
        related_case = self._find_related_case(alert)

        if related_case:
            # Add alert to existing case
            self._add_alert_to_case(related_case, alert)
            return related_case
        else:
            # Create new case
            return self._create_case_from_alert(alert)

    def _should_create_case(self, alert: Alert) -> bool:
        """
        Determine if an alert should trigger case creation

        Criteria:
        - Severity is HIGH or CRITICAL
        - Or alert is part of certain categories (malware, intrusion, etc.)
        """
        if alert.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]:
            return True

        critical_categories = ['malware', 'intrusion', 'authentication', 'exploit']
        if alert.category and alert.category.lower() in critical_categories:
            return True

        return False

    def _find_related_case(self, alert: Alert) -> Optional[Case]:
        """
        Find an existing open case that this alert might be related to

        Correlation criteria (in order of priority):
        1. Same source IP within last 24 hours
        2. Same hostname within last 24 hours
        3. Same category and similar timeframe (6 hours)
        """
        time_threshold_24h = datetime.utcnow() - timedelta(hours=24)
        time_threshold_6h = datetime.utcnow() - timedelta(hours=6)

        # First, try to find cases with same source IP
        if alert.src_ip:
            related_case = self._find_case_by_criteria(
                ip_address=alert.src_ip,
                time_threshold=time_threshold_24h
            )
            if related_case:
                return related_case

        # Try to find cases with same hostname
        if alert.hostname:
            related_case = self._find_case_by_criteria(
                hostname=alert.hostname,
                time_threshold=time_threshold_24h
            )
            if related_case:
                return related_case

        # Try to find cases with same category
        if alert.category:
            related_case = self._find_case_by_criteria(
                category=alert.category,
                time_threshold=time_threshold_6h
            )
            if related_case:
                return related_case

        return None

    def _find_case_by_criteria(
        self,
        ip_address: Optional[str] = None,
        hostname: Optional[str] = None,
        category: Optional[str] = None,
        time_threshold: Optional[datetime] = None
    ) -> Optional[Case]:
        """Find a case matching the given criteria"""
        # Get open cases
        query = self.db.query(Case).filter(
            Case.status.in_([CaseStatus.OPEN, CaseStatus.IN_PROGRESS])
        )

        if time_threshold:
            query = query.filter(Case.created_at >= time_threshold)

        # Get cases with their alerts
        cases = query.all()

        for case in cases:
            for case_alert in case.alerts:
                # Check IP match
                if ip_address and case_alert.src_ip == ip_address:
                    return case

                # Check hostname match
                if hostname and case_alert.hostname == hostname:
                    return case

                # Check category match
                if category and case_alert.category == category:
                    return case

        return None

    def _create_case_from_alert(self, alert: Alert) -> Case:
        """
        Create a new case from an alert

        The case will automatically create an incident if it doesn't exist
        """
        # Generate case title from alert
        title = self._generate_case_title(alert)

        # Generate description
        description = self._generate_case_description(alert)

        # Find or create incident
        incident = self._find_or_create_incident(alert)

        # Create the case
        case = Case(
            title=title,
            description=description,
            priority=alert.severity,
            status=CaseStatus.OPEN,
            incident_id=incident.id,
            metadata={
                'auto_created': True,
                'source_alert_id': alert.id,
                'correlation_key': alert.src_ip or alert.hostname
            }
        )

        self.db.add(case)
        self.db.flush()  # Get the case ID

        # Add the alert to the case
        self._add_alert_to_case(case, alert)

        # Create activity log
        self._log_activity(
            case=case,
            action="case_created",
            description=f"Case automatically created from alert {alert.id}",
            metadata={'alert_id': alert.id}
        )

        self.db.commit()
        self.db.refresh(case)

        return case

    def _find_or_create_incident(self, alert: Alert) -> Incident:
        """
        Find an existing incident or create a new one for the alert

        Correlation logic:
        - Same category within last 7 days
        - Same severity level
        - Open status
        """
        time_threshold = datetime.utcnow() - timedelta(days=7)

        # Try to find existing open incident
        if alert.category:
            incident = self.db.query(Incident).filter(
                and_(
                    Incident.category == alert.category,
                    Incident.severity == alert.severity,
                    Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS]),
                    Incident.created_at >= time_threshold
                )
            ).first()

            if incident:
                return incident

        # Create new incident
        incident = Incident(
            title=self._generate_incident_title(alert),
            description=f"Automatically created from alert: {alert.rule_description}",
            severity=alert.severity,
            status=IncidentStatus.OPEN,
            source="Wazuh",
            source_id=alert.source_id,
            category=alert.category,
            detected_at=alert.timestamp,
            metadata={
                'auto_created': True,
                'source_alert_id': alert.id
            }
        )

        self.db.add(incident)
        self.db.flush()

        return incident

    def _add_alert_to_case(self, case: Case, alert: Alert):
        """Add an alert to a case and update alert status"""
        # Add alert to case
        if alert not in case.alerts:
            case.alerts.append(alert)

        # Update alert status
        alert.status = AlertStatus.IN_CASE

        # Update case priority if this alert is more severe
        if self._compare_severity(alert.severity, case.priority) > 0:
            old_priority = case.priority
            case.priority = alert.severity

            # Log priority change
            self._log_activity(
                case=case,
                action="priority_changed",
                description=f"Priority escalated from {old_priority} to {alert.severity} due to alert {alert.id}"
            )

        # Log alert addition
        self._log_activity(
            case=case,
            action="alert_added",
            description=f"Alert {alert.id} added to case",
            metadata={'alert_id': alert.id, 'alert_severity': alert.severity.value}
        )

        case.updated_at = datetime.utcnow()
        self.db.commit()

    def _generate_case_title(self, alert: Alert) -> str:
        """Generate a descriptive title for the case"""
        category = alert.category.title() if alert.category else "Security"
        source = alert.hostname or alert.src_ip or "Unknown Host"
        return f"{category} Alert on {source}"

    def _generate_case_description(self, alert: Alert) -> str:
        """Generate a detailed description for the case"""
        parts = [
            f"Alert Rule: {alert.rule_description}",
            f"Severity: {alert.severity.value.upper()}",
        ]

        if alert.src_ip:
            parts.append(f"Source IP: {alert.src_ip}")
        if alert.hostname:
            parts.append(f"Hostname: {alert.hostname}")
        if alert.username:
            parts.append(f"User: {alert.username}")

        return "\n".join(parts)

    def _generate_incident_title(self, alert: Alert) -> str:
        """Generate title for incident"""
        category = alert.category.title() if alert.category else "Security"
        return f"{category} Incident - {alert.severity.value.upper()}"

    def _log_activity(
        self,
        case: Case,
        action: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None
    ):
        """Log an activity for a case"""
        # Use system user (id=1) if no user specified
        if user_id is None:
            user_id = 1  # System user

        activity = Activity(
            case_id=case.id,
            user_id=user_id,
            action=action,
            description=description,
            metadata=metadata or {}
        )

        self.db.add(activity)

    def _compare_severity(self, severity1: SeverityLevel, severity2: SeverityLevel) -> int:
        """
        Compare two severity levels

        Returns:
            1 if severity1 > severity2
            0 if equal
            -1 if severity1 < severity2
        """
        severity_order = {
            SeverityLevel.INFO: 0,
            SeverityLevel.LOW: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.HIGH: 3,
            SeverityLevel.CRITICAL: 4
        }

        level1 = severity_order.get(severity1, 0)
        level2 = severity_order.get(severity2, 0)

        if level1 > level2:
            return 1
        elif level1 < level2:
            return -1
        else:
            return 0

    def auto_escalate_case(self, case: Case) -> bool:
        """
        Automatically escalate a case based on criteria

        Escalation criteria:
        - More than 10 alerts in the case
        - Priority is CRITICAL
        - Case open for more than 24 hours without resolution

        Returns:
            True if escalated, False otherwise
        """
        should_escalate = False
        escalation_reason = []

        # Check alert count
        alert_count = len(case.alerts)
        if alert_count > 10:
            should_escalate = True
            escalation_reason.append(f"High alert count ({alert_count})")

        # Check priority
        if case.priority == SeverityLevel.CRITICAL:
            should_escalate = True
            escalation_reason.append("Critical priority")

        # Check age
        age = datetime.utcnow() - case.created_at
        if age > timedelta(hours=24) and case.status == CaseStatus.OPEN:
            should_escalate = True
            escalation_reason.append(f"Open for {age.days} days")

        if should_escalate and case.status != CaseStatus.IN_PROGRESS:
            case.status = CaseStatus.IN_PROGRESS

            self._log_activity(
                case=case,
                action="case_escalated",
                description=f"Case escalated: {', '.join(escalation_reason)}",
                metadata={'escalation_reasons': escalation_reason}
            )

            # Also escalate the parent incident
            if case.incident.status == IncidentStatus.OPEN:
                case.incident.status = IncidentStatus.IN_PROGRESS

            self.db.commit()
            return True

        return False

    def get_case_statistics(self, case: Case) -> Dict[str, Any]:
        """
        Get statistics and metrics for a case

        Returns:
            Dictionary with case statistics
        """
        return {
            'id': case.id,
            'title': case.title,
            'status': case.status.value,
            'priority': case.priority.value,
            'alert_count': len(case.alerts),
            'alerts_by_severity': self._count_alerts_by_severity(case),
            'unique_source_ips': self._count_unique_values(case.alerts, 'src_ip'),
            'unique_hostnames': self._count_unique_values(case.alerts, 'hostname'),
            'age_hours': (datetime.utcnow() - case.created_at).total_seconds() / 3600,
            'last_alert_time': max([a.timestamp for a in case.alerts]) if case.alerts else None,
            'assigned_analysts': len(case.assigned_users)
        }

    def _count_alerts_by_severity(self, case: Case) -> Dict[str, int]:
        """Count alerts in case by severity level"""
        counts = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'info': 0
        }

        for alert in case.alerts:
            counts[alert.severity.value] += 1

        return counts

    def _count_unique_values(self, alerts: List[Alert], field: str) -> int:
        """Count unique values for a field across alerts"""
        unique_values = set()
        for alert in alerts:
            value = getattr(alert, field, None)
            if value:
                unique_values.add(value)
        return len(unique_values)
