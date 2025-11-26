"""
IOC Correlation Service
Matches alerts against threat intelligence indicators of compromise (IOCs)
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID

from backend.app.models.models_multitenant import (
    ThreatIntelIOC,
    IOCType,
    SeverityLevel
)


class IOCCorrelator:
    """
    Service for correlating alerts with threat intelligence IOCs
    """

    def __init__(self, db: Session):
        self.db = db

    def correlate_alert(
        self,
        alert_data: Dict[str, Any],
        tenant_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Correlate an alert against known IOCs

        Args:
            alert_data: Alert data with fields like src_ip, dst_ip, hostname, file_hash, etc.
            tenant_id: Tenant ID for scoping IOC search (includes global IOCs)

        Returns:
            Dictionary with correlation results:
            {
                "matched": bool,
                "matches": [{"ioc_id": UUID, "type": str, "value": str, "severity": str, ...}],
                "highest_severity": str,
                "should_escalate": bool
            }
        """
        matches = []

        # Extract potential IOC values from alert
        ioc_candidates = self._extract_ioc_candidates(alert_data)

        # Query IOCs
        for ioc_type, value in ioc_candidates:
            ioc_matches = self._query_iocs(ioc_type, value, tenant_id)
            if ioc_matches:
                for ioc in ioc_matches:
                    matches.append({
                        "ioc_id": str(ioc.id),
                        "ioc_type": ioc.ioc_type.value,
                        "value": ioc.value,
                        "severity": ioc.severity.value,
                        "confidence": ioc.confidence,
                        "threat_type": ioc.threat_type,
                        "threat_actor": ioc.threat_actor,
                        "description": ioc.description,
                        "tags": ioc.tags or [],
                        "mitre_attack_ids": ioc.mitre_attack_ids or [],
                        "matched_at": datetime.utcnow().isoformat()
                    })

                    # Update IOC match statistics
                    ioc.match_count += 1
                    ioc.last_match_at = datetime.utcnow()

        # Commit match statistics updates
        if matches:
            self.db.commit()

        # Determine highest severity and escalation
        highest_severity = self._get_highest_severity(matches)
        should_escalate = self._should_escalate(matches, highest_severity)

        return {
            "matched": len(matches) > 0,
            "matches": matches,
            "match_count": len(matches),
            "highest_severity": highest_severity,
            "should_escalate": should_escalate
        }

    def _extract_ioc_candidates(self, alert_data: Dict[str, Any]) -> List[tuple]:
        """
        Extract potential IOC values from alert data

        Returns:
            List of (IOCType, value) tuples
        """
        candidates = []

        # IP addresses
        if alert_data.get("src_ip"):
            candidates.append((IOCType.IP, str(alert_data["src_ip"])))
        if alert_data.get("dst_ip"):
            candidates.append((IOCType.IP, str(alert_data["dst_ip"])))

        # Domains and URLs
        if alert_data.get("hostname"):
            hostname = alert_data["hostname"]
            # Check if it's a domain
            if "." in hostname and not hostname.replace(".", "").isdigit():
                candidates.append((IOCType.DOMAIN, hostname))

        if alert_data.get("url"):
            candidates.append((IOCType.URL, alert_data["url"]))

        # File hashes
        if alert_data.get("file_hash"):
            candidates.append((IOCType.FILE_HASH, alert_data["file_hash"].lower()))

        # Extract from raw_data if available
        raw_data = alert_data.get("raw_data", {})
        if isinstance(raw_data, dict):
            # Check for additional domains in raw data
            for key in ["domain", "dns_query", "http_host"]:
                if key in raw_data and raw_data[key]:
                    candidates.append((IOCType.DOMAIN, raw_data[key]))

            # Check for additional hashes
            for key in ["md5", "sha1", "sha256", "sha512"]:
                if key in raw_data and raw_data[key]:
                    candidates.append((IOCType.FILE_HASH, raw_data[key].lower()))

            # Check for email addresses
            if raw_data.get("email") or raw_data.get("sender"):
                email = raw_data.get("email") or raw_data.get("sender")
                candidates.append((IOCType.EMAIL, email))

        return candidates

    def _query_iocs(
        self,
        ioc_type: IOCType,
        value: str,
        tenant_id: Optional[UUID] = None
    ) -> List[ThreatIntelIOC]:
        """
        Query IOCs by type and value

        Args:
            ioc_type: Type of IOC
            value: IOC value to search for
            tenant_id: Tenant ID (will also include global IOCs)

        Returns:
            List of matching IOCs
        """
        query = self.db.query(ThreatIntelIOC).filter(
            ThreatIntelIOC.ioc_type == ioc_type,
            ThreatIntelIOC.value == value,
            ThreatIntelIOC.is_active == True
        )

        # Include tenant-specific and global IOCs
        if tenant_id:
            query = query.filter(
                or_(
                    ThreatIntelIOC.tenant_id == tenant_id,
                    ThreatIntelIOC.tenant_id == None  # Global IOCs
                )
            )
        else:
            # Only global IOCs if no tenant specified
            query = query.filter(ThreatIntelIOC.tenant_id == None)

        # Filter out expired IOCs
        query = query.filter(
            or_(
                ThreatIntelIOC.expiration_date == None,
                ThreatIntelIOC.expiration_date > datetime.utcnow()
            )
        )

        return query.all()

    def _get_highest_severity(self, matches: List[Dict[str, Any]]) -> Optional[str]:
        """
        Get the highest severity from matched IOCs

        Returns:
            Severity level string or None
        """
        if not matches:
            return None

        severity_order = {
            SeverityLevel.CRITICAL.value: 5,
            SeverityLevel.HIGH.value: 4,
            SeverityLevel.MEDIUM.value: 3,
            SeverityLevel.LOW.value: 2,
            SeverityLevel.INFO.value: 1
        }

        highest = max(
            matches,
            key=lambda m: severity_order.get(m.get("severity", "info"), 0)
        )

        return highest.get("severity")

    def _should_escalate(
        self,
        matches: List[Dict[str, Any]],
        highest_severity: Optional[str]
    ) -> bool:
        """
        Determine if alert should be escalated based on IOC matches

        Escalation criteria:
        - Any CRITICAL severity IOC match
        - 2+ HIGH severity IOC matches
        - 5+ MEDIUM severity IOC matches
        """
        if not matches or not highest_severity:
            return False

        # Count by severity
        critical_count = sum(1 for m in matches if m.get("severity") == SeverityLevel.CRITICAL.value)
        high_count = sum(1 for m in matches if m.get("severity") == SeverityLevel.HIGH.value)
        medium_count = sum(1 for m in matches if m.get("severity") == SeverityLevel.MEDIUM.value)

        # Escalation logic
        if critical_count > 0:
            return True
        if high_count >= 2:
            return True
        if medium_count >= 5:
            return True

        return False

    def enrich_alert_severity(
        self,
        original_severity: str,
        ioc_correlation: Dict[str, Any]
    ) -> str:
        """
        Enrich alert severity based on IOC correlation

        Args:
            original_severity: Original alert severity
            ioc_correlation: IOC correlation result from correlate_alert()

        Returns:
            Enriched severity level (possibly escalated)
        """
        if not ioc_correlation.get("matched"):
            return original_severity

        ioc_severity = ioc_correlation.get("highest_severity")
        if not ioc_severity:
            return original_severity

        severity_order = {
            SeverityLevel.CRITICAL.value: 5,
            SeverityLevel.HIGH.value: 4,
            SeverityLevel.MEDIUM.value: 3,
            SeverityLevel.LOW.value: 2,
            SeverityLevel.INFO.value: 1
        }

        original_level = severity_order.get(original_severity.lower(), 1)
        ioc_level = severity_order.get(ioc_severity.lower(), 1)

        # Return the higher severity
        if ioc_level > original_level:
            return ioc_severity

        return original_severity

    def get_ioc_context(self, ioc_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get full context for a specific IOC

        Args:
            ioc_id: IOC UUID

        Returns:
            IOC context dictionary or None
        """
        ioc = self.db.query(ThreatIntelIOC).filter(
            ThreatIntelIOC.id == ioc_id
        ).first()

        if not ioc:
            return None

        return {
            "id": str(ioc.id),
            "type": ioc.ioc_type.value,
            "value": ioc.value,
            "severity": ioc.severity.value,
            "confidence": ioc.confidence,
            "threat_type": ioc.threat_type,
            "threat_actor": ioc.threat_actor,
            "description": ioc.description,
            "tags": ioc.tags or [],
            "mitre_attack_ids": ioc.mitre_attack_ids or [],
            "first_seen": ioc.first_seen.isoformat() if ioc.first_seen else None,
            "last_seen": ioc.last_seen.isoformat() if ioc.last_seen else None,
            "match_count": ioc.match_count,
            "feed_id": str(ioc.feed_id)
        }


def correlate_alert_with_iocs(
    db: Session,
    alert_data: Dict[str, Any],
    tenant_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """
    Convenience function to correlate an alert with IOCs

    Args:
        db: Database session
        alert_data: Alert data dictionary
        tenant_id: Optional tenant ID for scoping

    Returns:
        IOC correlation results
    """
    correlator = IOCCorrelator(db)
    return correlator.correlate_alert(alert_data, tenant_id)
