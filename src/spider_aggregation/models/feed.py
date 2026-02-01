"""
Feed data model for RSS/Atom subscription sources.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from sqlalchemy import Boolean, DateTime, Integer, String, Text, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from spider_aggregation.models.entry import EntryModel


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class FeedModel(Base):
    """SQLAlchemy ORM model for Feed."""

    __tablename__ = "feeds"

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("ix_feeds_enabled_last_fetched", "enabled", "last_fetched_at"),
        Index("ix_feeds_enabled_errors", "enabled", "fetch_error_count"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Feed configuration
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fetch_interval_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Error tracking
    fetch_error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_error_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Metadata
    etag: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    last_modified: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationship to Entries
    entries: Mapped[list["EntryModel"]] = relationship(
        "EntryModel",
        back_populates="feed",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<FeedModel(id={self.id}, url='{self.url}', name='{self.name}')>"


# Pydantic models for API


class FeedBase(BaseModel):
    """Base Feed schema."""

    url: str = Field(..., max_length=2048, description="Feed URL")
    name: Optional[str] = Field(None, max_length=500, description="Feed name")
    description: Optional[str] = Field(None, description="Feed description")
    enabled: bool = Field(True, description="Whether feed is enabled")
    fetch_interval_minutes: int = Field(60, ge=10, le=10080, description="Fetch interval in minutes")


class FeedCreate(FeedBase):
    """Schema for creating a new feed."""

    pass


class FeedUpdate(BaseModel):
    """Schema for updating a feed."""

    name: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    enabled: Optional[bool] = None
    fetch_interval_minutes: Optional[int] = Field(None, ge=10, le=10080)


class FeedResponse(FeedBase):
    """Schema for feed response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    last_fetched_at: Optional[datetime] = None
    fetch_error_count: int
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None


class FeedListResponse(BaseModel):
    """Schema for feed list response."""

    model_config = ConfigDict(from_attributes=True)

    feeds: list[FeedResponse]
    total: int
    page: int
    page_size: int
