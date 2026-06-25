"""
API Integration Tests
Test all REST endpoints with mocked external dependencies.
"""

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_check(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"


from unittest.mock import patch, AsyncMock

class TestInvestigateEndpoint:
    @patch('app.api.investigate.sarvam_service.extract_entities', new_callable=AsyncMock)
    @patch('app.api.investigate.sarvam_service.generate_hindi_from_investigation', new_callable=AsyncMock)
    @patch('app.api.investigate.neo4j_service.detect_ring_connections', new_callable=AsyncMock)
    @patch('app.api.investigate.blockchain_service.flag_entity', new_callable=AsyncMock)
    def test_investigate_valid_input(self, mock_blockchain, mock_neo4j, mock_hindi, mock_extract):
        """Full investigation with sample scam text."""
        mock_extract.return_value = {"fee_amount": 2499, "website_url": "infosys-careers.in"}
        mock_hindi.return_value = "Scam explanation"
        mock_neo4j.return_value = {"flagged_count": 5, "rings": ["Infosys Scam Ring"]}
        mock_blockchain.return_value = "0x12345"

        resp = client.post("/api/v1/investigate", json={
            "raw_input": "Your profile selected at Infosys. Salary 45k. Fee Rs.2499. Register at infosys-careers.in immediately!",
            "input_type": "paste"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "trust_score" in data
        assert "verdict" in data
        assert "verdict_label" in data
        assert 0 <= data["trust_score"] <= 100
        assert data["trust_score"] < 35
        assert data["entities"]["fee_amount"] == 2499

    def test_investigate_short_input(self):
        """Input too short should fail validation."""
        resp = client.post("/api/v1/investigate", json={
            "raw_input": "Hi",
            "input_type": "paste"
        })
        assert resp.status_code == 400

    @patch('app.api.investigate.sarvam_service.extract_entities', new_callable=AsyncMock)
    @patch('app.api.investigate.sarvam_service.generate_hindi_from_investigation', new_callable=AsyncMock)
    @patch('app.api.investigate.neo4j_service.get_entity_graph', new_callable=AsyncMock)
    @patch('app.api.investigate.neo4j_service.detect_ring_connections', new_callable=AsyncMock)
    @patch('app.api.investigate.whois_service.lookup_domain', new_callable=AsyncMock)
    @patch('app.api.investigate._check_mca', new_callable=AsyncMock)
    @patch('app.api.investigate.dns_service.check_email_auth', new_callable=AsyncMock)
    @patch('app.api.investigate.safebrowsing_service.check_url', new_callable=AsyncMock)
    def test_investigate_legitimate_offer(self, mock_safebrowsing, mock_dns, mock_mca, mock_whois, mock_neo4j_detect, mock_neo4j_graph, mock_hindi, mock_extract):
        """Legitimate TCS offer should score higher."""
        mock_extract.return_value = {"company_name": "Tata Consultancy Services Limited", "email": "hr@tcs.com", "website_url": "www.tcs.com"}
        mock_hindi.return_value = "Legitimate explanation"
        mock_neo4j_detect.return_value = {"flagged_count": 0, "rings": []}
        mock_neo4j_graph.return_value = {"nodes": [], "relationships": []}
        mock_mca.return_value = {"found": True, "company_name": "Tata Consultancy Services Limited", "status": "Active", "age_years": 20, "cin": "L22210MH1995PLC084781"}
        mock_dns.return_value = {"checked": True, "spf": True, "dkim": True, "dmarc": True, "overall_auth_pass": True}
        mock_safebrowsing.return_value = {"checked": True, "flagged": False}
        # TCS domain is ~20 years old — simulate a well-established domain
        mock_whois.return_value = {
            "found": True, "domain": "www.tcs.com",
            "age_days": 7300, "age_years": 20,
            "registrar": "MarkMonitor Inc.",
            "nameservers": ["ns1.tcs.com"],
            "has_privacy_protection": False, "status": "active",
        }

        resp = client.post("/api/v1/investigate", json={
            "raw_input": "We are pleased to offer you the position of Systems Engineer at Tata Consultancy Services Limited. CTC Rs. 3,36,877 per annum. Report date: 15th July 2024. Contact: hr@tcs.com | www.tcs.com",
            "input_type": "paste"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["trust_score"] >= 58
        assert data["entities"]["company_name"] is not None

    def test_investigate_empty_input(self):
        """Empty input should fail."""
        resp = client.post("/api/v1/investigate", json={
            "raw_input": "",
            "input_type": "paste"
        })
        assert resp.status_code == 400

    def test_investigate_invalid_input_type(self):
        """Invalid input_type should fail validation."""
        resp = client.post("/api/v1/investigate", json={
            "raw_input": "Valid text here that is long enough to pass validation",
            "input_type": "invalid_type"
        })
        assert resp.status_code == 422


class TestStatsEndpoint:
    def test_get_stats(self):
        resp = client.get("/api/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_investigations" in data
        assert "total_entities_flagged" in data
        assert "high_risk_percentage" in data
        assert isinstance(data["total_investigations"], int)


class TestGraphEndpoint:
    def test_get_graph_existing_entity(self):
        """Graph query for known entity."""
        resp = client.get("/api/v1/graph/infosys-careers.in")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data

    def test_get_graph_nonexistent_entity(self):
        """Graph query returns empty for unknown."""
        resp = client.get("/api/v1/graph/nonexistent-domain-12345.xyz")
        assert resp.status_code == 200


class TestCommunityEndpoint:
    def test_submit_report(self):
        """Submit a community report."""
        resp = client.post("/api/v1/community/report", json={
            "entity_id": "123e4567-e89b-12d3-a456-426614174000",
            "report_type": "SCAM",
            "loss_amount_inr": 2500,
            "description": "Asked for registration fee"
        })
        assert resp.status_code in (201, 404)  # 404 if entity doesn't exist

    def test_list_reports(self):
        resp = client.get("/api/v1/community/reports")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestAuthEndpoints:
    def test_register_and_login(self):
        """Full auth flow: register then login."""
        import uuid
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        password = "SecurePass123!"

        # Register
        resp = client.post("/api/v1/auth/register", json={
            "email": email,
            "password": password,
        })
        assert resp.status_code == 201
        register_data = resp.json()
        assert "access_token" in register_data

        # Login
        resp = client.post("/api/v1/auth/token", json={
            "email": email,
            "password": password,
        })
        assert resp.status_code == 200
        login_data = resp.json()
        assert "access_token" in login_data

    def test_login_invalid_credentials(self):
        resp = client.post("/api/v1/auth/token", json={
            "email": "nonexistent@test.com",
            "password": "wrongpassword"
        })
        assert resp.status_code == 401

    def test_register_duplicate_email(self):
        import uuid
        email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
        password = "SecurePass123!"

        client.post("/api/v1/auth/register", json={"email": email, "password": password})
        resp = client.post("/api/v1/auth/register", json={"email": email, "password": password})
        assert resp.status_code == 400


class TestPerformance:
    """Performance benchmarks."""

    @patch('app.api.investigate.sarvam_service.extract_entities', new_callable=AsyncMock)
    @patch('app.api.investigate.sarvam_service.generate_hindi_from_investigation', new_callable=AsyncMock)
    @patch('app.api.investigate.neo4j_service.detect_ring_connections', new_callable=AsyncMock)
    @patch('app.api.investigate.blockchain_service.flag_entity', new_callable=AsyncMock)
    @patch('app.api.investigate.whois_service.lookup_domain', new_callable=AsyncMock)
    def test_investigation_response_time(self, mock_whois, mock_blockchain, mock_neo4j, mock_hindi, mock_extract):
        """Investigation should complete in under 15 seconds (CI-safe threshold)."""
        mock_extract.return_value = {"fee_amount": 3500, "website_url": "wipro-jobs.co.in"}
        mock_hindi.return_value = "Performance scam report"
        mock_neo4j.return_value = {"flagged_count": 0, "rings": []}
        mock_blockchain.return_value = "0x12345"
        mock_whois.return_value = {"found": True, "domain": "wipro-jobs.co.in", "age_days": 10}

        import time
        start = time.time()
        resp = client.post("/api/v1/investigate", json={
            "raw_input": "Dear Candidate, your profile selected at Wipro. Salary 60k/month. Pay registration fee Rs.3500 at wipro-jobs.co.in immediately!",
            "input_type": "paste"
        })
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < 15, f"Investigation took {elapsed:.2f}s, expected < 15s"