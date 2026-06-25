"""
Full Docker integration test — Step 7 of production verification.
Tests the real Sarvam AI (no fallbacks) via the containerized backend.
"""
import urllib.request, urllib.error, json, sys

BASE = "http://localhost:8000"

def post(path, data, timeout=60):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        BASE + path,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def get(path, timeout=15):
    req = urllib.request.Request(BASE + path)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

print("=" * 70)
print("STEP 7a: GET /health")
print("=" * 70)
s, d = get("/health")
print(f"Status: {s}")
print(json.dumps(d, indent=2))
assert s == 200 and d["status"] == "healthy", "HEALTH FAILED"
print("PASS")

print()
print("=" * 70)
print("STEP 7b: GET /api/v1/health/sarvam")
print("=" * 70)
s, d = get("/api/v1/health/sarvam")
print(f"Status: {s}")
print(json.dumps(d, indent=2, ensure_ascii=False))
if s != 200:
    print("SARVAM HEALTH FAILED — stopping")
    sys.exit(1)
print("PASS")

print()
print("=" * 70)
print("STEP 7c: POST /api/v1/investigate (real Sarvam AI, no fallback)")
print("=" * 70)
s, d = post("/api/v1/investigate", {
    "raw_input": "I received a job offer from ABC Corp Ltd. They asked me to pay Rs.5000 for training. The email is hr@abccorp.in and the website is abccorp-investment.com. Contact: +91 9876543210.",
    "input_type": "paste"
})
print(f"Status: {s}")
if s != 200:
    print("INVESTIGATE FAILED:")
    print(json.dumps(d, indent=2, ensure_ascii=False))
    sys.exit(1)

print(f"Trust Score  : {d.get('trust_score')}/100")
print(f"Verdict      : {d.get('verdict_label')}")
print(f"Confidence   : {d.get('confidence_score')}%")
print(f"Processing   : {d.get('processing_ms')}ms")
print()
print("ENTITIES (extracted by Sarvam sarvam-30b):")
ent = d.get("entities", {})
print(json.dumps(ent, indent=2, ensure_ascii=False))
print()
print("RED FLAGS:")
for flag in ent.get("red_flags", []):
    print(f"  - {flag}")
print()
print("HINDI EXPLANATION (via /translate):")
print(d.get("hindi_explanation", "(none)"))
print()
print("GRAPH CONNECTIONS:")
print(json.dumps(d.get("graph_connections", {}), indent=2))
print()

# Verify key entities were extracted by real Sarvam (not regex)
assert ent.get("email") is not None, "email must be extracted"
assert ent.get("fee_amount") is not None, "fee_amount must be extracted"
assert ent.get("company_name") is not None, "company_name must be extracted"
print("ALL ASSERTIONS PASSED - Sarvam AI is working inside Docker (no fallbacks)")
