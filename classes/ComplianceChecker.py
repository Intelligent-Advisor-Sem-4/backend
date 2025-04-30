# compliance/checker.py
from typing import Dict, List, Optional
from datetime import datetime
import pytz
import requests
from concurrent.futures import ThreadPoolExecutor
import logging

import db.dbConnect


class ComplianceChecker:
    def __init__(self, db_session, config):
        self.db = db.dbConnect.get_db()
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.active_rules = self.load_compliance_rules()

        # External service clients
        self.sanctions_client = SanctionsAPIClient(config['sanctions_api'])
        self.pep_checker = PEPDatabaseClient(config['pep_db'])
        self.geo_ip = GeoIPService(config['geoip_service'])
        self.risk_engine = RiskModelAPI(config['risk_model_api'])

    def load_compliance_rules(self) -> List[Dict]:
        """Load compliance rules from database with caching"""
        try:
            rules = self.db.query(ComplianceRule).filter_by(active=True).all()
            return [{
                "rule_id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "condition": self._compile_condition(rule.condition_logic),
                "action": rule.action,
                "risk_level": rule.risk_level,
                "applicable_regions": rule.applicable_regions or ["GLOBAL"],
                "external_checks": rule.external_checks  # JSON field with API configs
            } for rule in rules]
        except Exception as e:
            self.logger.error(f"Error loading rules: {str(e)}")
            return self._get_default_rules()

    async def check_transaction(self, transaction_data: Dict) -> Dict:
        """Enhanced compliance check with external APIs"""
        violations = []
        enriched_data = await self._enrich_transaction(transaction_data)

        # Check against each rule with parallel external checks
        with ThreadPoolExecutor() as executor:
            futures = []
            for rule in self.active_rules:
                if not self._is_rule_applicable(rule, enriched_data):
                    continue

                futures.append(executor.submit(
                    self._check_rule_with_externals,
                    rule,
                    enriched_data
                ))

            for future in futures:
                try:
                    rule_violations = future.result()
                    if rule_violations:
                        violations.extend(rule_violations)
                except Exception as e:
                    self.logger.error(f"Rule check failed: {str(e)}")

        return {
            "transaction_id": enriched_data.get('id'),
            "is_compliant": len(violations) == 0,
            "violations": violations,
            "enriched_data": {k: v for k, v in enriched_data.items()
                              if k not in ['user_info', 'account_details']},
            "checked_at": datetime.now(pytz.utc)
        }

    async def _enrich_transaction(self, transaction: Dict) -> Dict:
        """Add external data to transaction for better checks"""
        enriched = transaction.copy()

        # Parallel enrichment
        with ThreadPoolExecutor() as executor:
            # User verification
            user_future = executor.submit(
                self.db.query(user).get,
                transaction.get('user_id')
            )

            # Sanctions check
            sanctions_future = executor.submit(
                self.sanctions_client.check,
                transaction.get('parties', [])
            )

            # GeoIP verification
            geo_future = executor.submit(
                self.geo_ip.lookup,
                transaction.get('ip_address')
            )

            # Get results
            enriched['user_info'] = user_future.result()
            enriched['sanctions_matches'] = sanctions_future.result()
            enriched['geo_data'] = geo_future.result()

        # Additional enrichment
        enriched['pep_status'] = self.pep_checker.check(
            enriched['user_info'].get('name')
        )
        enriched['risk_score'] = self.risk_engine.get_score(enriched)

        return enriched

    def _check_rule_with_externals(self, rule: Dict, transaction: Dict) -> List[Dict]:
        """Check rule with external API verifications"""
        violations = []

        try:
            # Check core condition
            if rule['condition'](transaction):
                violation = {
                    "rule_id": rule['rule_id'],
                    "rule_name": rule['name'],
                    "action": rule['action'],
                    "risk_level": rule['risk_level'],
                    "timestamp": datetime.now(pytz.utc),
                    "external_verifications": []
                }

                # Perform external checks if configured
                for check in rule.get('external_checks', []):
                    try:
                        result = self._perform_external_check(check, transaction)
                        violation['external_verifications'].append({
                            "service": check['service'],
                            "result": result,
                            "matched": result.get('match', False)
                        })
                    except Exception as e:
                        self.logger.error(f"External check failed: {str(e)}")

                violations.append(violation)
        except Exception as e:
            self.logger.error(f"Rule evaluation failed: {str(e)}")

        return violations

    def _perform_external_check(self, check_config: Dict, transaction: Dict) -> Dict:
        """Call external compliance APIs"""
        check_type = check_config['type']

        if check_type == "sanctions":
            return self.sanctions_client.enhanced_check(
                transaction['parties'],
                check_config.get('lists', ['OFAC', 'UN'])
            )
        elif check_type == "geo_block":
            return self.geo_ip.check_jurisdiction(
                transaction['ip_address'],
                blocked_countries=check_config['countries']
            )
        elif check_type == "pep":
            return self.pep_checker.enhanced_check(
                transaction['user_info']['name'],
                positions=check_config.get('positions', [])
            )
        else:
            raise ValueError(f"Unknown check type: {check_type}")

    # Helper methods
    def _compile_condition(self, condition_logic: str):
        """Compile rule condition from stored logic"""
        # In production, use a safe evaluator like restrictedpython
        return eval(f"lambda t: {condition_logic}")

    def _is_rule_applicable(self, rule: Dict, transaction: Dict) -> bool:
        """Check if rule applies to this transaction"""
        region = transaction.get('region')
        if region not in rule['applicable_regions']:
            if "GLOBAL" not in rule['applicable_regions']:
                return False
        return True

    def _get_default_rules(self):
        """Fallback rules if DB fails"""
        return [
            {
                "rule_id": "AML-001",
                "name": "Large Transaction Monitoring",
                "description": "Flag transactions above $10,000",
                "condition": lambda t: t['amount'] > 10000,
                "action": "flag_for_review",
                "risk_level": "high",
                "applicable_regions": ["GLOBAL"],
                "external_checks": [
                    {
                        "type": "sanctions",
                        "service": "sanctions_api",
                        "lists": ["OFAC", "EU"]
                    }
                ]
            }
        ]


# External Service Clients (simplified implementations)
class SanctionsAPIClient:
    def __init__(self, config):
        self.base_url = config['url']
        self.api_key = config['key']

    def check(self, parties):
        response = requests.post(
            f"{self.base_url}/check",
            json={"entities": parties},
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return response.json().get('matches', [])

    def enhanced_check(self, parties, lists):
        # More thorough check with specific lists
        pass


class PEPDatabaseClient:
    def __init__(self, config):
        self.connection_string = config['conn_str']

    def check(self, name):
        # Check if name appears in PEP database
        pass


class GeoIPService:
    def __init__(self, config):
        self.endpoint = config['endpoint']

    def lookup(self, ip):
        # Get geo location data
        pass

    def check_jurisdiction(self, ip, blocked_countries):
        # Verify if IP is in blocked country
        pass


class RiskModelAPI:
    def __init__(self, config):
        self.model_endpoint = config['url']

    def get_score(self, transaction):
        # Get risk score from ML model
        pass