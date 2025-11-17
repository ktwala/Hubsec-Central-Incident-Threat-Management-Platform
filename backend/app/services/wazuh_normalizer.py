"""
Wazuh Alert Normalizer Service
Transforms Wazuh alerts into standardized format for the platform
"""
import yaml
import re
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class WazuhNormalizer:
    """
    Normalizes Wazuh alerts into a standard format
    Uses configurable mapping rules from YAML configuration
    """

    def __init__(self, config_path: str = "config/wazuh_mapping.yml"):
        """Initialize the normalizer with configuration"""
        self.config_path = config_path
        self.mapping_config = self._load_config()
        self.severity_rules = self._load_severity_rules()

    def _load_config(self) -> Dict[str, Any]:
        """Load mapping configuration from YAML file"""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    return yaml.safe_load(f)
            else:
                # Return default configuration
                return self._get_default_config()
        except Exception as e:
            print(f"Warning: Could not load config from {self.config_path}: {e}")
            return self._get_default_config()

    def _load_severity_rules(self) -> Dict[str, Any]:
        """Load severity mapping rules"""
        try:
            config_file = Path("config/severity_rules.yml")
            if config_file.exists():
                with open(config_file, 'r') as f:
                    return yaml.safe_load(f)
            else:
                return self._get_default_severity_rules()
        except Exception:
            return self._get_default_severity_rules()

    def _get_default_config(self) -> Dict[str, Any]:
        """Default mapping configuration"""
        return {
            'field_mappings': {
                'source_ip': ['data.srcip', 'data.src_ip', 'srcip'],
                'dest_ip': ['data.dstip', 'data.dst_ip', 'dstip'],
                'source_port': ['data.srcport', 'data.src_port'],
                'dest_port': ['data.dstport', 'data.dst_port'],
                'protocol': ['data.protocol'],
                'username': ['data.dstuser', 'data.win.eventdata.targetUserName', 'data.user'],
                'filename': ['data.file', 'data.win.eventdata.image'],
                'file_path': ['data.path'],
                'file_hash': ['data.md5', 'data.sha256', 'data.hash']
            },
            'category_mappings': {
                'authentication': ['authentication', 'login', 'logon', 'password'],
                'malware': ['malware', 'virus', 'trojan', 'ransomware'],
                'network': ['network', 'firewall', 'ids', 'ips'],
                'web': ['web', 'http', 'apache', 'nginx'],
                'system': ['system', 'windows', 'linux'],
                'intrusion': ['intrusion', 'exploit', 'attack']
            }
        }

    def _get_default_severity_rules(self) -> Dict[str, Any]:
        """Default severity mapping rules"""
        return {
            'rule_level_mapping': {
                'range': {
                    '0-3': 'info',
                    '4-6': 'low',
                    '7-10': 'medium',
                    '11-14': 'high',
                    '15-20': 'critical'
                }
            },
            'keyword_boost': {
                'critical': ['critical', 'emergency', 'rootkit', 'ransomware'],
                'high': ['attack', 'exploit', 'malware', 'breach']
            }
        }

    def normalize_alert(self, wazuh_alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a Wazuh alert into standard format

        Args:
            wazuh_alert: Raw Wazuh alert dictionary

        Returns:
            Normalized alert dictionary ready for database insertion
        """
        normalized = {
            'source': 'Wazuh',
            'source_id': wazuh_alert.get('id'),
            'timestamp': self._parse_timestamp(wazuh_alert.get('timestamp')),
            'raw_data': wazuh_alert
        }

        # Extract rule information
        rule = wazuh_alert.get('rule', {})
        normalized['rule_id'] = rule.get('id')
        normalized['rule_description'] = rule.get('description')

        # Determine severity
        normalized['severity'] = self._determine_severity(wazuh_alert)

        # Determine event type and category
        normalized['event_type'] = self._determine_event_type(wazuh_alert)
        normalized['category'] = self._determine_category(wazuh_alert)

        # Extract agent information
        agent = wazuh_alert.get('agent', {})
        normalized['agent_id'] = agent.get('id')
        normalized['agent_name'] = agent.get('name')
        normalized['hostname'] = agent.get('name')  # Use agent name as hostname

        # Extract network information
        data = wazuh_alert.get('data', {})
        normalized.update(self._extract_network_info(data))

        # Extract user information
        normalized['username'] = self._extract_field(data, self.mapping_config['field_mappings']['username'])

        # Extract file information
        normalized['filename'] = self._extract_field(data, self.mapping_config['field_mappings']['filename'])
        normalized['file_path'] = self._extract_field(data, self.mapping_config['field_mappings']['file_path'])
        normalized['file_hash'] = self._extract_field(data, self.mapping_config['field_mappings']['file_hash'])

        # Store normalized data separately
        normalized['normalized_data'] = {
            'rule_level': rule.get('level'),
            'rule_groups': rule.get('groups', []),
            'mitre_techniques': rule.get('mitre', {}).get('technique', []),
            'location': wazuh_alert.get('location'),
            'full_log': wazuh_alert.get('full_log')
        }

        # Remove None values
        normalized = {k: v for k, v in normalized.items() if v is not None}

        return normalized

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse Wazuh timestamp string to datetime object"""
        if not timestamp_str:
            return datetime.utcnow()

        try:
            # Wazuh format: 2024-01-15T10:30:45.123+0000
            # Remove timezone info for simplicity (store as UTC)
            timestamp_str = re.sub(r'[+-]\d{4}$', '', timestamp_str)
            return datetime.fromisoformat(timestamp_str)
        except Exception:
            return datetime.utcnow()

    def _determine_severity(self, alert: Dict[str, Any]) -> str:
        """
        Determine severity level based on rule level and keywords

        Priority:
        1. Check for critical keywords
        2. Check rule level
        3. Default to 'medium'
        """
        rule = alert.get('rule', {})
        rule_level = rule.get('level', 0)
        rule_description = rule.get('description', '').lower()
        rule_groups = rule.get('groups', [])

        # Check for critical keywords
        for keyword in self.severity_rules['keyword_boost']['critical']:
            if keyword in rule_description or keyword in str(rule_groups).lower():
                return 'critical'

        # Check for high severity keywords
        for keyword in self.severity_rules['keyword_boost']['high']:
            if keyword in rule_description or keyword in str(rule_groups).lower():
                return 'high'

        # Map based on rule level
        if rule_level >= 15:
            return 'critical'
        elif rule_level >= 11:
            return 'high'
        elif rule_level >= 7:
            return 'medium'
        elif rule_level >= 4:
            return 'low'
        else:
            return 'info'

    def _determine_event_type(self, alert: Dict[str, Any]) -> Optional[str]:
        """Determine the event type from rule groups"""
        rule = alert.get('rule', {})
        groups = rule.get('groups', [])

        if not groups:
            return None

        # Return the first meaningful group
        # Skip generic groups like 'wazuh', 'syslog'
        skip_groups = {'wazuh', 'syslog', 'ossec'}
        for group in groups:
            if group.lower() not in skip_groups:
                return group

        return groups[0] if groups else None

    def _determine_category(self, alert: Dict[str, Any]) -> Optional[str]:
        """Determine category based on rule description and groups"""
        rule = alert.get('rule', {})
        description = rule.get('description', '').lower()
        groups = [g.lower() for g in rule.get('groups', [])]

        # Check each category mapping
        for category, keywords in self.mapping_config['category_mappings'].items():
            for keyword in keywords:
                if keyword in description or keyword in ' '.join(groups):
                    return category

        return None

    def _extract_network_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract network-related information"""
        network_info = {}

        # Source IP
        src_ip = self._extract_field(data, self.mapping_config['field_mappings']['source_ip'])
        if src_ip:
            network_info['src_ip'] = src_ip

        # Destination IP
        dst_ip = self._extract_field(data, self.mapping_config['field_mappings']['dest_ip'])
        if dst_ip:
            network_info['dst_ip'] = dst_ip

        # Source Port
        src_port = self._extract_field(data, self.mapping_config['field_mappings']['source_port'])
        if src_port:
            network_info['src_port'] = int(src_port)

        # Destination Port
        dst_port = self._extract_field(data, self.mapping_config['field_mappings']['dest_port'])
        if dst_port:
            network_info['dst_port'] = int(dst_port)

        # Protocol
        protocol = self._extract_field(data, self.mapping_config['field_mappings']['protocol'])
        if protocol:
            network_info['protocol'] = protocol

        return network_info

    def _extract_field(self, data: Dict[str, Any], field_paths: list) -> Optional[str]:
        """
        Extract field value using multiple possible paths

        Args:
            data: Data dictionary to search
            field_paths: List of dot-notation paths to try

        Returns:
            First matching value found, or None
        """
        for path in field_paths:
            value = self._get_nested_value(data, path)
            if value:
                return str(value)
        return None

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Optional[Any]:
        """
        Get value from nested dictionary using dot notation

        Example: 'data.win.eventdata.user' -> data['win']['eventdata']['user']
        """
        keys = path.split('.')
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current

    def batch_normalize(self, alerts: list) -> list:
        """
        Normalize multiple alerts

        Args:
            alerts: List of raw Wazuh alerts

        Returns:
            List of normalized alerts
        """
        return [self.normalize_alert(alert) for alert in alerts]


# Singleton instance
_normalizer_instance = None


def get_normalizer() -> WazuhNormalizer:
    """Get or create the normalizer singleton instance"""
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = WazuhNormalizer()
    return _normalizer_instance
