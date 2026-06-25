"""
TrustNet - FastAPI Application Entry Point
"""

import os
import time

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from config import settings

logger = structlog.get_logger()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Real-time job offer fraud investigation platform for Indian job seekers",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://trustnet-frontend-80kg.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Error handling
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
    )


# Health check
@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy", "version": "1.0.0", "environment": settings.ENV}


# Include routers
from app.api.auth import router as auth_router
from app.api.community import router as community_router
from app.api.graph import router as graph_router
from app.api.health import router as health_router
from app.api.investigate import router as investigate_router
from app.api.stats import router as stats_router
from app.api.voice import router as voice_router

app.include_router(investigate_router, prefix=settings.API_V1_PREFIX)
app.include_router(voice_router,       prefix=settings.API_V1_PREFIX)
app.include_router(graph_router,       prefix=settings.API_V1_PREFIX)
app.include_router(community_router,   prefix=settings.API_V1_PREFIX)
app.include_router(stats_router,       prefix=settings.API_V1_PREFIX)
app.include_router(auth_router,        prefix=settings.API_V1_PREFIX)
app.include_router(health_router,      prefix=settings.API_V1_PREFIX)



# Startup / Shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup."""
    logger.info("trustnet.startup")
    try:
        from app.services.neo4j_service import Neo4jService
        neo4j = Neo4jService()
        connected = await neo4j.verify_connectivity()
        if connected:
            logger.info("neo4j.connected")
            # Seed data
            await neo4j.seed_legitimate_brands()
            await neo4j.seed_scam_rings()
        else:
            logger.warning("neo4j.connection_failed")
    except Exception as e:
        logger.error("neo4j.startup_error", error=str(e))


@app.on_event("shutdown")
async def shutdown_event():
    """Close connections on shutdown."""
    logger.info("trustnet.shutdown")
    try:
        from app.services.neo4j_service import Neo4jService
        neo4j = Neo4jService()
        await neo4j.close()
    except Exception:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
