import urllib.request
import urllib.error
import json

BASE = "http://localhost:8000"

def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        BASE + path,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

print("=" * 60)
print("TEST 1: Scam offer (should score LOW trust)")
print("=" * 60)
status, data = post("/api/v1/investigate", {
    "raw_input": "Your profile selected at Infosys. Salary 45k. Fee Rs.2499. Register at infosys-careers.in immediately! Contact us at hr@infosys-careers.in or +91 8888888888",
    "input_type": "paste"
})
print(f"Status: {status}")
print(f"Trust Score : {data.get('trust_score')}")
print(f"Verdict     : {data.get('verdict_label')}")
print(f"Entities    : {json.dumps(data.get('entities', {}), indent=2)}")
print(f"Confidence  : {data.get('confidence_score')}")
print(f"Hindi       : {data.get('hindi_explanation', '')[:120]}")
print()

print("=" * 60)
print("TEST 2: Sarvam health check")
print("=" * 60)
req2 = urllib.request.Request(BASE + "/api/v1/health/sarvam")
try:
    with urllib.request.urlopen(req2, timeout=15) as r:
        print(f"Status: {r.status}")
        print(json.loads(r.read()))
except urllib.error.HTTPError as e:
    print(f"Status: {e.code}")
    print(json.loads(e.read()))
