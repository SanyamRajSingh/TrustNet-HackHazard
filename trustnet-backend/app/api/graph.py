"""
Graph Router
GET /api/v1/graph/{entity} - Get graph connections for entity
"""

from fastapi import APIRouter, HTTPException

from app.models.schemas import GraphResponse
from app.services.neo4j_service import Neo4jService

router = APIRouter()
neo4j_service = Neo4jService()


@router.get(
    "/graph/{entity_value}",
    response_model=GraphResponse,
    summary="Get graph connections for entity",
    description="Query Neo4j graph for connections up to 3 hops from the given entity.",
)
async def get_entity_graph(entity_value: str) -> GraphResponse:
    """Get graph visualization data for an entity."""
    try:
        graph_data = await neo4j_service.get_entity_graph(entity_value, max_level=3)

        from app.models.schemas import GraphEdge, GraphNode

        nodes = []
        edges = []
        flagged_count = 0
        rings = set()

        for n in graph_data.get("nodes", []):
            props = n.get("properties", {})
            labels = n.get("labels", [])
            label = labels[0] if labels else "Unknown"
            risk = props.get("risk_score")
            if props.get("is_flagged") or label == "ScamRing":
                flagged_count += 1
            ring = props.get("ring_name")
            if ring:
                rings.add(ring)

            nodes.append(GraphNode(
                id=str(n.get("id", "")),
                label=props.get("value", props.get("name", "Unknown")),
                type=label,
                properties=props,
                risk_score=risk,
            ))

        for e in graph_data.get("relationships", []):
            edges.append(GraphEdge(
                source=str(e.get("start", "")),
                target=str(e.get("end", "")),
                type=e.get("type", "UNKNOWN"),
                properties=e.get("properties", {}),
            ))

        return GraphResponse(
            nodes=nodes,
            edges=edges,
            flagged_count=flagged_count,
            rings=list(rings),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Graph query failed: {str(exc)}")
