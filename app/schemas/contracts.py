from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, HttpUrl
from app.models.entities import FactType, RecordStatus, SourceType


class ClientCreate(BaseModel):
    name: str
    business_name: str | None = None
    website: str | None = None


class BootstrapRequest(ClientCreate):
    social_links: list[str] = Field(default_factory=list)
    niche: str | None = None
    notes: str | None = None
    documents: list[str] = Field(default_factory=list, description="Pasted document text")
    goals: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class SourceCreate(BaseModel):
    source_type: SourceType
    url: str | None = None
    title: str | None = None
    raw_reference: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FactCreate(BaseModel):
    category: str
    key: str
    value: Any
    fact_type: FactType
    confidence: float = Field(ge=0, le=1)
    source_ids: list[str] = Field(default_factory=list)
    supersede_existing: bool = False


class FactOut(BaseModel):
    id: str; category: str; key: str; value: Any; fact_type: FactType; confidence: float; status: RecordStatus
    source_ids: list[str]; created_at: datetime | None = None; updated_at: datetime | None = None; last_verified_at: datetime | None = None


class InsightOut(BaseModel):
    id: str; statement: str; category: str; confidence: float; status: RecordStatus
    supporting_fact_ids: list[str]; supporting_source_ids: list[str]


class InsightCreate(BaseModel):
    statement: str
    category: str
    confidence: float = Field(ge=0, le=1)
    supporting_fact_ids: list[str] = Field(min_length=1)
    supporting_source_ids: list[str] = Field(default_factory=list)
    sample_size: int | None = Field(default=None, ge=0)
    date_range: str | None = None


class ContextRequest(BaseModel):
    task: str = "general"


class AskRequest(BaseModel):
    question: str


class BrandAnalysisRequest(BaseModel):
    brand_name: str = Field(min_length=2, max_length=255)
    website: str | None = None
    notes: str | None = None
    max_pages: int = Field(default=6, ge=1, le=12)


class QuestionAnswer(BaseModel):
    known_facts: list[FactOut]
    inferences: list[InsightOut]
    unknown: list[str]
    answer: str
