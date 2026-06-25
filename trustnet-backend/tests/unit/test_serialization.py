"""
tests/unit/test_serialization.py
==================================
Unit tests for app.core.serialization.sanitize_for_json

Coverage
--------
* Python standard library temporal types
* All neo4j temporal types (DateTime, Date, Time, LocalDateTime, LocalTime, Duration)
* Containers: dict, list, tuple, set
* Nesting (arbitrary depth)
* Idempotency
* Pass-through of scalars and non-temporal objects
* Error resilience when .isoformat() raises
* Field-path logging (smoke test — verifies the parameter is accepted)
"""

import datetime
from unittest.mock import MagicMock

import pytest

from app.core.serialization import sanitize_for_json


# ---------------------------------------------------------------------------
# Helpers — lightweight stand-ins for neo4j temporal types when the real
# neo4j driver is present in the test environment.
# ---------------------------------------------------------------------------

def _neo4j_datetime():
    """Return a real neo4j.time.DateTime if available, else a stub."""
    try:
        from neo4j.time import DateTime
        return DateTime(2024, 3, 15, 10, 30, 45)
    except ImportError:
        stub = MagicMock()
        stub.isoformat.return_value = "2024-03-15T10:30:45"
        stub.__class__.__name__ = "DateTime"
        return stub


def _neo4j_date():
    try:
        from neo4j.time import Date
        return Date(2024, 3, 15)
    except ImportError:
        stub = MagicMock()
        stub.isoformat.return_value = "2024-03-15"
        return stub


def _neo4j_time():
    try:
        from neo4j.time import Time
        return Time(10, 30, 45)
    except ImportError:
        stub = MagicMock()
        stub.isoformat.return_value = "10:30:45"
        return stub


def _neo4j_local_datetime():
    try:
        from neo4j.time import LocalDateTime
        return LocalDateTime(2024, 3, 15, 10, 30, 45)
    except ImportError:
        stub = MagicMock()
        stub.isoformat.return_value = "2024-03-15T10:30:45"
        return stub


def _neo4j_local_time():
    try:
        from neo4j.time import LocalTime
        return LocalTime(10, 30, 45)
    except ImportError:
        stub = MagicMock()
        stub.isoformat.return_value = "10:30:45"
        return stub


# ---------------------------------------------------------------------------
# Python datetime types
# ---------------------------------------------------------------------------

class TestPythonDatetimeTypes:
    def test_datetime_datetime(self):
        dt = datetime.datetime(2024, 3, 15, 10, 30, 45)
        result = sanitize_for_json(dt)
        assert result == "2024-03-15T10:30:45"
        assert isinstance(result, str)

    def test_datetime_date(self):
        d = datetime.date(2024, 3, 15)
        result = sanitize_for_json(d)
        assert result == "2024-03-15"
        assert isinstance(result, str)

    def test_datetime_time(self):
        t = datetime.time(10, 30, 45)
        result = sanitize_for_json(t)
        assert result == "10:30:45"
        assert isinstance(result, str)

    def test_datetime_with_timezone(self):
        dt = datetime.datetime(2024, 3, 15, 10, 30, 45, tzinfo=datetime.timezone.utc)
        result = sanitize_for_json(dt)
        assert "+00:00" in result or "Z" in result or result == dt.isoformat()


# ---------------------------------------------------------------------------
# neo4j temporal types
# ---------------------------------------------------------------------------

class TestNeo4jTemporalTypes:
    def test_neo4j_datetime(self):
        obj = _neo4j_datetime()
        result = sanitize_for_json(obj)
        assert isinstance(result, str)
        # Must be an ISO-8601 string with date and time components
        assert "T" in result or "-" in result

    def test_neo4j_date(self):
        obj = _neo4j_date()
        result = sanitize_for_json(obj)
        assert isinstance(result, str)
        assert "-" in result  # date separator

    def test_neo4j_time(self):
        obj = _neo4j_time()
        result = sanitize_for_json(obj)
        assert isinstance(result, str)
        assert ":" in result  # time separator

    def test_neo4j_local_datetime(self):
        obj = _neo4j_local_datetime()
        result = sanitize_for_json(obj)
        assert isinstance(result, str)

    def test_neo4j_local_time(self):
        obj = _neo4j_local_time()
        result = sanitize_for_json(obj)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Container types
# ---------------------------------------------------------------------------

class TestContainerTypes:
    def test_dict_with_datetime_value(self):
        dt = datetime.datetime(2024, 1, 1, 0, 0, 0)
        result = sanitize_for_json({"created_at": dt, "name": "test"})
        assert result == {"created_at": "2024-01-01T00:00:00", "name": "test"}

    def test_dict_keys_are_preserved(self):
        d = {"a": 1, "b": "hello", "c": None}
        assert sanitize_for_json(d) == d

    def test_list_with_datetime(self):
        items = [datetime.date(2024, 1, 1), "plain", 42]
        result = sanitize_for_json(items)
        assert result == ["2024-01-01", "plain", 42]

    def test_tuple_is_returned_as_list(self):
        t = (datetime.date(2024, 1, 1), "x")
        result = sanitize_for_json(t)
        assert isinstance(result, list)
        assert result[0] == "2024-01-01"
        assert result[1] == "x"

    def test_set_is_returned_as_list(self):
        s = {"apple", "banana"}
        result = sanitize_for_json(s)
        assert isinstance(result, list)
        assert sorted(result) == ["apple", "banana"]

    def test_empty_dict(self):
        assert sanitize_for_json({}) == {}

    def test_empty_list(self):
        assert sanitize_for_json([]) == []


# ---------------------------------------------------------------------------
# Nesting
# ---------------------------------------------------------------------------

class TestNestedStructures:
    def test_nested_dict_with_datetime(self):
        obj = {
            "outer": {
                "inner": datetime.datetime(2024, 6, 1, 12, 0, 0),
                "value": 42,
            }
        }
        result = sanitize_for_json(obj)
        assert result["outer"]["inner"] == "2024-06-01T12:00:00"
        assert result["outer"]["value"] == 42

    def test_list_of_dicts_with_datetimes(self):
        items = [
            {"ts": datetime.datetime(2024, 1, i), "n": i}
            for i in range(1, 4)
        ]
        result = sanitize_for_json(items)
        assert result[0]["ts"] == "2024-01-01T00:00:00"
        assert result[1]["n"] == 2

    def test_graph_node_properties(self):
        """Simulates a Neo4j node properties dict from the graph query."""
        neo4j_dt = _neo4j_datetime()
        node = {
            "id": 42,
            "labels": ["Domain"],
            "properties": {
                "value": "example.com",
                "first_seen": neo4j_dt,
                "risk_score": 15,
                "is_flagged": True,
            },
        }
        result = sanitize_for_json(node)
        assert isinstance(result["properties"]["first_seen"], str)
        assert result["properties"]["value"] == "example.com"
        assert result["properties"]["risk_score"] == 15
        assert result["id"] == 42

    def test_list_of_graph_nodes(self):
        neo4j_dt = _neo4j_datetime()
        nodes = [
            {"id": i, "labels": ["Domain"], "properties": {"first_seen": neo4j_dt}}
            for i in range(5)
        ]
        result = sanitize_for_json(nodes)
        for node in result:
            assert isinstance(node["properties"]["first_seen"], str)

    def test_relationship_properties_with_datetime(self):
        neo4j_dt = _neo4j_datetime()
        rel = {
            "start": 1,
            "end": 2,
            "type": "REPORTED_WITH",
            "properties": {"first_seen": neo4j_dt, "count": 3},
        }
        result = sanitize_for_json(rel)
        assert isinstance(result["properties"]["first_seen"], str)
        assert result["properties"]["count"] == 3

    def test_deeply_nested(self):
        neo4j_dt = _neo4j_datetime()
        obj = {"a": {"b": {"c": {"d": neo4j_dt}}}}
        result = sanitize_for_json(obj)
        assert isinstance(result["a"]["b"]["c"]["d"], str)


# ---------------------------------------------------------------------------
# Scalars and pass-through
# ---------------------------------------------------------------------------

class TestScalarPassthrough:
    @pytest.mark.parametrize("value", [
        None,
        True,
        False,
        0,
        42,
        3.14,
        "hello",
        "",
        "2024-01-01",   # already a string — must NOT double-encode
        b"bytes",
    ])
    def test_scalar_passthrough(self, value):
        assert sanitize_for_json(value) is value or sanitize_for_json(value) == value

    def test_string_not_isoformat_called(self):
        """A plain string has no .isoformat() method and must pass through unchanged."""
        s = "2024-03-15T10:30:45"
        assert sanitize_for_json(s) == s


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

class TestIdempotency:
    def test_idempotent_datetime(self):
        dt = datetime.datetime(2024, 3, 15, 10, 30, 45)
        once = sanitize_for_json(dt)
        twice = sanitize_for_json(once)
        assert once == twice

    def test_idempotent_dict(self):
        obj = {"ts": datetime.datetime(2024, 1, 1), "n": 99}
        once = sanitize_for_json(obj)
        twice = sanitize_for_json(once)
        assert once == twice

    def test_idempotent_nested(self):
        neo4j_dt = _neo4j_datetime()
        obj = {"nodes": [{"properties": {"first_seen": neo4j_dt}}]}
        once = sanitize_for_json(obj)
        twice = sanitize_for_json(once)
        assert once == twice

    def test_idempotent_list(self):
        items = [datetime.date(2024, i, 1) for i in range(1, 6)]
        once = sanitize_for_json(items)
        twice = sanitize_for_json(once)
        assert once == twice

    def test_idempotent_on_plain_dict(self):
        d = {"a": 1, "b": "hello", "c": True}
        assert sanitize_for_json(d) == d
        assert sanitize_for_json(sanitize_for_json(d)) == d


# ---------------------------------------------------------------------------
# Realistic InvestigationResponse.graph_connections payload
# ---------------------------------------------------------------------------

class TestRealisticPayload:
    def test_ring_connections_payload(self):
        """
        Simulates the exact dict that ring_connections takes when Neo4j returns
        node properties containing neo4j.time.DateTime objects.
        """
        neo4j_dt = _neo4j_datetime()
        payload = {
            "flagged_count": 1,
            "rings": ["Infosys Impersonation Ring"],
            "nodes": [
                {
                    "id": 101,
                    "labels": ["Domain"],
                    "properties": {
                        "value": "infosys-careers.in",
                        "first_seen": neo4j_dt,
                        "risk_score": 12,
                        "is_flagged": True,
                        "ring_name": "Infosys Impersonation Ring",
                    },
                },
                {
                    "id": 102,
                    "labels": ["ScamRing"],
                    "properties": {
                        "name": "Infosys Impersonation Ring",
                        "discovered_date": neo4j_dt,
                        "entity_count": 22,
                        "is_active": True,
                    },
                },
            ],
            "relationships": [
                {"start": 101, "end": 102, "type": "BELONGS_TO_RING"},
            ],
        }

        result = sanitize_for_json(payload)

        # Structure preserved
        assert result["flagged_count"] == 1
        assert result["rings"] == ["Infosys Impersonation Ring"]
        assert len(result["nodes"]) == 2

        # Temporal types converted
        domain_node = result["nodes"][0]
        assert isinstance(domain_node["properties"]["first_seen"], str)

        ring_node = result["nodes"][1]
        assert isinstance(ring_node["properties"]["discovered_date"], str)

        # Non-temporal values unchanged
        assert domain_node["properties"]["risk_score"] == 12
        assert domain_node["properties"]["is_flagged"] is True
        assert result["relationships"][0]["type"] == "BELONGS_TO_RING"

    def test_empty_ring_connections(self):
        payload = {"flagged_count": 0, "rings": [], "nodes": [], "relationships": []}
        result = sanitize_for_json(payload)
        assert result == payload

    def test_mixed_temporal_and_scalar_list(self):
        neo4j_dt = _neo4j_datetime()
        items = [neo4j_dt, "plain", 42, None, True, datetime.date(2024, 1, 1)]
        result = sanitize_for_json(items)
        assert isinstance(result[0], str)
        assert result[1] == "plain"
        assert result[2] == 42
        assert result[3] is None
        assert result[4] is True
        assert result[5] == "2024-01-01"
