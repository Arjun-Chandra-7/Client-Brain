import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Column, DateTime, Enum as SAEnum, Float, ForeignKey, String, Table, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def uid() -> str:
    return str(uuid.uuid4())


class FactType(str, Enum):
    CLIENT_PROVIDED = "client_provided"
    OBSERVED = "observed"
    MEASURED = "measured"
    RESEARCHED = "researched"
    INFERRED = "inferred"
    HYPOTHESIS = "hypothesis"


class RecordStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DISPUTED = "disputed"
    STALE = "stale"


class SourceType(str, Enum):
    WEBSITE = "website"
    SOCIAL = "social"
    DOCUMENT = "document"
    CLIENT_INPUT = "client_input"
    ANALYTICS = "analytics"
    EXTERNAL_RESEARCH = "external_research"
    MANUAL = "manual"


fact_sources = Table("fact_sources", Base.metadata,
    Column("fact_id", ForeignKey("facts.id"), primary_key=True),
    Column("source_id", ForeignKey("sources.id"), primary_key=True),
)
insight_facts = Table("insight_facts", Base.metadata,
    Column("insight_id", ForeignKey("insights.id"), primary_key=True),
    Column("fact_id", ForeignKey("facts.id"), primary_key=True),
)
insight_sources = Table("insight_sources", Base.metadata,
    Column("insight_id", ForeignKey("insights.id"), primary_key=True),
    Column("source_id", ForeignKey("sources.id"), primary_key=True),
)


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Client(Base, Timestamped):
    __tablename__ = "clients"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(255), index=True)
    business_name: Mapped[str | None] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[str] = mapped_column(String(30), default="active")
    facts: Mapped[list["Fact"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    sources: Mapped[list["Source"]] = relationship(back_populates="client", cascade="all, delete-orphan")


class Source(Base, Timestamped):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    source_type: Mapped[SourceType] = mapped_column(SAEnum(SourceType))
    url: Mapped[str | None] = mapped_column(String(2048))
    title: Mapped[str | None] = mapped_column(String(500))
    raw_reference: Mapped[str | None] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    client: Mapped[Client] = relationship(back_populates="sources")
    facts: Mapped[list["Fact"]] = relationship(secondary=fact_sources, back_populates="sources")


class Fact(Base, Timestamped):
    __tablename__ = "facts"
    __table_args__ = (UniqueConstraint("client_id", "category", "key", "value_json", "status", name="uq_active_fact_value"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    key: Mapped[str] = mapped_column(String(150), index=True)
    value_json: Mapped[object] = mapped_column(JSON)
    fact_type: Mapped[FactType] = mapped_column(SAEnum(FactType))
    confidence: Mapped[float] = mapped_column(Float)
    status: Mapped[RecordStatus] = mapped_column(SAEnum(RecordStatus), default=RecordStatus.ACTIVE)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    client: Mapped[Client] = relationship(back_populates="facts")
    sources: Mapped[list[Source]] = relationship(secondary=fact_sources, back_populates="facts")


class Insight(Base, Timestamped):
    __tablename__ = "insights"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    statement: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    sample_size: Mapped[int | None] = mapped_column()
    date_range: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[RecordStatus] = mapped_column(SAEnum(RecordStatus), default=RecordStatus.ACTIVE)
    supporting_facts: Mapped[list[Fact]] = relationship(secondary=insight_facts)
    supporting_sources: Mapped[list[Source]] = relationship(secondary=insight_sources)


# Typed extension tables keep high-value concepts normalized while facts remain the evidence ledger.
class Offer(Base, Timestamped):
    __tablename__ = "offers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    name: Mapped[str] = mapped_column(String(255)); description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RecordStatus] = mapped_column(SAEnum(RecordStatus), default=RecordStatus.ACTIVE)


class AudienceSegment(Base, Timestamped):
    __tablename__ = "audience_segments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    name: Mapped[str] = mapped_column(String(255)); description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RecordStatus] = mapped_column(SAEnum(RecordStatus), default=RecordStatus.ACTIVE)


class Competitor(Base, Timestamped):
    __tablename__ = "competitors"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    name: Mapped[str] = mapped_column(String(255)); website: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[RecordStatus] = mapped_column(SAEnum(RecordStatus), default=RecordStatus.ACTIVE)


class Goal(Base, Timestamped):
    __tablename__ = "goals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    statement: Mapped[str] = mapped_column(Text); status: Mapped[RecordStatus] = mapped_column(SAEnum(RecordStatus), default=RecordStatus.ACTIVE)


class Constraint(Base, Timestamped):
    __tablename__ = "constraints"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    statement: Mapped[str] = mapped_column(Text); status: Mapped[RecordStatus] = mapped_column(SAEnum(RecordStatus), default=RecordStatus.ACTIVE)


class SocialAccount(Base, Timestamped):
    __tablename__ = "social_accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    platform: Mapped[str] = mapped_column(String(80)); url: Mapped[str] = mapped_column(String(2048))
    handle: Mapped[str | None] = mapped_column(String(255)); status: Mapped[RecordStatus] = mapped_column(SAEnum(RecordStatus), default=RecordStatus.ACTIVE)
