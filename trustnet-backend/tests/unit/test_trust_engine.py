"""
Trust Engine Unit Tests
15 test inputs covering all verdict bands.
"""

import pytest

from app.core.trust_engine import CategoryScorer, TrustEngine


@pytest.fixture
def engine():
    return TrustEngine()


class TestTrustEngine:
    """Test the main trust scoring engine."""

    def test_high_risk_verdict(self, engine):
        """Score < 25 should yield HIGH_RISK verdict."""
        categories = {
            "identity_company": {"score": 18, "evidence": []},
            "domain_infrastructure": {"score": 8, "evidence": []},
            "communication_channel": {"score": 15, "evidence": []},
            "content_red_flags": {"score": 20, "evidence": []},
            "community_intelligence": {"score": 12, "evidence": []},
        }
        data = {k: True for k in [
            "company_found", "whois_data", "dns_records", "sarvam_extraction",
            "community_reports", "phone_verified", "email_auth"
        ]}
        result = engine.calculate(categories, data)
        assert result["trust_score"] < 25
        assert result["verdict"] == "HIGH_RISK"

    def test_suspicious_verdict(self, engine):
        """Score 25-44 should yield SUSPICIOUS verdict."""
        categories = {
            "identity_company": {"score": 35, "evidence": []},
            "domain_infrastructure": {"score": 30, "evidence": []},
            "communication_channel": {"score": 40, "evidence": []},
            "content_red_flags": {"score": 25, "evidence": []},
            "community_intelligence": {"score": 35, "evidence": []},
        }
        data = {k: True for k in [
            "company_found", "whois_data", "dns_records", "sarvam_extraction",
            "phone_verified", "email_auth"
        ]}
        result = engine.calculate(categories, data)
        assert 25 <= result["trust_score"] < 45
        assert result["verdict"] == "SUSPICIOUS"

    def test_verified_verdict(self, engine):
        """Score >= 80 with confidence >= 60% should yield VERIFIED."""
        categories = {
            "identity_company": {"score": 95, "evidence": []},
            "domain_infrastructure": {"score": 90, "evidence": []},
            "communication_channel": {"score": 85, "evidence": []},
            "content_red_flags": {"score": 90, "evidence": []},
            "community_intelligence": {"score": 80, "evidence": []},
        }
        data = {k: True for k in [
            "company_found", "whois_data", "dns_records", "sarvam_extraction",
            "community_reports", "phone_verified", "email_auth"
        ]}
        result = engine.calculate(categories, data)
        assert result["trust_score"] >= 80
        assert result["confidence_score"] >= 60
        assert result["verdict"] == "VERIFIED"

    def test_insufficient_data_low_confidence(self, engine):
        """Low confidence should yield INSUFFICIENT_DATA regardless of score."""
        categories = {
            "identity_company": {"score": 50, "evidence": []},
            "domain_infrastructure": {"score": 50, "evidence": []},
            "communication_channel": {"score": 50, "evidence": []},
            "content_red_flags": {"score": 50, "evidence": []},
            "community_intelligence": {"score": 50, "evidence": []},
        }
        data = {"sarvam_extraction": True}  # Very limited data
        result = engine.calculate(categories, data)
        assert result["confidence_score"] < 25
        assert result["verdict"] == "INSUFFICIENT_DATA"

    def test_single_entity_score(self, engine):
        """Single entity extraction should still produce valid score."""
        categories = {
            "identity_company": {"score": 20, "evidence": []},
            "domain_infrastructure": {"score": 0, "evidence": []},
            "communication_channel": {"score": 0, "evidence": []},
            "content_red_flags": {"score": 30, "evidence": []},
            "community_intelligence": {"score": 0, "evidence": []},
        }
        data = {"sarvam_extraction": True}
        result = engine.calculate(categories, data)
        assert isinstance(result["trust_score"], int)
        assert 0 <= result["trust_score"] <= 100

    def test_score_bounds_0_and_100(self, engine):
        """Trust score should always be within 0-100 range."""
        for identity in [0, 50, 100]:
            categories = {
                "identity_company": {"score": identity, "evidence": []},
                "domain_infrastructure": {"score": identity, "evidence": []},
                "communication_channel": {"score": identity, "evidence": []},
                "content_red_flags": {"score": identity, "evidence": []},
                "community_intelligence": {"score": identity, "evidence": []},
            }
            data = {k: True for k in [
                "company_found", "whois_data", "dns_records",
                "sarvam_extraction", "phone_verified", "email_auth"
            ]}
            result = engine.calculate(categories, data)
            assert 0 <= result["trust_score"] <= 100


class TestCategoryScorer:
    """Test individual category scoring functions."""

    def test_identity_company_found_active_old(self):
        result = CategoryScorer.score_identity_company({
            "found": True, "status": "Active", "age_years": 25,
            "cin": "L12345", "company_name": "TCS Limited"
        })
        assert result["score"] >= 85
        assert any("Active" in e["finding"] for e in result["evidence"])

    def test_identity_company_not_found(self):
        result = CategoryScorer.score_identity_company({"found": False})
        assert result["score"] <= 25
        assert any("not found" in e["finding"].lower() for e in result["evidence"])

    def test_identity_dissolved_company(self):
        result = CategoryScorer.score_identity_company({
            "found": True, "status": "Dissolved", "age_years": 2,
        })
        assert result["score"] < 50
        # Engine outputs e.g. "Company is dissolved" (lowercase status)
        assert any("dissolved" in e["finding"].lower() or "strike off" in e["finding"].lower() for e in result["evidence"])

    def test_domain_new_domain(self):
        result = CategoryScorer.score_domain_infrastructure(
            {"found": True, "age_days": 15}, {}, {}, {}
        )
        assert result["score"] <= 10

    def test_domain_old_domain(self):
        result = CategoryScorer.score_domain_infrastructure(
            {"found": True, "age_days": 2000}, {}, {}, {}
        )
        assert result["score"] >= 85

    def test_domain_blacklisted(self):
        result = CategoryScorer.score_domain_infrastructure(
            {"found": True, "age_days": 500},
            {"checked": True, "flagged": True, "threat_types": ["SOCIAL_ENGINEERING"]},
            {}, {}
        )
        assert result["score"] == 0

    def test_communication_personal_email(self):
        result = CategoryScorer.score_communication_channel(
            {"checked": True, "spf": True, "dmarc": True},
            "scammer@gmail.com"
        )
        assert any("Personal email" in e["finding"] for e in result["evidence"])

    def test_content_fee_detected(self):
        result = CategoryScorer.score_content_red_flags(
            {"fee_amount": 2499, "urgency_indicators": True,
             "personal_email_for_corp_contact": True, "red_flags": [], "salary_mentioned": None},
            "Pay Rs. 2499 registration fee immediately"
        )
        assert result["score"] < 50
        assert any("fee" in e["finding"].lower() for e in result["evidence"])

    def test_content_no_fee(self):
        result = CategoryScorer.score_content_red_flags(
            {"fee_amount": None, "urgency_indicators": False,
             "personal_email_for_corp_contact": False, "red_flags": [], "salary_mentioned": 50000},
            "Your offer letter from TCS"
        )
        assert result["score"] >= 60

    def test_community_ring_connected(self):
        result = CategoryScorer.score_community_intelligence(
            {"flagged_count": 3, "rings": ["Test Ring"]}, []
        )
        assert result["score"] < 50
        # Engine outputs "Connected to known scam ring(s): Test Ring"
        assert any("scam ring" in e["finding"].lower() or "ring" in e["finding"].lower() for e in result["evidence"])

    def test_community_no_connections(self):
        result = CategoryScorer.score_community_intelligence(
            {"flagged_count": 0, "rings": []}, []
        )
        assert result["score"] >= 45