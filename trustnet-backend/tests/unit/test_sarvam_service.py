"""
Unit Tests for SarvamService (app/services/sarvam_service.py)

Tests cover:
  - Regex fallback when API key is missing/dummy
  - Multi-language entity extraction (mocked API)
  - Fallback on timeout
  - Fallback on HTTP error
  - JSON parsing from markdown code fences
  - Language detection heuristic
  - BCP-47 language code resolution
  - Health ping: ok / degraded paths
  - Hindi report: API call / template fallback
  - Result normalisation (missing keys filled with defaults)
  - Field merging (regex fills gaps in AI result)
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Helpers ─────────────────────────────────────────────────────────────────

SCAM_TEXT_EN = (
    "Dear Candidate, your profile has been selected at Wipro Technologies. "
    "Salary: Rs.45,000/month. Register at wipro-jobs.co.in immediately. "
    "Contact hr.wipro2024@gmail.com or +919876543210. "
    "Pay registration fee of Rs.2500 today."
)

SCAM_TEXT_HI = (
    "Pyare Umeedwar, aapka profile Infosys mein select hua hai. "
    "Salary 40k monthly. Registration fee Rs.1500 abhi bhejein. "
    "hr@infosys-fake.in par contact karein."
)

LEGIT_RESPONSE = {
    "company_name": "Wipro Technologies",
    "email": "hr.wipro2024@gmail.com",
    "phone_number": "+919876543210",
    "website_url": "wipro-jobs.co.in",
    "recruiter_name": None,
    "job_title": "Software Engineer",
    "location": "Bangalore",
    "salary_mentioned": 45000,
    "fee_amount": 2500,
    "urgency_indicators": True,
    "personal_email_for_corp_contact": True,
    "language_detected": "english",
    "red_flags": ["Fee requested: ₹2500", "Urgency language detected"],
}


def make_mock_resp(content: dict, status: int = 200):
    """Build a fake httpx Response-like object."""
    mock = MagicMock()
    mock.status_code = status
    mock.json.return_value = {
        "choices": [{"message": {"content": json.dumps(content)}}]
    }
    mock.raise_for_status = MagicMock()
    return mock


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def sarvam_with_key():
    """
    SarvamService with the api_key forced to a real-looking value.
    Uses patch.object to avoid .env leakage.
    """
    from app.services.sarvam_service import SarvamService
    svc = SarvamService()
    svc.api_key = "sk_test_fake_key_for_unit_tests"
    svc.headers["Authorization"] = f"Bearer {svc.api_key}"
    return svc


@pytest.fixture
def sarvam_no_key():
    """SarvamService with api_key blanked — forces regex fallback."""
    from app.services.sarvam_service import SarvamService
    svc = SarvamService()
    svc.api_key = "dummy"
    return svc


# ── Tests: Regex fallback ────────────────────────────────────────────────────

class TestRegexFallback:
    def test_no_api_key_uses_regex(self, sarvam_no_key):
        """When API key is dummy, extract_entities returns a regex result."""
        # Use http:// URL so regex matches it
        text = (
            "Dear Candidate, your profile selected at Wipro. "
            "Salary Rs.45,000/month. Register at http://wipro-jobs.co.in immediately. "
            "Contact hr.wipro2024@gmail.com or +919876543210. "
            "Pay registration fee of Rs.2500 today."
        )
        result = asyncio.run(sarvam_no_key.extract_entities(text))
        assert result["email"] == "hr.wipro2024@gmail.com"
        assert result["phone_number"] == "+919876543210"
        assert result["website_url"] is not None
        assert result["fee_amount"] == 2500
        assert result["urgency_indicators"] is True
        assert result["personal_email_for_corp_contact"] is True

    def test_regex_extracts_job_title(self, sarvam_no_key):
        # Regex stops at commas/dots — use comma-free text
        text = "We are hiring for the position of Senior Data Analyst at Acme Corp"
        result = asyncio.run(sarvam_no_key.extract_entities(text))
        assert result["job_title"] is not None
        assert "Senior Data Analyst" in result["job_title"]

    def test_regex_extracts_location(self, sarvam_no_key):
        text = "Work location: Bengaluru office and offers 50k monthly salary"
        result = asyncio.run(sarvam_no_key.extract_entities(text))
        assert result["location"] is not None
        assert "Bengaluru" in result["location"]

    def test_regex_salary_normalise_lpa(self, sarvam_no_key):
        """3 LPA should normalise to 25000/month."""
        text = "Salary offered: Rs. 3 LPA. Apply now at example.com"
        result = asyncio.run(sarvam_no_key.extract_entities(text))
        assert result["salary_mentioned"] == 25000

    def test_regex_no_false_positives(self, sarvam_no_key):
        text = "Welcome to our company. Please visit our website for more information."
        result = asyncio.run(sarvam_no_key.extract_entities(text))
        assert result["email"] is None
        assert result["phone_number"] is None
        assert result["fee_amount"] is None


# ── Tests: API path (mocked HTTP) ───────────────────────────────────────────

class TestAPIExtraction:
    @pytest.mark.asyncio
    async def test_successful_api_call(self, sarvam_with_key):
        """API returns valid JSON → use it."""
        with patch("app.services.sarvam_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__  = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=make_mock_resp(LEGIT_RESPONSE))

            result = await sarvam_with_key.extract_entities(SCAM_TEXT_EN)

        assert result["company_name"] == "Wipro Technologies"
        assert result["job_title"] == "Software Engineer"
        assert result["location"] == "Bangalore"
        assert result["fee_amount"] == 2500

    @pytest.mark.asyncio
    async def test_language_hint_passed_to_api(self, sarvam_with_key):
        """Hindi hint should resolve to hi-IN and be in the payload."""
        captured_payload = {}

        async def fake_post(url, json=None, headers=None, **kwargs):
            captured_payload.update(json or {})
            return make_mock_resp(LEGIT_RESPONSE)

        with patch("app.services.sarvam_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__  = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=fake_post)

            await sarvam_with_key.extract_entities(SCAM_TEXT_HI, language_hint="hindi")

        assert captured_payload.get("language_code") == "hi-IN"

    @pytest.mark.asyncio
    async def test_timeout_falls_back_to_regex(self, sarvam_with_key):
        """Timeout during API call → regex fallback, no exception raised."""
        with patch(
            "app.services.sarvam_service.SarvamService._call_sarvam_extraction",
            new_callable=AsyncMock,
            side_effect=asyncio.TimeoutError,
        ):
            result = await sarvam_with_key.extract_entities(SCAM_TEXT_EN)

        # Should still return a valid dict from regex
        assert isinstance(result, dict)
        assert "email" in result
        assert "red_flags" in result

    @pytest.mark.asyncio
    async def test_http_error_falls_back_to_regex(self, sarvam_with_key):
        """HTTP error during API call → regex fallback, no exception raised."""
        with patch(
            "app.services.sarvam_service.SarvamService._call_sarvam_extraction",
            new_callable=AsyncMock,
            side_effect=Exception("Connection refused"),
        ):
            result = await sarvam_with_key.extract_entities(SCAM_TEXT_EN)

        assert isinstance(result, dict)
        assert "language_detected" in result

    @pytest.mark.asyncio
    async def test_api_result_merged_with_regex(self, sarvam_with_key):
        """If AI misses email but regex finds it, it should be filled in."""
        ai_response = {**LEGIT_RESPONSE, "email": None}  # AI missed email

        with patch(
            "app.services.sarvam_service.SarvamService._call_sarvam_extraction",
            new_callable=AsyncMock,
            return_value=ai_response,
        ):
            result = await sarvam_with_key.extract_entities(SCAM_TEXT_EN)

        # Regex fill should have restored the email
        assert result["email"] == "hr.wipro2024@gmail.com"


# ── Tests: JSON parsing ──────────────────────────────────────────────────────

class TestJSONParsing:
    def test_plain_json(self, sarvam_no_key):
        content = json.dumps({"company_name": "Test Corp"})
        result  = sarvam_no_key._parse_json_response(content)
        assert result["company_name"] == "Test Corp"

    def test_markdown_fenced_json(self, sarvam_no_key):
        content = "```json\n{\"company_name\": \"Test Corp\"}\n```"
        result  = sarvam_no_key._parse_json_response(content)
        assert result["company_name"] == "Test Corp"

    def test_json_embedded_in_prose(self, sarvam_no_key):
        content = 'Sure! Here is the result: {"company_name": "Acme"} Hope that helps.'
        result  = sarvam_no_key._parse_json_response(content)
        assert result["company_name"] == "Acme"

    def test_empty_string_returns_empty_dict(self, sarvam_no_key):
        result = sarvam_no_key._parse_json_response("")
        assert result == {}


# ── Tests: Language detection ────────────────────────────────────────────────

class TestLanguageDetection:
    def test_detects_english(self, sarvam_no_key):
        result = sarvam_no_key._detect_language("We are pleased to offer you this position.")
        assert result == "english"

    def test_detects_hinglish(self, sarvam_no_key):
        result = sarvam_no_key._detect_language("Aapka profile select hua hai.")
        assert result in ("hinglish", "hindi")

    def test_detects_hindi(self, sarvam_no_key):
        result = sarvam_no_key._detect_language(
            "Aapka profile select hua hai aur aapko mein aur ke ke liye rupaye bhej karein"
        )
        assert result == "hindi"

    def test_detects_tamil(self, sarvam_no_key):
        result = sarvam_no_key._detect_language("Ungal profile select aayam seythi vaalthukkal")
        assert result == "tamil"

    def test_detects_telugu(self, sarvam_no_key):
        result = sarvam_no_key._detect_language("Meeku meela jeetham nela paniki ivvalenu")
        assert result == "telugu"


# ── Tests: Language code resolution ─────────────────────────────────────────

class TestLanguageCodeResolution:
    def test_hindi_resolves(self, sarvam_no_key):
        assert sarvam_no_key._resolve_language_code("hindi") == "hi-IN"

    def test_tamil_resolves(self, sarvam_no_key):
        assert sarvam_no_key._resolve_language_code("tamil") == "ta-IN"

    def test_bcp47_passthrough(self, sarvam_no_key):
        assert sarvam_no_key._resolve_language_code("kn-IN") == "kn-IN"

    def test_none_returns_none(self, sarvam_no_key):
        assert sarvam_no_key._resolve_language_code(None) is None

    def test_unknown_returns_none(self, sarvam_no_key):
        assert sarvam_no_key._resolve_language_code("klingon") is None


# ── Tests: Health ping ───────────────────────────────────────────────────────

class TestHealthPing:
    @pytest.mark.asyncio
    async def test_ping_ok(self, sarvam_with_key):
        """API responds 200 → status ok."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("app.services.sarvam_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__  = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)

            result = await sarvam_with_key.ping()

        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_ping_degraded_no_key(self, sarvam_no_key):
        """No API key → degraded immediately, no HTTP call."""
        result = await sarvam_no_key.ping()
        assert result["status"] == "degraded"
        assert result["fallback"] is True

    @pytest.mark.asyncio
    async def test_ping_degraded_on_timeout(self, sarvam_with_key):
        """Timeout → degraded."""
        with patch("app.services.sarvam_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__  = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=asyncio.TimeoutError)

            result = await sarvam_with_key.ping()

        assert result["status"] == "degraded"
        assert "timeout" in result["reason"]


# ── Tests: Hindi report ──────────────────────────────────────────────────────

class TestHindiReport:
    @pytest.mark.asyncio
    async def test_template_fallback_no_key(self, sarvam_no_key):
        """No API key → template is returned, contains verdict text."""
        result = await sarvam_no_key.generate_hindi_report(
            verdict="HIGH_RISK", trust_score=12, evidence=[]
        )
        assert "HIGH RISK" in result
        assert "12" in result
        assert len(result) > 30

    @pytest.mark.asyncio
    async def test_template_for_all_verdicts(self, sarvam_no_key):
        """All verdict types should return non-empty Hindi text."""
        for verdict in ("HIGH_RISK", "SUSPICIOUS", "UNVERIFIED", "LIKELY_LEGITIMATE", "VERIFIED"):
            result = await sarvam_no_key.generate_hindi_report(
                verdict=verdict, trust_score=50, evidence=[]
            )
            assert isinstance(result, str)
            assert len(result) > 20, f"Empty fallback for {verdict}"

    @pytest.mark.asyncio
    async def test_api_success_returns_content(self, sarvam_with_key):
        """When API returns content, it's returned directly."""
        hindi_text = "Aapke liye yeh offer bahut risky hai."
        with patch("app.services.sarvam_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__  = AsyncMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": hindi_text}}]
            }
            mock_resp.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_resp)

            result = await sarvam_with_key.generate_hindi_report(
                verdict="HIGH_RISK", trust_score=10, evidence=[]
            )

        assert result == hindi_text


# ── Tests: Result normalisation ──────────────────────────────────────────────

class TestNormalisation:
    def test_all_keys_present(self, sarvam_no_key):
        """_normalise_result should always return all expected keys."""
        result = sarvam_no_key._normalise_result({"company_name": "Acme"})
        required = [
            "company_name", "email", "phone_number", "website_url",
            "recruiter_name", "job_title", "location", "salary_mentioned",
            "fee_amount", "urgency_indicators", "personal_email_for_corp_contact",
            "language_detected", "red_flags",
        ]
        for key in required:
            assert key in result, f"Missing key: {key}"

    def test_existing_values_not_overwritten(self, sarvam_no_key):
        result = sarvam_no_key._normalise_result({"company_name": "Acme", "fee_amount": 999})
        assert result["company_name"] == "Acme"
        assert result["fee_amount"] == 999
