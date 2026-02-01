"""
Entry data model for RSS/Atom feed entries.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from spider_aggregation.models.feed import Base


class EntryModel(Base):
    """SQLAlchemy ORM model for Entry."""

    __tablename__ = "entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feed_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("feeds.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Basic entry fields
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    link: Mapped[str] = mapped_column(String(2048), nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Content fields
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Deduplication fields
    title_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    link_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # Additional metadata
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string of tags
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    reading_time_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<EntryModel(id={self.id}, title='{self.title}', link='{self.link}')>"


# Pydantic models for API


class EntryBase(BaseModel):
    """Base Entry schema."""

    title: str = Field(..., max_length=1000, description="Entry title")
    link: str = Field(..., max_length=2048, description="Entry link")
    author: Optional[str] = Field(None, max_length=500, description="Entry author")
    summary: Optional[str] = Field(None, description="Entry summary")
    content: Optional[str] = Field(None, description="Entry full content")
    published_at: Optional[datetime] = Field(None, description="Publication date")
    tags: Optional[list[str]] = Field(None, description="Entry tags")
    language: Optional[str] = Field(None, max_length=10, description="Content language")
    reading_time_seconds: Optional[int] = Field(None, ge=0, description="Estimated reading time")


class EntryCreate(EntryBase):
    """Schema for creating a new entry."""

    feed_id: int = Field(..., description="Feed ID")
    title_hash: str = Field(..., max_length=64, description="Hash of title for deduplication")
    link_hash: str = Field(..., max_length=64, description="Hash of link for deduplication")
    content_hash: Optional[str] = Field(None, max_length=64, description="Hash of content for deduplication")


class EntryUpdate(BaseModel):
    """Schema for updating an entry."""

    title: Optional[str] = Field(None, max_length=1000)
    summary: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[list[str]] = None
    language: Optional[str] = Field(None, max_length=10)
    reading_time_seconds: Optional[int] = Field(None, ge=0)


class EntryResponse(EntryBase):
    """Schema for entry response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    feed_id: int
    fetched_at: datetime
    title_hash: str
    link_hash: str
    content_hash: Optional[str] = None


class EntryListResponse(BaseModel):
    """Schema for entry list response."""

    model_config = ConfigDict(from_attributes=True)

    entries: list[EntryResponse]
    total: int
    page: int
    page_size: int


# Filter rule model


class FilterRuleModel(Base):
    """SQLAlchemy ORM model for FilterRule."""

    __tablename__ = "filter_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Rule configuration
    rule_type: Mapped[str] = mapped_column(
        String(50), nullable=False  # keyword, regex, tag, language
    )
    match_type: Mapped[str] = mapped_column(
        String(50), nullable=False  # include, exclude
    )
    pattern: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<FilterRuleModel(id={self.id}, name='{self.name}', type='{self.rule_type}')>"
