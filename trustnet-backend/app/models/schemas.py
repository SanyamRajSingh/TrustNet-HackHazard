"""
TrustNet Pydantic Schemas
Request/Response models for all API endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============== AUTH ==============

class UserRegisterRequest(BaseModel):
    email: str = Field(..., description="Login email")
    password: str = Field(..., min_length=8, max_length=128)
    phone: Optional[str] = Field(None, description="Optional phone number")


class UserLoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(86400, description="Token expiration in seconds")


class UserResponse(BaseModel):
    id: str
    email: str
    is_trusted_reporter: bool
    investigation_count: int
    created_at: datetime


# ============== ENTITY EXTRACTION ==============

class ExtractedEntities(BaseModel):
    company_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    website_url: Optional[str] = None
    recruiter_name: Optional[str] = None
    job_title: Optional[str] = None
    location: Optional[str] = None
    salary_mentioned: Optional[int] = None
    fee_amount: Optional[int] = None
    urgency_indicators: bool = False
    personal_email_for_corp_contact: bool = False
    language_detected: str = "english"
    red_flags: List[str] = Field(default_factory=list)



# ============== INVESTIGATION ==============

class InvestigationRequest(BaseModel):
    raw_input: str = Field(..., max_length=10000, description="Raw text to investigate")
    input_type: str = Field("paste", pattern=r"^(paste|screenshot|pdf|voice)$")
    source_language: Optional[str] = Field(None, description="Optional language hint")


class CategoryBreakdown(BaseModel):
    identity_company: Dict[str, Any]
    domain_infrastructure: Dict[str, Any]
    communication_channel: Dict[str, Any]
    content_red_flags: Dict[str, Any]
    community_intelligence: Dict[str, Any]


class EvidenceItem(BaseModel):
    category: str
    finding: str
    severity: str  # critical|warning|info|positive
    details: Optional[str] = None


class InvestigationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    trust_score: int = Field(..., ge=0, le=100)
    confidence_score: int = Field(..., ge=0, le=100)
    verdict: str  # HIGH_RISK|SUSPICIOUS|UNVERIFIED|LIKELY_LEGITIMATE|VERIFIED|INSUFFICIENT_DATA
    verdict_label: str
    verdict_color: str
    entities: ExtractedEntities
    category_scores: Dict[str, Any]
    evidence: List[EvidenceItem]
    hindi_explanation: Optional[str] = None
    graph_connections: Optional[Dict[str, Any]] = None
    blockchain_tx_hash: Optional[str] = None
    processing_ms: int
    created_at: datetime


class InvestigationDetail(InvestigationResponse):
    raw_input: str
    input_type: str


# ============== VOICE ==============

class VoiceInvestigationRequest(BaseModel):
    audio_base64: str = Field(..., description="Base64-encoded audio data")
    mime_type: str = Field("audio/wav", description="Audio MIME type")


class VoiceInvestigationResponse(InvestigationResponse):
    transcript: str


# ============== GRAPH ==============

class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    properties: Dict[str, Any]
    risk_score: Optional[int] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str
    properties: Dict[str, Any]


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    flagged_count: int
    rings: List[str]


# ============== ENTITY ==============

class EntityResponse(BaseModel):
    id: str
    entity_type: str
    entity_value: str
    entity_hash: str
    first_seen_at: datetime
    investigation_count: int
    aggregate_score: Optional[int]
    on_chain: bool
    ring_name: Optional[str]


# ============== COMMUNITY REPORT ==============

class CommunityReportRequest(BaseModel):
    entity_id: str
    report_type: str = Field(..., pattern=r"^(SCAM|LEGITIMATE|SUSPICIOUS)$")
    loss_amount_inr: Optional[int] = None
    description: Optional[str] = None


class CommunityReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_id: str
    report_type: str
    loss_amount_inr: Optional[int]
    description: Optional[str]
    verified_by_admin: bool
    reporter_weight: float
    created_at: datetime


# ============== STATS ==============

class StatsResponse(BaseModel):
    total_investigations: int
    total_entities_flagged: int
    total_inr_protected: int
    total_on_chain_records: int
    high_risk_percentage: float
    avg_processing_ms: int


# ============== BLOCKCHAIN ==============

class BlockchainCheckResponse(BaseModel):
    entity_hash: str
    entity_type: int
    trust_score: int
    report_count: int
    first_flagged_at: Optional[int]
    last_updated_at: Optional[int]
    is_active: bool


# ============== ERROR ==============

class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None