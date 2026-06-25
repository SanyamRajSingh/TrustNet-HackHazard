"""
Sarvam AI Integration Service — Production v3
Multi-language entity extraction and Hindi report generation.

REAL API CONTRACT (confirmed 2026-06-25 via test_sarvam.py):
- Auth header : api-subscription-key: <key>
- Chat model  : sarvam-30b  (models endpoint lists: sarvam-30b, sarvam-105b)
- Endpoint    : POST https://api.sarvam.ai/v1/chat/completions
- Hindi report: POST https://api.sarvam.ai/translate  (mayura:v1 model)

Supported languages: English, Hindi, Tamil, Kannada, Telugu, Bengali,
                     Marathi, Gujarati, Malayalam, Punjabi, Odia, Hinglish.

NO FALLBACKS. If the API key is missing or the call fails, an HTTPException
is raised immediately so the caller gets a clean 500 with the exact reason.
"""

import asyncio
import json
import re
from typing import Any, Dict, Optional

import httpx
import structlog
from fastapi import HTTPException

from config import settings

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Sarvam model / endpoint constants (verified working)
# ---------------------------------------------------------------------------
CHAT_MODEL    = "sarvam-30b"
CHAT_ENDPOINT = "/v1/chat/completions"
TRANSLATE_ENDPOINT = "/translate"

# ---------------------------------------------------------------------------
# Language code mapping (human name → Sarvam/BCP-47 hint)
# ---------------------------------------------------------------------------
LANGUAGE_CODES: Dict[str, str] = {
    "english":   "en-IN",
    "hindi":     "hi-IN",
    "hinglish":  "hi-IN",
    "tamil":     "ta-IN",
    "telugu":    "te-IN",
    "kannada":   "kn-IN",
    "bengali":   "bn-IN",
    "marathi":   "mr-IN",
    "gujarati":  "gu-IN",
    "malayalam": "ml-IN",
    "punjabi":   "pa-IN",
    "odia":      "or-IN",
}

# ---------------------------------------------------------------------------
# System prompt for entity extraction (kept tight for sarvam-30b)
# ---------------------------------------------------------------------------
EXTRACTION_SYSTEM_PROMPT = """\
You are an AI assistant that extracts structured information from Indian job \
offer texts to detect potential fraud.

Extract the following fields and return ONLY a valid JSON object \
(no markdown, no preamble, no explanation):
{
  "company_name":                    string | null,
  "email":                           string | null,
  "phone_number":                    string | null,
  "website_url":                     string | null,
  "recruiter_name":                  string | null,
  "job_title":                       string | null,
  "location":                        string | null,
  "salary_mentioned":                integer | null,
  "fee_amount":                      integer | null,
  "urgency_indicators":              boolean,
  "personal_email_for_corp_contact": boolean,
  "language_detected":               "english"|"hindi"|"hinglish"|"tamil"|\
"telugu"|"kannada"|"bengali"|"marathi"|"gujarati"|"malayalam"|"punjabi"|"odia"|"other",
  "red_flags":                       array of strings
}

Rules:
- salary_mentioned: normalise ALL formats to monthly INR integer.
  '3 LPA' → 25000, '40k/month' → 40000, '5.5 CTC' → 45833
- fee_amount: ANY payment requested in INR (registration, deposit, training, kit).
- urgency_indicators: true if text uses urgent / immediate / 24 hours / today / abhi / jaldi.
- personal_email_for_corp_contact: true if gmail/yahoo/outlook used for corporate claim.
- red_flags: list all suspicious signals found.
- No preamble, no markdown, no explanation — JSON only.\
"""


class SarvamService:
    """Sarvam AI API integration — production, no fallbacks."""

    def __init__(self):
        if not settings.SARVAM_API_KEY or settings.SARVAM_API_KEY.strip() == "":
            raise HTTPException(
                status_code=503,
                detail="SARVAM_API_KEY is not configured. Set it in your .env or Render environment."
            )
        self.api_key  = settings.SARVAM_API_KEY.strip()
        self.base_url = settings.SARVAM_API_BASE.rstrip("/")
        self.timeout  = settings.SARVAM_TIMEOUT
        self.headers  = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Public: entity extraction
    # ------------------------------------------------------------------

    async def extract_entities(
        self,
        input_text: str,
        language_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract entities from input text using Sarvam AI (sarvam-30b).

        Raises HTTPException on any failure — no silent fallbacks.
        """
        payload: Dict[str, Any] = {
            "model": CHAT_MODEL,
            "messages": [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user",   "content": input_text},
            ],
            "temperature": 0.0,
            "max_tokens": 500,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}{CHAT_ENDPOINT}",
                    json=payload,
                    headers=self.headers,
                )
                resp.raise_for_status()

            data    = resp.json()
            content = data["choices"][0]["message"]["content"]
            result  = self._parse_json_response(content)

            if not result:
                raise HTTPException(
                    status_code=502,
                    detail=f"Sarvam returned unparseable JSON: {content[:300]}"
                )

            logger.info(
                "sarvam_extraction.success",
                model=CHAT_MODEL,
                language=result.get("language_detected"),
                company=result.get("company_name"),
                tokens=data.get("usage", {}).get("total_tokens"),
            )
            return self._normalise_result(result)

        except httpx.HTTPStatusError as exc:
            logger.error(
                "sarvam_extraction.http_error",
                status=exc.response.status_code,
                body=exc.response.text[:500],
            )
            raise HTTPException(
                status_code=502,
                detail=f"Sarvam API error {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except httpx.TimeoutException:
            logger.error("sarvam_extraction.timeout", timeout=self.timeout)
            raise HTTPException(
                status_code=504,
                detail=f"Sarvam API timed out after {self.timeout}s"
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("sarvam_extraction.unexpected_error", error=str(exc))
            raise HTTPException(
                status_code=502,
                detail=f"Sarvam extraction failed: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Public: Hindi report generation via /translate
    # ------------------------------------------------------------------

    async def generate_hindi_from_investigation(
        self,
        trust_score: int,
        verdict: str,
        key_findings: list,
        entities: Dict[str, Any],
    ) -> str:
        """
        Generate a Hindi explanation using Sarvam's /translate endpoint.

        Builds an English summary and translates it to Hindi with mayura:v1.
        Raises HTTPException on failure.
        """
        fee = entities.get("fee_amount")
        company = entities.get("company_name") or "The company"
        red_flags = entities.get("red_flags", [])

        # Build a natural English summary to translate
        summary_parts = [
            f"This job offer has a trust score of {trust_score} out of 100.",
            f"Verdict: {verdict.replace('_', ' ').title()}.",
        ]
        if fee:
            summary_parts.append(f"A payment of Rs. {fee:,} was requested. Legitimate employers never charge fees.")
        if red_flags:
            summary_parts.append(f"Suspicious signals found: {', '.join(red_flags[:3])}.")
        if trust_score <= 25:
            summary_parts.append("This is almost certainly a scam. Do not pay any money. Report it to cybercrime.gov.in.")
        elif trust_score <= 45:
            summary_parts.append("This offer is suspicious. Verify the company on MCA.gov.in before proceeding.")
        else:
            summary_parts.append("This offer appears legitimate but always verify through official channels.")

        english_text = " ".join(summary_parts)

        payload = {
            "input": english_text,
            "source_language_code": "en-IN",
            "target_language_code": "hi-IN",
            "speaker_gender": "Female",
            "mode": "formal",
            "model": "mayura:v1",
            "enable_preprocessing": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}{TRANSLATE_ENDPOINT}",
                    json=payload,
                    headers=self.headers,
                )
                resp.raise_for_status()

            data = resp.json()
            hindi_text = data.get("translated_text", "")
            logger.info("sarvam.hindi_report.success", length=len(hindi_text))
            return hindi_text

        except httpx.HTTPStatusError as exc:
            logger.error(
                "sarvam.hindi_report.http_error",
                status=exc.response.status_code,
                body=exc.response.text[:300],
            )
            raise HTTPException(
                status_code=502,
                detail=f"Sarvam translate error {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Sarvam /translate timed out")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Sarvam translate failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Health ping — for /api/v1/health/sarvam
    # ------------------------------------------------------------------

    async def ping(self) -> Dict[str, Any]:
        """
        Ping Sarvam by calling /v1/models.
        Returns {"status": "ok", "models": [...]} or raises HTTPException.
        """
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(
                    f"{self.base_url}/v1/models",
                    headers=self.headers,
                )
                resp.raise_for_status()
            data = resp.json()
            model_ids = [m["id"] for m in data.get("data", [])]
            logger.info("health.sarvam.ok", models=model_ids)
            return {"status": "ok", "models": model_ids, "active_model": CHAT_MODEL}
        except Exception as exc:
            logger.error("health.sarvam.failed", error=str(exc))
            raise HTTPException(
                status_code=503,
                detail=f"Sarvam API unreachable: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling markdown code fences."""
        content = content.strip()
        for extractor in [
            lambda c: json.loads(c),
            lambda c: json.loads(re.search(r'```(?:json)?\s*(.*?)\s*```', c, re.DOTALL).group(1)),
            lambda c: json.loads(re.search(r'\{.*\}', c, re.DOTALL).group(0)),
        ]:
            try:
                return extractor(content)
            except Exception:
                continue
        return {}

    def _normalise_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all expected keys are present with sensible defaults."""
        defaults: Dict[str, Any] = {
            "company_name":                    None,
            "email":                           None,
            "phone_number":                    None,
            "website_url":                     None,
            "recruiter_name":                  None,
            "job_title":                       None,
            "location":                        None,
            "salary_mentioned":                None,
            "fee_amount":                      None,
            "urgency_indicators":              False,
            "personal_email_for_corp_contact": False,
            "language_detected":               "english",
            "red_flags":                       [],
        }
        for key, default in defaults.items():
            if key not in result:
                result[key] = default
        return result


# Module-level singleton used by API routes
sarvam_service = SarvamService()