"""
Sarvam API — confirmed working config test
Models: sarvam-30b, sarvam-105b
"""
import urllib.request, urllib.error, json, sys

API_KEY = "sk_0gmc7kpd_zeSbFO6PH1LiqB1AX8v6YtDK"
BASE = "https://api.sarvam.ai"
HEADERS = {"api-subscription-key": API_KEY, "Content-Type": "application/json"}
TEXT = "I received a job offer from ABC Corp Ltd. They asked me to pay Rs.5000 for training. The email is hr@abccorp.in and the website is abccorp-investment.com. Contact: +91 9876543210."

EXTRACTION_PROMPT = """You are an AI assistant that extracts structured information from Indian job offer texts to detect potential scams.

Extract the following fields and return ONLY a valid JSON object (no markdown, no preamble):
{
  "company_name": "<string or null>",
  "email": "<string or null>",
  "phone_number": "<string or null>",
  "website_url": "<string or null>",
  "job_title": "<string or null>",
  "location": "<string or null>",
  "salary_mentioned": <number in INR or null>,
  "fee_amount": <number in INR or null>,
  "urgency_indicators": <true|false>,
  "personal_email_for_corp_contact": <true|false>,
  "language_detected": "<english|hindi|hinglish|tamil|telugu|kannada|bengali|marathi|gujarati|malayalam>",
  "red_flags": ["<list of suspicious signals>"]
}"""

def post(url, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())
    except Exception as ex:
        return 0, {"error": str(ex)}

print("TEST 1: Chat completion with sarvam-30b")
status, body = post(f"{BASE}/v1/chat/completions", {
    "model": "sarvam-30b",
    "messages": [
        {"role": "system", "content": EXTRACTION_PROMPT},
        {"role": "user", "content": TEXT}
    ],
    "temperature": 0.0,
    "max_tokens": 400,
})
print(f"Status: {status}")
print(json.dumps(body, ensure_ascii=False, indent=2)[:1500])

print("\nTEST 2: Chat completion with sarvam-105b")
status2, body2 = post(f"{BASE}/v1/chat/completions", {
    "model": "sarvam-105b",
    "messages": [
        {"role": "system", "content": EXTRACTION_PROMPT},
        {"role": "user", "content": TEXT}
    ],
    "temperature": 0.0,
    "max_tokens": 400,
})
print(f"Status: {status2}")
print(json.dumps(body2, ensure_ascii=False, indent=2)[:1500])

print("\nTEST 3: /translate for Hindi report generation")
status3, body3 = post(f"{BASE}/translate", {
    "input": "This job offer has a trust score of 14/100. A fee of Rs. 5000 was requested. This is a likely scam.",
    "source_language_code": "en-IN",
    "target_language_code": "hi-IN",
    "speaker_gender": "Male",
    "mode": "formal",
    "model": "mayura:v1",
    "enable_preprocessing": False,
})
print(f"Status: {status3}")
print(json.dumps(body3, ensure_ascii=False, indent=2)[:800])
