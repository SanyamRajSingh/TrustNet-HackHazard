"""
Seed Neo4j with demo scam ring data.
Usage: python -m scripts.seed_neo4j
"""

import asyncio
import sys
from pathlib import Path

import structlog

# Add project root to Python path so we can import app modules
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.services.neo4j_service import Neo4jService

logger = structlog.get_logger()

async def main():
    logger.info("seed_neo4j.started", msg="Initializing Neo4j Service")
    service = Neo4jService()
    
    # Verify connectivity first
    connected = await service.verify_connectivity()
    if not connected:
        logger.error("seed_neo4j.failed", msg="Could not connect to Neo4j. Is the URI correct in .env?")
        return
        
    logger.info("seed_neo4j.seeding", msg="Connected successfully. Seeding data...")
    
    # Run the seeding functions
    await service.seed_legitimate_brands()
    await service.seed_scam_rings()
    await service.seed_demo_scam_ring()
    
    logger.info("seed_neo4j.completed", msg="Graph seeded successfully.")
    await service.close()

if __name__ == "__main__":
    asyncio.run(main())
