"""
Regression + regression check against the live endpoint.
Run with: python scripts/regression_check.py
"""
import datetime
import json
import sys
import urllib.error
import urllib.request

ENDPOINT = "https://trustnet-backend.onrender.com/api/v1/investigate"

PAYLOADS = [
    {
        "label": "HIGH_RISK input",
        "body": {
            "raw_input": (
                "Urgent job offer from Infosys Ltd. Contact recruiter Priya Sharma "
                "at hr@infosys-careers.in. Visit infosys-careers.in for details. "
                "Salary Rs 60000/month. Pay Rs 4500 registration fee via Google Pay "
                "to 9876543210 within 24 hours. Offer expires today."
            ),
            "input_type": "paste",
        },
    },
    {
        "label": "LOW_RISK input",
        "body": {
            "raw_input": (
                "Job opening at TCS Pune. Email: recruitment@tcs.com. "
                "Position: Software Engineer. CTC 8 LPA. No fees required."
            ),
            "input_type": "paste",
        },
    },
]

REQUIRED_FIELDS = [
    "id", "trust_score", "confidence_score", "verdict",
    "verdict_label", "verdict_color", "entities",
    "category_scores", "evidence", "processing_ms", "created_at",
]
OPTIONAL_FIELDS = ["hindi_explanation", "graph_connections", "blockchain_tx_hash"]

ENTITY_FIELDS = [
    "company_name", "email", "phone_number", "website_url",
    "recruiter_name", "job_title", "location", "salary_mentioned",
    "fee_amount", "urgency_indicators", "personal_email_for_corp_contact",
    "language_detected", "red_flags",
]

all_passed = True

for case in PAYLOADS:
    print(f"\n{'='*60}")
    print(f"TEST CASE: {case['label']}")
    print("="*60)

    data = json.dumps(case["body"]).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            status = r.status
            body = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8")[:500]
        print(f"HTTP ERROR {e.code}: {body_text}")
        all_passed = False
        continue
    except Exception as ex:
        print(f"REQUEST ERROR: {type(ex).__name__}: {ex}")
        all_passed = False
        continue

    print(f"STATUS: {status}")
    if status != 200:
        all_passed = False
        continue

    # Required fields
    missing = [f for f in REQUIRED_FIELDS if f not in body]
    extra = [k for k in body if k not in REQUIRED_FIELDS + OPTIONAL_FIELDS]
    print(f"Missing required fields: {missing or 'NONE'}")
    print(f"Unexpected extra fields:  {extra or 'NONE'}")
    if missing:
        all_passed = False

    # Type checks
    checks = {
        "trust_score is int": isinstance(body.get("trust_score"), int),
        "confidence_score is int": isinstance(body.get("confidence_score"), int),
        "verdict is str": isinstance(body.get("verdict"), str),
        "evidence is list": isinstance(body.get("evidence"), list),
        "entities is dict": isinstance(body.get("entities"), dict),
        "processing_ms is int": isinstance(body.get("processing_ms"), int),
        "created_at is ISO str": isinstance(body.get("created_at"), str),
    }
    for check, passed in checks.items():
        status_str = "PASS" if passed else "FAIL"
        print(f"  [{status_str}] {check}")
        if not passed:
            all_passed = False

    # created_at parses as ISO-8601
    try:
        datetime.datetime.fromisoformat(body["created_at"])
        print("  [PASS] created_at parses as ISO-8601")
    except Exception as ex:
        print(f"  [FAIL] created_at not ISO-8601: {ex}")
        all_passed = False

    # graph_connections — no temporal object leaked
    gc = body.get("graph_connections")
    if gc is not None:
        leaked = []
        for node in gc.get("nodes", []):
            for k, v in node.get("properties", {}).items():
                if hasattr(v, "isoformat") and not isinstance(v, str):
                    leaked.append(f"node.properties.{k}: {type(v)}")
        if leaked:
            print(f"  [FAIL] Temporal objects leaked in graph_connections: {leaked}")
            all_passed = False
        else:
            print("  [PASS] graph_connections has no leaked temporal objects")
        print(f"  graph nodes: {len(gc.get('nodes', []))}, rels: {len(gc.get('relationships', []))}")

    # Evidence shape
    ev_ok = all(
        "category" in e and "finding" in e and "severity" in e
        for e in body.get("evidence", [])
    )
    print(f"  [{'PASS' if ev_ok else 'FAIL'}] evidence items have required fields")
    if not ev_ok:
        all_passed = False
    print(f"  evidence count: {len(body.get('evidence', []))}")

    # Entities shape
    ent = body.get("entities", {})
    missing_ent = [f for f in ENTITY_FIELDS if f not in ent]
    print(f"  [{'PASS' if not missing_ent else 'FAIL'}] entities fields complete")
    if missing_ent:
        print(f"    missing: {missing_ent}")
        all_passed = False

    print(f"\n  verdict={body.get('verdict')} | trust_score={body.get('trust_score')} | confidence={body.get('confidence_score')}")
    print(f"  hindi_explanation present: {bool(body.get('hindi_explanation'))}")

print("\n" + "="*60)
if all_passed:
    print("ALL REGRESSION CHECKS PASSED")
    sys.exit(0)
else:
    print("REGRESSION FAILURES DETECTED - see above")
    sys.exit(1)
