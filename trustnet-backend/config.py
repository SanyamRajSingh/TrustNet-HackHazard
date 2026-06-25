"""
TrustNet Configuration
Pydantic Settings for all environment variables and application config.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    APP_NAME: str = "TrustNet"
    DEBUG: bool = False
    ENV: str = "production"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL connection string")
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Neo4j
    NEO4J_URI: str = Field(..., description="Neo4j AuraDB connection URI")
    NEO4J_USERNAME: str = Field(..., description="Neo4j username")
    NEO4J_PASSWORD: str = Field(..., description="Neo4j password")

    # Redis / Upstash
    REDIS_URL: str = Field(..., description="Redis/Upstash connection URL")

    # JWT
    SECRET_KEY: str = Field(..., description="JWT signing secret")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    JWT_REFRESH_EXPIRATION_DAYS: int = 7

    # Sarvam AI
    SARVAM_API_KEY: str = Field(..., description="Sarvam AI API key")
    SARVAM_API_BASE: str = "https://api.sarvam.ai/v1"
    SARVAM_TIMEOUT: int = 4
    SARVAM_MAX_RETRIES: int = 3

    # External APIs
    WHOIS_API_KEY: str = Field(..., description="WhoisXML API key")
    GOOGLE_SAFE_BROWSING_KEY: str = Field(..., description="Google Safe Browsing API key")
    PHISHTANK_API_KEY: str = Field("", description="PhishTank API key (optional)")
    NUMVERIFY_API_KEY: str = Field(..., description="NumVerify API key")
    CLOUDINARY_URL: str = Field("", description="Cloudinary connection string")

    # Blockchain (Base Sepolia)
    BASE_SEPOLIA_RPC: str = Field(..., description="Base Sepolia RPC endpoint")
    BACKEND_WALLET_PRIVATE_KEY: str = Field(..., description="Backend wallet private key")
    TRUSTNET_CONTRACT_ADDRESS: str = Field(..., description="Deployed contract address")
    BLOCKCHAIN_ENABLED: bool = True

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 30
    RATE_LIMIT_PER_HOUR: int = 200

    # Investigation
    INVESTIGATION_TIMEOUT_SECONDS: int = 8
    MAX_INPUT_LENGTH: int = 10000
    MAX_FILE_SIZE_MB: int = 10

    # Confidence scoring
    CONFIDENCE_COMPANY_FOUND: int = 20
    CONFIDENCE_WHOIS: int = 15
    CONFIDENCE_DNS: int = 15
    CONFIDENCE_SARVAM: int = 20
    CONFIDENCE_COMMUNITY: int = 15
    CONFIDENCE_PHONE: int = 10
    CONFIDENCE_EMAIL_AUTH: int = 5

    # Trust engine weights
    WEIGHT_IDENTITY: float = 0.25
    WEIGHT_DOMAIN: float = 0.20
    WEIGHT_COMMUNICATION: float = 0.15
    WEIGHT_CONTENT: float = 0.20
    WEIGHT_COMMUNITY: float = 0.20

    # Trust score thresholds
    THRESHOLD_HIGH_RISK: int = 25
    THRESHOLD_SUSPICIOUS: int = 45
    THRESHOLD_UNVERIFIED: int = 65
    THRESHOLD_LIKELY_LEGITIMATE: int = 80
    CONFIDENCE_THRESHOLD: int = 25

    # Render Workflows
    WORKFLOW_DAILY_REFRESH_HOUR: int = 2
    WORKFLOW_COMMUNITY_RECALC_MINUTES: int = 30
    WORKFLOW_BLOCKCHAIN_SYNC_HOUR: int = 1

    # Frontend URL
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = "http://localhost:5173,https://trustnet.onrender.com"

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