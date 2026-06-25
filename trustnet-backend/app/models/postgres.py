"""
TrustNet PostgreSQL Models
SQLAlchemy 2.0 async models for all database tables.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.types import JSON, SMALLINT, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    """User accounts - anonymous investigations allowed."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    phone_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="SHA-256 of phone for dedup"
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    investigation_count: Mapped[int] = mapped_column(
        Integer, default=0
    )
    is_trusted_reporter: Mapped[bool] = mapped_column(
        Boolean, default=False
    )

    # Relationships
    investigations: Mapped[List["Investigation"]] = relationship(
        "Investigation", back_populates="user", lazy="selectin"
    )
    community_reports: Mapped[List["CommunityReport"]] = relationship(
        "CommunityReport", back_populates="reporter_user", lazy="selectin"
    )


class Investigation(Base):
    """Core investigation records - the primary data entity."""

    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True
    )
    raw_input: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Original pasted text or transcript"
    )
    input_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="paste|screenshot|pdf|voice"
    )
    entities_json: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict,
        comment="Sarvam-extracted entities"
    )
    trust_score: Mapped[Optional[int]] = mapped_column(
        SMALLINT, nullable=True, comment="Final weighted score 0-100"
    )
    confidence_score: Mapped[Optional[int]] = mapped_column(
        SMALLINT, nullable=True, comment="Data availability confidence 0-100"
    )
    verdict: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="HIGH_RISK|SUSPICIOUS|UNVERIFIED|LIKELY_LEGITIMATE|VERIFIED|INSUFFICIENT_DATA"
    )
    category_scores_json: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict,
        comment="Per-category breakdown"
    )
    evidence_json: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=list,
        comment="Evidence items array"
    )
    hindi_explanation: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Sarvam-generated Hindi report"
    )
    blockchain_tx_hash: Mapped[Optional[str]] = mapped_column(
        String(66), nullable=True, comment="Base tx hash if flagged"
    )
    neo4j_connections_json: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="Graph connection summary"
    )
    processing_ms: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Total investigation time in ms"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    fee_amount_inr: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Extracted fee in INR"
    )
    language_detected: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="investigations"
    )


class Entity(Base):
    """Tracked entities extracted across investigations."""

    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid
    )
    entity_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="domain|email|phone|company|person"
    )
    entity_value: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="Normalized entity value"
    )
    entity_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False,
        comment="SHA-256 of type+value"
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    investigation_count: Mapped[int] = mapped_column(
        Integer, default=1
    )
    aggregate_score: Mapped[Optional[int]] = mapped_column(
        SMALLINT, nullable=True, comment="Running average trust score"
    )
    on_chain: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Written to Base registry"
    )
    ring_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Named scam ring if known"
    )
    last_refreshed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    community_reports: Mapped[List["CommunityReport"]] = relationship(
        "CommunityReport", back_populates="entity", lazy="selectin"
    )


class CommunityReport(Base):
    """User-submitted community scam reports."""

    __tablename__ = "community_reports"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid
    )
    entity_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("entities.id"), nullable=False
    )
    reporter_user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True
    )
    report_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="SCAM|LEGITIMATE|SUSPICIOUS"
    )
    loss_amount_inr: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Reported loss in INR"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Free text description"
    )
    verified_by_admin: Mapped[bool] = mapped_column(
        Boolean, default=False
    )
    reporter_weight: Mapped[float] = mapped_column(
        default=1.0, comment="Reporter trust weight"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    entity: Mapped["Entity"] = relationship(
        "Entity", back_populates="community_reports"
    )
    reporter_user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="community_reports"
    )


class CompanyMaster(Base):
    """MCA company master data - seeded from MCA bulk CSV."""

    __tablename__ = "company_master"

    cin: Mapped[str] = mapped_column(
        String(21), primary_key=True, comment="Corporate Identification Number"
    )
    company_name: Mapped[str] = mapped_column(
        String(500), nullable=False, index=True
    )
    registration_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    authorized_capital: Mapped[Optional[float]] = mapped_column(
        nullable=True
    )
    paid_up_capital: Mapped[Optional[float]] = mapped_column(
        nullable=True
    )
    state: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    directors_json: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StatsCounter(Base):
    """Platform statistics for counter animations."""

    __tablename__ = "stats_counters"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid
    )
    total_investigations: Mapped[int] = mapped_column(
        Integer, default=0
    )
    total_entities_flagged: Mapped[int] = mapped_column(
        Integer, default=0
    )
    total_inr_protected: Mapped[int] = mapped_column(
        Integer, default=0, comment="Estimated INR saved from scams"
    )
    total_on_chain_records: Mapped[int] = mapped_column(
        Integer, default=0
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )