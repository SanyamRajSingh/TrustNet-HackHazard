"""
TrustNet Configuration — Production Hardened
Pydantic Settings for all environment variables and application config.

CRITICAL VARS (app crashes on startup if missing):
  NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, SARVAM_API_KEY, SECRET_KEY

OPTIONAL VARS (set to None if missing — those checks are skipped with WARNING):
  WHOIS_API_KEY, GOOGLE_SAFE_BROWSING_KEY, NUMVERIFY_API_KEY
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "TrustNet"
    DEBUG: bool = False
    ENV: str = "production"
    API_V1_PREFIX: str = "/api/v1"

    # ── Database ─────────────────────────────────────────────────────────────
    # Defaults to SQLite so Render free-tier works without Postgres.
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./trustnet.db",
        description="Database connection string"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ── Neo4j — REQUIRED ─────────────────────────────────────────────────────
    NEO4J_URI: str = Field(
        ...,
        description="Neo4j AuraDB URI (e.g. neo4j+s://xxxx.databases.neo4j.io)"
    )
    NEO4J_USERNAME: str = Field(..., description="Neo4j username")
    NEO4J_PASSWORD: str = Field(..., description="Neo4j password")

    # ── JWT — REQUIRED ────────────────────────────────────────────────────────
    SECRET_KEY: str = Field(
        ...,
        description="JWT signing secret — must be set via SECRET_KEY env var"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    JWT_REFRESH_EXPIRATION_DAYS: int = 7

    # ── Sarvam AI — REQUIRED ─────────────────────────────────────────────────
    SARVAM_API_KEY: str = Field(..., description="Sarvam AI API key (api-subscription-key)")
    SARVAM_API_BASE: str = "https://api.sarvam.ai"
    SARVAM_TIMEOUT: int = 15   # sarvam-30b can take up to 10s for long inputs
    SARVAM_MAX_RETRIES: int = 2

    # ── External APIs — OPTIONAL (None → skip check, log WARNING) ─────────────
    WHOIS_API_KEY: Optional[str] = Field(
        default=None,
        description="WhoisXML API key — OPTIONAL. WHOIS check skipped if not set."
    )
    GOOGLE_SAFE_BROWSING_KEY: Optional[str] = Field(
        default=None,
        description="Google Safe Browsing key — OPTIONAL. URL safety check skipped if not set."
    )
    NUMVERIFY_API_KEY: Optional[str] = Field(
        default=None,
        description="NumVerify API key — OPTIONAL. Phone validation skipped if not set."
    )
    PHISHTANK_API_KEY: Optional[str] = Field(default=None, description="PhishTank API key (optional)")
    CLOUDINARY_URL: Optional[str] = Field(default=None, description="Cloudinary URL (optional)")

    # ── Redis — OPTIONAL ─────────────────────────────────────────────────────
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL — optional, tasks run synchronously without it"
    )

    # ── Blockchain — disabled by default ─────────────────────────────────────
    BLOCKCHAIN_ENABLED: bool = False
    BASE_SEPOLIA_RPC: str = Field(default="https://sepolia.base.org", description="Base Sepolia RPC")
    BACKEND_WALLET_PRIVATE_KEY: Optional[str] = Field(default=None, description="Wallet private key")
    TRUSTNET_CONTRACT_ADDRESS: Optional[str] = Field(default=None, description="Contract address")

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 30
    RATE_LIMIT_PER_HOUR: int = 200

    # ── Investigation ─────────────────────────────────────────────────────────
    INVESTIGATION_TIMEOUT_SECONDS: int = 30  # Increased from 8 to allow sarvam-30b time
    MAX_INPUT_LENGTH: int = 10000
    MAX_FILE_SIZE_MB: int = 10

    # ── Confidence scoring ────────────────────────────────────────────────────
    CONFIDENCE_COMPANY_FOUND: int = 20
    CONFIDENCE_WHOIS: int = 15
    CONFIDENCE_DNS: int = 15
    CONFIDENCE_SARVAM: int = 20
    CONFIDENCE_COMMUNITY: int = 15
    CONFIDENCE_PHONE: int = 10
    CONFIDENCE_EMAIL_AUTH: int = 5

    # ── Trust engine weights ──────────────────────────────────────────────────
    WEIGHT_IDENTITY: float = 0.25
    WEIGHT_DOMAIN: float = 0.20
    WEIGHT_COMMUNICATION: float = 0.15
    WEIGHT_CONTENT: float = 0.20
    WEIGHT_COMMUNITY: float = 0.20

    # ── Trust score thresholds ────────────────────────────────────────────────
    THRESHOLD_HIGH_RISK: int = 25
    THRESHOLD_SUSPICIOUS: int = 45
    THRESHOLD_UNVERIFIED: int = 65
    THRESHOLD_LIKELY_LEGITIMATE: int = 80
    CONFIDENCE_THRESHOLD: int = 25

    # ── Frontend / CORS ───────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = (
        "http://localhost:5173,"
        "http://localhost:3000,"
        "https://trustnet-frontend.onrender.com,"
        "https://trustnet.onrender.com"
    )

    @field_validator("CORS_ORIGINS")
    def parse_cors(cls, v: str) -> str:
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()