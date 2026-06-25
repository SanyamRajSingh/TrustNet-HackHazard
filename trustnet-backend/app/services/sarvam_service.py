"""
Sarvam AI Integration Service — v2
Multi-language entity extraction, voice transcription, Hindi report generation.

Supports: English, Hindi, Tamil, Kannada, Telugu, Bengali, Marathi, Gujarati,
          Malayalam, Punjabi, Odia, and Hinglish.

Falls back gracefully to regex extraction when the API key is absent or the
call times out / returns an error.
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional

import httpx
import structlog

from config import settings

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Language code mapping (ISO 639-1 / BCP-47 → Sarvam hint)
# ---------------------------------------------------------------------------
LANGUAGE_CODES: Dict[str, str] = {
    "english":    "en-IN",
    "hindi":      "hi-IN",
    "hinglish":   "hi-IN",
    "tamil":      "ta-IN",
    "telugu":     "te-IN",
    "kannada":    "kn-IN",
    "bengali":    "bn-IN",
    "marathi":    "mr-IN",
    "gujarati":   "gu-IN",
    "malayalam":  "ml-IN",
    "punjabi":    "pa-IN",
    "odia":       "or-IN",
}

# ---------------------------------------------------------------------------
# Regex patterns for offline fallback
# ---------------------------------------------------------------------------
EMAIL_PATTERN  = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PHONE_PATTERN  = re.compile(r'(?:\+91|0)?[\s-]?[6789]\d{9}')
URL_PATTERN    = re.compile(
    r'https?://(?:[-\w.])+(?::\d+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.]*)?)?(?:#(?:[\w.])*)?)?',
    re.IGNORECASE,
)
SALARY_PATTERN = re.compile(
    r'(?:Rs\.?\s*|INR\s*|₹\s*)(\d[\d,]*(?:\.\d+)?)\s*(?:k|thousand)?',
    re.IGNORECASE,
)
FEE_PATTERN    = re.compile(
    r'(?:fee|charges|registration|payment)\s*(?:of\s*)?(?:Rs\.?\s*|INR\s*|₹\s*)(\d[\d,]*(?:\.\d+)?)',
    re.IGNORECASE,
)
JOB_TITLE_PATTERN = re.compile(
    r'(?:position of|role of|vacancy for|post of|designation[:\s]+)\s*'
    r'([A-Z][A-Za-z\s\-]+?)'
    r'(?:\s+(?:at|in|for|with)\s|[,\.;]|$)',
    re.IGNORECASE,
)
LOCATION_PATTERN = re.compile(
    r'(?:location[:\s]+|based in|work from|office at|office in|working from)\s*'
    r'([A-Za-z][A-Za-z\s,]+?)'
    r'(?:\s+(?:office|and|or|offers)\s|[,\.;]|$)',
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------
EXTRACTION_SYSTEM_PROMPT = """\
You are an expert entity extractor for Indian job fraud detection.
Extract all entities from the text below. The text may be in English, Hindi,
Tamil, Kannada, Telugu, Bengali, Marathi, Gujarati, Hinglish, or a mix.

Return ONLY a valid JSON object with these exact fields:
{
  "company_name":                 string | null,
  "email":                        string | null,
  "phone_number":                 string | null,
  "website_url":                  string | null,
  "recruiter_name":               string | null,
  "job_title":                    string | null,
  "location":                     string | null,
  "salary_mentioned":             integer | null,
  "fee_amount":                   integer | null,
  "urgency_indicators":           boolean,
  "personal_email_for_corp_contact": boolean,
  "language_detected":            "english"|"hindi"|"hinglish"|"tamil"|"telugu"|"kannada"|"bengali"|"marathi"|"gujarati"|"malayalam"|"punjabi"|"odia"|"other",
  "red_flags":                    array of strings
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

HINDI_REPORT_SYSTEM_PROMPT = """\
You are a fraud awareness assistant for Indian job seekers.
Explain the investigation result in simple Hindi (Class 10 level).
Speak directly to the student ('aapke liye'). Max 120 words.
Be empathetic and clear. Give actionable advice.\
"""


class SarvamService:
    """Sarvam AI API integration for extraction, voice, and Hindi generation."""

    def __init__(self):
        self.api_key     = settings.SARVAM_API_KEY.strip()
        self.base_url    = settings.SARVAM_API_BASE
        self.timeout     = settings.SARVAM_TIMEOUT
        self.max_retries = settings.SARVAM_MAX_RETRIES
        self.headers = {
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
        Extract entities from input text using Sarvam AI.

        Multi-language: pass language_hint as a language name (e.g. "hindi",
        "tamil") or a BCP-47 code ("hi-IN"). If absent, Sarvam auto-detects.

        Falls back to regex extraction when:
          • SARVAM_API_KEY is empty / a placeholder
          • The API call times out or returns an HTTP error
        """
        if not self.api_key or self.api_key in ("dummy", ""):
            logger.warning(
                "sarvam_extraction.no_api_key",
                msg="SARVAM_API_KEY not configured — using regex fallback",
            )
            return self._regex_extraction(input_text)

        # Normalise language hint to BCP-47
        lang_code = self._resolve_language_code(language_hint)

        try:
            result = await asyncio.wait_for(
                self._call_sarvam_extraction(input_text, lang_code),
                timeout=self.timeout,
            )
            if result and isinstance(result, dict):
                # Merge any missing fields from regex so we always have full data
                regex_fill = self._regex_extraction(input_text)
                for key in ("email", "phone_number", "website_url", "salary_mentioned",
                            "fee_amount", "job_title", "location"):
                    if result.get(key) is None and regex_fill.get(key) is not None:
                        result[key] = regex_fill[key]
                logger.info(
                    "sarvam_extraction.success",
                    language=result.get("language_detected"),
                    company=result.get("company_name"),
                )
                return self._normalise_result(result)
        except asyncio.TimeoutError:
            logger.warning(
                "sarvam_extraction.timeout",
                msg=f"Timed out after {self.timeout}s — using regex fallback",
            )
        except Exception as exc:
            logger.warning(
                "sarvam_extraction.api_error",
                error=str(exc),
                msg="API error — using regex fallback",
            )

        logger.warning("sarvam_extraction.using_regex_fallback")
        return self._regex_extraction(input_text)

    # ------------------------------------------------------------------
    # Internal: Sarvam API call
    # ------------------------------------------------------------------

    async def _call_sarvam_extraction(
        self,
        input_text: str,
        lang_code: Optional[str],
    ) -> Dict[str, Any]:
        """Make the actual HTTP call to Sarvam chat completions."""
        payload: Dict[str, Any] = {
            "messages": [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user",   "content": input_text},
            ],
            "model":       "sarvam-2b",
            "temperature": 0.1,
        }
        if lang_code:
            payload["language_code"] = lang_code

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                        headers=self.headers,
                    )
                    if resp.status_code == 429:
                        await asyncio.sleep(1.0 * (attempt + 1))
                        continue
                    resp.raise_for_status()
                    data    = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return self._parse_json_response(content)
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 429 and attempt < self.max_retries - 1:
                        await asyncio.sleep(1.0 * (attempt + 1))
                        continue
                    raise
        return {}

    # ------------------------------------------------------------------
    # Health ping for monitoring endpoint
    # ------------------------------------------------------------------

    async def ping(self) -> Dict[str, Any]:
        """
        Ping the Sarvam API to check availability.
        Returns {"status": "ok"} or {"status": "degraded", "fallback": True, "reason": ...}
        """
        if not self.api_key or self.api_key in ("dummy", ""):
            return {
                "status":   "degraded",
                "fallback": True,
                "reason":   "SARVAM_API_KEY not configured",
            }
        payload = {
            "messages": [
                {"role": "user", "content": "ping"},
            ],
            "model":       "sarvam-2b",
            "temperature": 0.0,
            "max_tokens":  1,
        }
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=self.headers,
                )
                if resp.status_code in (200, 201):
                    return {"status": "ok"}
                return {
                    "status":   "degraded",
                    "fallback": True,
                    "reason":   f"HTTP {resp.status_code}",
                }
        except asyncio.TimeoutError:
            return {"status": "degraded", "fallback": True, "reason": "timeout"}
        except Exception as exc:
            return {"status": "degraded", "fallback": True, "reason": str(exc)}

    # ------------------------------------------------------------------
    # Regex-based fallback
    # ------------------------------------------------------------------

    def _regex_extraction(self, text: str) -> Dict[str, Any]:
        """Full offline entity extraction using regex patterns."""
        emails   = EMAIL_PATTERN.findall(text)
        phones   = PHONE_PATTERN.findall(text)
        urls     = URL_PATTERN.findall(text)
        salaries = SALARY_PATTERN.findall(text)
        fees     = FEE_PATTERN.findall(text)

        # Normalise phone
        phone = None
        if phones:
            raw = re.sub(r'\D', '', phones[0])
            if len(raw) == 10:
                phone = f"+91{raw}"
            elif len(raw) == 12 and raw.startswith("91"):
                phone = f"+{raw}"

        # Salary → monthly INR
        salary = None
        if salaries:
            raw_sal = salaries[0].replace(",", "")
            try:
                val = float(raw_sal)
                text_lower = text.lower()
                if "lpa" in text_lower or "ctc" in text_lower:
                    salary = int(val * 100_000 / 12)
                elif "k" in text_lower:
                    salary = int(val * 1_000)
                else:
                    salary = int(val)
            except ValueError:
                pass

        # Fee
        fee = None
        if fees:
            try:
                fee = int(float(fees[0].replace(",", "")))
            except ValueError:
                pass

        # Job title
        job_title = None
        jt_match = JOB_TITLE_PATTERN.search(text)
        if jt_match:
            job_title = jt_match.group(1).strip()

        # Location
        location = None
        loc_match = LOCATION_PATTERN.search(text)
        if loc_match:
            location = loc_match.group(1).strip()

        # Red flags
        urgency_words = [
            "urgent", "immediate", "24 hour", "24 ghante", "limited",
            "today", "abhi", "turant", "jaldi",
        ]
        red_flags: List[str] = []
        if any(w in text.lower() for w in urgency_words):
            red_flags.append("Urgency language detected")
        if fee and fee > 0:
            red_flags.append(f"Fee requested: ₹{fee}")
        personal_domains = {"gmail.com", "yahoo.com", "outlook.com", "rediffmail.com", "hotmail.com"}
        has_personal_email = bool(
            emails and any(emails[0].split("@")[-1].lower() in personal_domains for _ in [1])
        )
        if has_personal_email:
            red_flags.append("Personal email used for corporate contact")

        return {
            "company_name":                    None,
            "email":                           emails[0] if emails else None,
            "phone_number":                    phone,
            "website_url":                     urls[0] if urls else None,
            "recruiter_name":                  None,
            "job_title":                       job_title,
            "location":                        location,
            "salary_mentioned":                salary,
            "fee_amount":                      fee,
            "urgency_indicators":              any(w in text.lower() for w in urgency_words),
            "personal_email_for_corp_contact": has_personal_email,
            "language_detected":               self._detect_language(text),
            "red_flags":                       red_flags,
        }

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _resolve_language_code(self, hint: Optional[str]) -> Optional[str]:
        """Convert a human language name or BCP-47 code to Sarvam's expected format."""
        if not hint:
            return None
        hint_lower = hint.lower().strip()
        # Already a BCP-47 code?
        if "-" in hint_lower:
            return hint
        return LANGUAGE_CODES.get(hint_lower)

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling markdown code fences."""
        content = content.strip()
        for attempt in [
            lambda c: json.loads(c),
            lambda c: json.loads(re.search(r'```(?:json)?\s*(.*?)\s*```', c, re.DOTALL).group(1)),
            lambda c: json.loads(re.search(r'\{.*\}', c, re.DOTALL).group(0)),
        ]:
            try:
                return attempt(content)
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

    def _detect_language(self, text: str) -> str:
        """Simple heuristic language detection."""
        text_lower = text.lower()
        checks: List[tuple] = [
            ("tamil",     ["ungal", "ungalukku", "vaalthukkal", "aayam", "seythi"], 2),
            ("telugu",    ["meeku", "meela", "paniki", "jeetham", "nela"],           2),
            ("kannada",   ["nimma", "naavu", "illi", "avaru", "yenu"],               2),
            ("bengali",   ["apnar", "amar", "kazi", "taka", "korben"],               2),
            ("marathi",   ["tumhi", "amhi", "rupaye", "kaam", "karaa"],              2),
            ("hindi",     ["aapka", "hai", "hain", "ka", "ke", "mein", "se",
                           "ko", "aur", "rupaye", "bhej", "karein", "bataiye"],     3),
            ("hinglish",  ["aapka", "hai", "hain", "ka", "ke", "mein"],             1),
        ]
        for lang, words, threshold in checks:
            if sum(1 for w in words if w in text_lower) >= threshold:
                return lang
        return "english"

    # ------------------------------------------------------------------
    # Voice transcription
    # ------------------------------------------------------------------

    async def transcribe_voice(
        self,
        audio_base64: str,
        mime_type: str = "audio/wav",
    ) -> str:
        """Transcribe audio to text via Sarvam speech-to-text."""
        if not self.api_key or self.api_key in ("dummy", ""):
            logger.warning("sarvam.voice.no_api_key")
            return ""

        payload = {
            "audio":     audio_base64,
            "mime_type": mime_type,
            "model":     "saaras:stt",
        }
        async with httpx.AsyncClient() as client:
            for attempt in range(self.max_retries):
                try:
                    resp = await client.post(
                        f"{self.base_url}/speech-to-text",
                        json=payload,
                        headers=self.headers,
                        timeout=10,
                    )
                    if resp.status_code == 429:
                        await asyncio.sleep(1.0 * (attempt + 1))
                        continue
                    resp.raise_for_status()
                    transcript = resp.json().get("transcript", "")
                    logger.info("sarvam.voice.transcription_success", length=len(transcript))
                    return transcript
                except httpx.HTTPStatusError:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(1.0 * (attempt + 1))
                        continue
                    raise
        return ""

    # ------------------------------------------------------------------
    # Hindi report generation
    # ------------------------------------------------------------------

    async def generate_hindi_report(
        self,
        verdict: str,
        trust_score: int,
        evidence: List[Dict[str, str]],
    ) -> str:
        """
        Generate a Hindi explanation of investigation results.
        Falls back to a template if API key is missing or call fails.
        """
        if not self.api_key or self.api_key in ("dummy", ""):
            logger.warning(
                "sarvam.hindi_report.no_api_key",
                msg="SARVAM_API_KEY not set — using template fallback",
            )
            return self._hindi_fallback(verdict, trust_score)

        evidence_text = "; ".join(
            f"{e['category']}: {e['finding']}" for e in evidence[:5]
        )
        prompt  = f"Verdict: {verdict} | Trust Score: {trust_score}/100\nKey Evidence: {evidence_text}"
        payload = {
            "messages": [
                {"role": "system", "content": HINDI_REPORT_SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            "model":       "sarvam-1",
            "temperature": 0.7,
        }
        async with httpx.AsyncClient() as client:
            for attempt in range(self.max_retries):
                try:
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                        headers=self.headers,
                        timeout=self.timeout,
                    )
                    if resp.status_code == 429:
                        await asyncio.sleep(1.0 * (attempt + 1))
                        continue
                    resp.raise_for_status()
                    content = resp.json()["choices"][0]["message"]["content"]
                    logger.info("sarvam.hindi_report.generated", length=len(content))
                    return content.strip()
                except Exception as exc:
                    logger.warning("sarvam.hindi_report.error", error=str(exc))
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(1.0)
                        continue
        return self._hindi_fallback(verdict, trust_score)

    def _hindi_fallback(self, verdict: str, trust_score: int) -> str:
        """Template-based Hindi report when API is unavailable."""
        templates = {
            "HIGH_RISK": (
                f"Aapke liye yeh jaanch karne par hamne paaya ki yeh job offer "
                f"{trust_score}/100 trust score ke saath HIGH RISK hai. "
                f"Kripya is offer ko bilkul bhi na maanein aur koi bhi payment na karein. "
                f"Yeh ek aam phishing prakaar ka scam lagta hai. "
                f"Aap cybercrime.gov.in par report kar sakte hain."
            ),
            "SUSPICIOUS": (
                f"Yeh job offer {trust_score}/100 trust score ke saath SUSPICIOUS hai. "
                f"Kuch cheezein theek nahi lagti hain. Bariki se verify karein. "
                f"Koi advance payment na karein. Company ki official website se verify karein."
            ),
            "UNVERIFIED": (
                f"Is offer ke baare mein hamare paas {trust_score}/100 trust score ke saath "
                f"kaafi jaankari nahi hai. Kripya apni research karein aur company ke "
                f"official channels se contact karein."
            ),
            "LIKELY_LEGITIMATE": (
                f"Yeh job offer {trust_score}/100 trust score ke saath LIKELY SAFE hai. "
                f"Phir bhi, kripya company ke official HR se verify karein. "
                f"Koi bhi payment karne se pehle do baar sochein."
            ),
            "VERIFIED": (
                f"Yeh job offer {trust_score}/100 trust score ke saath verified hai. "
                f"Company ki jaanch poori hui hai. Phir bhi, swatantra roop se bhi verify karein."
            ),
        }
        return templates.get(verdict, templates["UNVERIFIED"])

    async def generate_hindi_from_investigation(
        self, investigation_data: Dict[str, Any]
    ) -> str:
        """Convenience wrapper for generating Hindi from investigation result dict."""
        return await self.generate_hindi_report(
            verdict=investigation_data.get("verdict", "UNVERIFIED"),
            trust_score=investigation_data.get("trust_score", 50),
            evidence=investigation_data.get("evidence", []),
        )