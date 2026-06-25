"""
app/core/serialization.py
=========================
Production-grade recursive serialization utility for TrustNet.

Why this module exists
----------------------
FastAPI uses Pydantic v2 for response serialization. Pydantic v2 does not
know how to serialize neo4j temporal types (neo4j.time.DateTime,
neo4j.time.Date, neo4j.time.Time, neo4j.time.LocalDateTime,
neo4j.time.LocalTime) because they are not standard Python types.

When Neo4j Cypher uses ``datetime()`` / ``date()`` inside CREATE/MERGE
statements those values are returned as neo4j temporal objects in node
``properties`` dicts. Those dicts propagate through graph queries and end
up inside InvestigationResponse.graph_connections which is typed
``Optional[Dict[str, Any]]``.  Pydantic then raises::

    PydanticSerializationError: Unable to serialize unknown type:
    <class 'neo4j.time.DateTime'>

This produces an HTTP 500 which the browser mis-reports as a CORS error.

Design decisions
----------------
* **Single responsibility** – this module does nothing but sanitize.
* **Idempotent** – ``sanitize_for_json(sanitize_for_json(x))`` is always
  equal to ``sanitize_for_json(x)``.
* **No data loss** – all keys, structure, and non-temporal values are
  preserved exactly.
* **Future-proof** – detects any object exposing ``.isoformat()`` so
  neo4j temporal types added in future neo4j driver versions are handled
  automatically.
* **Safe** – if serialization of any individual value raises, the raw
  repr string is used rather than crashing the whole response.
"""

import datetime
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try importing all known neo4j temporal types.  If the driver is not
# installed (e.g. in test environments) fall back to unreachable stubs.
# ---------------------------------------------------------------------------
try:
    from neo4j.time import (
        Date as _Neo4jDate,
        DateTime as _Neo4jDateTime,
        Duration as _Neo4jDuration,
        LocalDateTime as _Neo4jLocalDateTime,
        LocalTime as _Neo4jLocalTime,
        Time as _Neo4jTime,
    )

    _NEO4J_TEMPORAL_TYPES = (
        _Neo4jDateTime,
        _Neo4jDate,
        _Neo4jTime,
        _Neo4jLocalDateTime,
        _Neo4jLocalTime,
    )
    _NEO4J_DURATION_TYPE = _Neo4jDuration
except ImportError:  # pragma: no cover – driver not installed in test env
    _NEO4J_TEMPORAL_TYPES = ()
    _Neo4jDuration = None
    _NEO4J_DURATION_TYPE = type(None)  # unmatchable sentinel

_PYTHON_TEMPORAL_TYPES = (
    datetime.datetime,
    datetime.date,
    datetime.time,
)


def sanitize_for_json(obj: Any, _field_path: str = "<root>") -> Any:
    """
    Recursively walk *obj* and convert every temporal value to an ISO-8601
    string so the result is safe to pass to Pydantic v2 / ``json.dumps``.

    Supported container types
    ~~~~~~~~~~~~~~~~~~~~~~~~~
    * ``dict`` → values are sanitized, keys are left as-is
    * ``list`` → each element is sanitized
    * ``tuple`` → each element is sanitized, returned as list (JSON-safe)
    * ``set`` → each element is sanitized, returned as sorted list

    Supported temporal types
    ~~~~~~~~~~~~~~~~~~~~~~~~
    * ``datetime.datetime``, ``datetime.date``, ``datetime.time``
    * ``neo4j.time.DateTime``, ``neo4j.time.Date``, ``neo4j.time.Time``
    * ``neo4j.time.LocalDateTime``, ``neo4j.time.LocalTime``
    * Any future object that exposes a callable ``.isoformat()`` method

    neo4j.time.Duration
    ~~~~~~~~~~~~~~~~~~~
    Converted to its ISO 8601 string representation via ``str()``.

    Idempotency
    ~~~~~~~~~~~
    Once a temporal value has been converted to a string it is a plain
    ``str`` instance.  On a second call ``sanitize_for_json(str_value)``
    simply returns the same string unchanged, so the function is idempotent.

    Parameters
    ----------
    obj:
        The value to sanitize.  May be any Python object.
    _field_path:
        Internal dot-path string used only for logging when an unexpected
        type is encountered.  Callers should not pass this argument.

    Returns
    -------
    Any
        A JSON-serializable representation of *obj*.
    """
    # ── Containers ─────────────────────────────────────────────────────────
    if isinstance(obj, dict):
        return {
            k: sanitize_for_json(v, _field_path=f"{_field_path}.{k}")
            for k, v in obj.items()
        }

    if isinstance(obj, (list, tuple)):
        return [
            sanitize_for_json(item, _field_path=f"{_field_path}[{i}]")
            for i, item in enumerate(obj)
        ]

    if isinstance(obj, set):
        # Sets are not JSON-serializable; convert to a sorted list so the
        # output is deterministic (important for idempotency tests).
        try:
            sorted_items = sorted(obj)
        except TypeError:
            sorted_items = list(obj)
        return [
            sanitize_for_json(item, _field_path=f"{_field_path}{{set}}")
            for item in sorted_items
        ]

    # ── Neo4j Duration (no isoformat; str() gives ISO 8601 form) ───────────
    if _NEO4J_DURATION_TYPE is not type(None) and isinstance(obj, _NEO4J_DURATION_TYPE):
        return str(obj)

    # ── All temporal types with .isoformat() ───────────────────────────────
    # This single branch covers:
    #   • datetime.datetime, datetime.date, datetime.time
    #   • neo4j.time.DateTime, Date, Time, LocalDateTime, LocalTime
    #   • Any third-party temporal object that follows the same convention
    if hasattr(obj, "isoformat") and callable(obj.isoformat):
        try:
            return obj.isoformat()
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "serialization.isoformat_failed",
                extra={
                    "field_path": _field_path,
                    "obj_type": type(obj).__qualname__,
                    "error": str(exc),
                },
            )
            return repr(obj)

    # ── Scalars and everything else pass through unchanged ─────────────────
    return obj
