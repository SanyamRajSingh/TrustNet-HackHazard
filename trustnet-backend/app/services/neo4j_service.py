"""
Neo4j Intelligence Engine Service
Graph operations: entity upsert, ring detection, brand impersonation, community detection.
"""

import asyncio
from functools import wraps
from typing import Any, Dict, List, Optional

import structlog
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import ServiceUnavailable, SessionExpired

from config import settings

logger = structlog.get_logger()

def with_retry(max_retries=3, base_delay=1.0):
    """Exponential backoff retry decorator for Neo4j operations."""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(self, *args, **kwargs)
                except (ServiceUnavailable, SessionExpired, Exception) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"neo4j.retry.attempt_{attempt+1}", delay=delay, error=str(e))
                        await asyncio.sleep(delay)
            logger.error("neo4j.retry.failed", retries=max_retries, error=str(last_exception))
            raise last_exception
        return wrapper
    return decorator

# Cypher Queries
UPSERT_DOMAIN = """
MERGE (d:Domain {value: $value})
ON CREATE SET d.first_seen = datetime(), d.investigation_count = 1,
    d.risk_score = $risk_score, d.age_days = $age_days, d.is_flagged = $is_flagged,
    d.registrar = $registrar, d.ring_name = $ring_name
ON MATCH SET d.investigation_count = d.investigation_count + 1,
    d.risk_score = (d.risk_score + $risk_score) / 2
RETURN d
"""

UPSERT_EMAIL = """
MERGE (e:Email {value: $value})
ON CREATE SET e.first_seen = datetime(), e.investigation_count = 1,
    e.domain = $domain, e.provider_type = $provider_type,
    e.is_disposable = $is_disposable, e.risk_score = $risk_score
ON MATCH SET e.investigation_count = e.investigation_count + 1
RETURN e
"""

UPSERT_PHONE = """
MERGE (p:Phone {value: $value})
ON CREATE SET p.first_seen = datetime(), p.investigation_count = 1,
    p.country_code = $country_code, p.line_type = $line_type,
    p.carrier = $carrier, p.risk_score = $risk_score
ON MATCH SET p.investigation_count = p.investigation_count + 1
RETURN p
"""

UPSERT_COMPANY = """
MERGE (c:Company {name: $name})
ON CREATE SET c.first_seen = datetime(), c.investigation_count = 1,
    c.mca_cin = $mca_cin, c.mca_status = $mca_status,
    c.mca_age_years = $mca_age_years, c.risk_score = $risk_score
ON MATCH SET c.investigation_count = c.investigation_count + 1
RETURN c
"""

UPSERT_PERSON = """
MERGE (per:Person {name: $name})
ON CREATE SET per.first_seen = datetime(), per.investigation_count = 1,
    per.is_director = $is_director, per.associated_company_cin = $associated_company_cin
ON MATCH SET per.investigation_count = per.investigation_count + 1
RETURN per
"""

CREATE_RELATIONSHIP = """
MATCH (a {value: $from_value}), (b {value: $to_value})
MERGE (a)-[r:%s]->(b)
ON CREATE SET r.first_seen = datetime(), r.count = 1
ON MATCH SET r.count = r.count + 1
RETURN r
"""

RING_DETECTION = """
MATCH (start {value: $entity_value})
CALL apoc.path.subgraphAll(start, {
    maxLevel: 3,
    limit: 100,
    relationshipFilter: 'SHARES_INFRASTRUCTURE|REPORTED_WITH|USES_EMAIL_DOMAIN|LISTED_PHONE'
}) YIELD nodes, relationships
WITH [n IN nodes WHERE n:ScamRing OR n.is_flagged = true] AS flagged_nodes,
     nodes, relationships
RETURN SIZE(flagged_nodes) AS flagged_count,
       [n IN flagged_nodes | n.ring_name] AS rings,
       [n IN nodes | {id: id(n), labels: labels(n), properties: properties(n)}] AS all_nodes,
       [r IN relationships | {start: id(startNode(r)), end: id(endNode(r)), type: type(r)}] AS all_rels
"""

BRAND_IMPERSONATION = """
MATCH (legit:Domain) WHERE legit.is_legitimate_brand = true
MATCH (suspect:Domain) WHERE suspect.value <> legit.value
WITH legit, suspect,
     apoc.text.levenshteinDistance(legit.value, suspect.value) AS dist
WHERE dist <= 3 AND dist > 0
MERGE (suspect)-[r:IMPERSONATES]->(legit)
SET r.similarity_score = 1.0 - (dist / toFloat(SIZE(legit.value)))
RETURN suspect.value AS suspect_domain, legit.value AS legit_domain,
       dist, r.similarity_score
"""

GET_ENTITY_GRAPH = """
MATCH (start {value: $entity_value})
CALL apoc.path.subgraphAll(start, {
    maxLevel: $max_level,
    limit: 100,
    relationshipFilter: 'SHARES_INFRASTRUCTURE|REPORTED_WITH|USES_EMAIL_DOMAIN|LISTED_PHONE|IMPERSONATES|BELONGS_TO_RING'
}) YIELD nodes, relationships
RETURN [n IN nodes | {
    id: id(n),
    labels: labels(n),
    properties: properties(n)
}] AS nodes,
[r IN relationships | {
    start: id(startNode(r)),
    end: id(endNode(r)),
    type: type(r),
    properties: properties(r)
}] AS relationships
"""

SEED_BRAND_DOMAINS = """
MERGE (d:Domain {value: $value})
SET d.is_legitimate_brand = true, d.brand_name = $brand_name
"""


class Neo4jService:
    """Neo4j graph database service for intelligence operations."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        try:
            self.driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
                max_connection_pool_size=50,
                connection_timeout=15.0,
                keep_alive=True,
            )
            self._connected = True
        except Exception as exc:
            logger.warning(
                "neo4j.init_failed — graph features disabled",
                error=str(exc),
                msg="Neo4j connection failed. All graph calls will return mock/empty data.",
            )
            self.driver = None
            self._connected = False
        self._initialized = True

    async def close(self):
        if self.driver:
            await self.driver.close()

    async def verify_connectivity(self) -> bool:
        if not self._connected or not self.driver:
            return False
        try:
            await self.driver.verify_connectivity()
            return True
        except Exception as e:
            logger.warning("neo4j.connection_check_failed", error=str(e))
            self._connected = False
            return False

    @with_retry()
    async def upsert_entities_from_investigation(
        self,
        entities: Dict[str, Any],
        risk_score: int,
        investigation_id: str,
    ) -> Dict[str, Any]:
        """
        Upsert all entities from an investigation into the graph.
        Create relationships between co-occurring entities.
        """
        results = {"upserted": [], "relationships": [], "rings": []}

        if not self._connected or not self.driver:
            logger.warning(
                "neo4j.upsert_skipped",
                msg="Neo4j unavailable — skipping entity upsert",
            )
            return results

        async with self.driver.session() as session:
            # Upsert domain
            domain = entities.get("website_url")
            if domain:
                domain = domain.lower().replace("https://", "").replace("http://", "").split("/")[0]
                await session.run(UPSERT_DOMAIN, {
                    "value": domain,
                    "risk_score": risk_score,
                    "age_days": None,
                    "is_flagged": risk_score < 25,
                    "registrar": None,
                    "ring_name": None,
                })
                results["upserted"].append({"type": "Domain", "value": domain})

            # Upsert email
            email = entities.get("email")
            if email:
                email_domain = email.split("@")[-1] if "@" in email else ""
                is_disposable = email_domain in [
                    "gmail.com", "yahoo.com", "outlook.com", "rediffmail.com"
                ]
                await session.run(UPSERT_EMAIL, {
                    "value": email.lower(),
                    "domain": email_domain,
                    "provider_type": "personal" if is_disposable else "corporate",
                    "is_disposable": is_disposable,
                    "risk_score": risk_score,
                })
                results["upserted"].append({"type": "Email", "value": email})

                # Create USES_EMAIL_DOMAIN relationship
                if domain and email_domain:
                    await session.run(
                        CREATE_RELATIONSHIP % "USES_EMAIL_DOMAIN",
                        {"from_value": email.lower(), "to_value": email_domain}
                    )

            # Upsert phone
            phone = entities.get("phone_number")
            if phone:
                await session.run(UPSERT_PHONE, {
                    "value": phone,
                    "country_code": "+91",
                    "line_type": "unknown",
                    "carrier": None,
                    "risk_score": risk_score,
                })
                results["upserted"].append({"type": "Phone", "value": phone})

                # Create LISTED_PHONE relationship
                if domain:
                    await session.run(
                        CREATE_RELATIONSHIP % "LISTED_PHONE",
                        {"from_value": domain, "to_value": phone}
                    )

            # Upsert company
            company = entities.get("company_name")
            if company:
                await session.run(UPSERT_COMPANY, {
                    "name": company,
                    "mca_cin": None,
                    "mca_status": None,
                    "mca_age_years": None,
                    "risk_score": risk_score,
                })
                results["upserted"].append({"type": "Company", "value": company})

            # Upsert person (recruiter)
            recruiter = entities.get("recruiter_name")
            if recruiter:
                await session.run(UPSERT_PERSON, {
                    "name": recruiter,
                    "is_director": False,
                    "associated_company_cin": None,
                })
                results["upserted"].append({"type": "Person", "value": recruiter})

            # Create REPORTED_WITH between all co-occurring entities
            entity_values = [e["value"] for e in results["upserted"]]
            for i, ev1 in enumerate(entity_values):
                for ev2 in entity_values[i+1:]:
                    await session.run(
                        CREATE_RELATIONSHIP % "REPORTED_WITH",
                        {"from_value": ev1, "to_value": ev2}
                    )

            # Run brand impersonation detection
            if domain:
                imp_result = await session.run(BRAND_IMPERSONATION)
                imp_records = await imp_result.data()
                if imp_records:
                    results["impersonations"] = imp_records
                    logger.info("neo4j.impersonation_detected", domain=domain, matches=len(imp_records))

            # Check for ring connections
            if domain:
                ring_result = await session.run(RING_DETECTION, {"entity_value": domain})
                ring_data = await ring_result.single()
                if ring_data:
                    results["rings"] = ring_data.get("rings", [])
                    results["flagged_count"] = ring_data.get("flagged_count", 0)

        return results

    @with_retry()
    async def get_entity_graph(
        self, entity_value: str, max_level: int = 3
    ) -> Dict[str, Any]:
        """Get graph data for visualization."""
        if not self._connected or not self.driver:
            logger.warning("neo4j.get_entity_graph.fallback", entity=entity_value)
            return {"nodes": [], "relationships": []}

        try:
          async with self.driver.session() as session:
                result = await session.run(GET_ENTITY_GRAPH, {
                    "entity_value": entity_value,
                    "max_level": max_level,
                })
                record = await result.single()
                if record:
                    return {
                        "nodes": record["nodes"],
                        "relationships": record["relationships"],
                    }
                return {"nodes": [], "relationships": []}
        except Exception as exc:
            logger.warning("neo4j.get_entity_graph.error", entity=entity_value, error=str(exc))
            return {"nodes": [], "relationships": []}

    @with_retry()
    async def detect_ring_connections(self, entity_value: str) -> Dict[str, Any]:
        """Detect scam ring connections for an entity."""
        if not self._connected or not self.driver:
            logger.warning(
                "neo4j.ring_detection.fallback",
                entity=entity_value,
                msg="Neo4j unavailable — returning empty ring data",
            )
            return {"flagged_count": 0, "rings": []}

        try:
            async with self.driver.session() as session:
                result = await session.run(RING_DETECTION, {"entity_value": entity_value})
                record = await result.single()
                if record:
                    return {
                        "flagged_count": record.get("flagged_count", 0),
                        "rings": [r for r in record.get("rings", []) if r],
                    }
                return {"flagged_count": 0, "rings": []}
        except Exception as exc:
            logger.warning("neo4j.ring_detection.error", entity=entity_value, error=str(exc))
            return {"flagged_count": 0, "rings": []}

    async def seed_legitimate_brands(self):
        """Seed known legitimate brand domains for impersonation detection."""
        brands = [
            ("infosys.com", "Infosys"),
            ("tcs.com", "TCS"),
            ("wipro.com", "Wipro"),
            ("hcltech.com", "HCL"),
            ("techmahindra.com", "Tech Mahindra"),
            ("accenture.com", "Accenture"),
            ("cognizant.com", "Cognizant"),
            ("ibm.com", "IBM"),
            ("capgemini.com", "Capgemini"),
            ("google.com", "Google"),
            ("microsoft.com", "Microsoft"),
            ("amazon.com", "Amazon"),
            ("flipkart.com", "Flipkart"),
        ]
        async with self.driver.session() as session:
            for domain, brand in brands:
                await session.run(SEED_BRAND_DOMAINS, {
                    "value": domain,
                    "brand_name": brand,
                })
        logger.info("neo4j.brands_seeded", count=len(brands))

    async def seed_scam_rings(self):
        """Seed initial scam ring data for demo."""
        seed_queries = [
            """
            MERGE (r:ScamRing {name: 'Infosys Impersonation Ring'})
            SET r.discovered_date = date('2023-01-15'), r.entity_count = 22, r.is_active = true
            """,
            """
            MERGE (d:Domain {value: 'infosys-careers.in'})
            SET d.age_days = 45, d.is_flagged = true, d.risk_score = 12,
                d.ring_name = 'Infosys Impersonation Ring', d.registrar = 'Namecheap'
            """,
            """
            MATCH (d:Domain {value:'infosys-careers.in'}), (ring:ScamRing {name:'Infosys Impersonation Ring'})
            MERGE (d)-[:BELONGS_TO_RING {confidence: 0.92}]->(ring)
            """,
            """
            MERGE (d:Domain {value: 'infosys-jobs.co.in'})
            SET d.age_days = 23, d.is_flagged = true, d.risk_score = 8,
                d.ring_name = 'Infosys Impersonation Ring'
            """,
            """
            MATCH (d:Domain {value:'infosys-jobs.co.in'}), (ring:ScamRing {name:'Infosys Impersonation Ring'})
            MERGE (d)-[:BELONGS_TO_RING {confidence: 0.88}]->(ring)
            """,
            # Wipro ring
            """
            MERGE (r:ScamRing {name: 'Wipro Fake Recruitment Ring'})
            SET r.discovered_date = date('2023-06-01'), r.entity_count = 15, r.is_active = true
            """,
            """
            MERGE (d:Domain {value: 'wiprojobs24.com'})
            SET d.age_days = 17, d.is_flagged = true, d.risk_score = 10,
                d.ring_name = 'Wipro Fake Recruitment Ring'
            """,
            """
            MATCH (d:Domain {value:'wiprojobs24.com'}), (ring:ScamRing {name:'Wipro Fake Recruitment Ring'})
            MERGE (d)-[:BELONGS_TO_RING {confidence: 0.90}]->(ring)
            """,
        ]
        async with self.driver.session() as session:
            for query in seed_queries:
                await session.run(query)
        logger.info("neo4j.scam_rings_seeded")

    async def seed_demo_scam_ring(self):
        """Seed 5-10 demo nodes and fake relationships to ensure the graph is never empty."""
        demo_queries = [
            """
            MERGE (r:ScamRing {name: 'HackHazard Demo Scam Ring'})
            SET r.discovered_date = date(), r.entity_count = 6, r.is_active = true
            """,
            """
            MERGE (d1:Domain {value: 'hackhazard-recruitment.com'})
            SET d1.age_days = 2, d1.is_flagged = true, d1.risk_score = 15,
                d1.ring_name = 'HackHazard Demo Scam Ring', d1.registrar = 'GoDaddy'
            """,
            """
            MERGE (d2:Domain {value: 'hackhazard-jobs.in'})
            SET d2.age_days = 5, d2.is_flagged = true, d2.risk_score = 22,
                d2.ring_name = 'HackHazard Demo Scam Ring'
            """,
            """
            MERGE (e:Email {value: 'hr@hackhazard-recruitment.com'})
            SET e.is_disposable = false, e.risk_score = 10, e.domain = 'hackhazard-recruitment.com'
            """,
            """
            MERGE (e2:Email {value: 'scammer123@gmail.com'})
            SET e2.is_disposable = true, e2.risk_score = 5, e2.domain = 'gmail.com'
            """,
            """
            MERGE (p:Phone {value: '+918888888888'})
            SET p.country_code = '+91', p.risk_score = 12
            """,
            """
            MERGE (c:Company {name: 'HackHazard Scam Corp'})
            SET c.mca_status = 'strike off', c.risk_score = 5
            """,
            # Relationships
            """
            MATCH (d1:Domain {value:'hackhazard-recruitment.com'}), (ring:ScamRing {name:'HackHazard Demo Scam Ring'})
            MERGE (d1)-[:BELONGS_TO_RING {confidence: 0.99}]->(ring)
            """,
            """
            MATCH (d2:Domain {value:'hackhazard-jobs.in'}), (ring:ScamRing {name:'HackHazard Demo Scam Ring'})
            MERGE (d2)-[:BELONGS_TO_RING {confidence: 0.95}]->(ring)
            """,
            """
            MATCH (e:Email {value:'hr@hackhazard-recruitment.com'}), (d1:Domain {value:'hackhazard-recruitment.com'})
            MERGE (e)-[:USES_EMAIL_DOMAIN]->(d1)
            """,
            """
            MATCH (e2:Email {value:'scammer123@gmail.com'}), (d2:Domain {value:'hackhazard-jobs.in'})
            MERGE (e2)-[:REPORTED_WITH]->(d2)
            """,
            """
            MATCH (p:Phone {value:'+918888888888'}), (d1:Domain {value:'hackhazard-recruitment.com'})
            MERGE (d1)-[:LISTED_PHONE]->(p)
            """,
            """
            MATCH (c:Company {name:'HackHazard Scam Corp'}), (d2:Domain {value:'hackhazard-jobs.in'})
            MERGE (c)-[:REPORTED_WITH]->(d2)
            """
        ]
        
        if not self._connected or not self.driver:
            logger.error("neo4j.seed_demo_failed.no_connection")
            return
            
        async with self.driver.session() as session:
            for query in demo_queries:
                await session.run(query)
        logger.info("neo4j.demo_scam_ring_seeded", nodes=7, relationships=6)
