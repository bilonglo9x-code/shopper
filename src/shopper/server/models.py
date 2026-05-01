"""API request/response models for the server."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ── Enums ──

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskType(str, Enum):
    PRODUCT = "product"
    SEARCH = "search"
    SHOP = "shop"
    CATEGORY = "category"


# ── Scraping Task Models ──

class ScrapeRequest(BaseModel):
    """Request to create a scraping task."""
    url: str = Field(..., description="Shopee URL, keyword, or shop username")
    domain: str = Field(default="shopee.vn", description="Shopee domain")
    max_items: int = Field(default=0, description="Max items to fetch (0 = all)")
    include_reviews: bool = Field(default=False, description="Include product reviews")
    max_reviews: int = Field(default=50, description="Max reviews per product")
    sort_by: str = Field(default="relevancy", description="Sort: relevancy, ctime, sales, price")
    generate_affiliate_links: bool = Field(
        default=False,
        description="Auto-generate affiliate links for scraped products",
    )


class TaskResponse(BaseModel):
    """Response for a created/queried task."""
    task_id: str
    status: TaskStatus
    task_type: TaskType | None = None
    url: str
    created_at: datetime
    completed_at: datetime | None = None
    total_items: int = 0
    error: str | None = None


class TaskResult(BaseModel):
    """Full task result including scraped data."""
    task_id: str
    status: TaskStatus
    task_type: TaskType | None = None
    url: str
    created_at: datetime
    completed_at: datetime | None = None
    total_items: int = 0
    error: str | None = None
    data: dict | list | None = None


# ── Affiliate Models ──

class AffiliateConfigRequest(BaseModel):
    """Request to configure affiliate credentials."""
    app_id: str = Field(..., description="Shopee Affiliate app_id")
    secret: str = Field(..., description="Shopee Affiliate secret key")
    region: str = Field(default="vn", description="Shopee region code")


class GenerateLinkRequest(BaseModel):
    """Request to generate affiliate link(s)."""
    urls: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of Shopee URLs to convert to affiliate links",
    )
    sub_ids: list[str] | None = Field(
        default=None,
        max_length=5,
        description="Sub IDs for tracking (up to 5)",
    )


class AffiliateLink(BaseModel):
    """A single affiliate link result."""
    original_url: str
    affiliate_url: str


class GenerateLinkResponse(BaseModel):
    """Response with generated affiliate links."""
    links: list[AffiliateLink]
    total: int


class ProductOfferRequest(BaseModel):
    """Request to search product offers."""
    keyword: str | None = None
    shop_id: int | None = None
    item_id: int | None = None
    sort_type: int = Field(default=2, description="1=relevant, 2=sales, 5=commission")
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class ShopOfferRequest(BaseModel):
    """Request to search shop offers."""
    keyword: str | None = None
    shop_id: int | None = None
    sort_type: int = Field(default=2, description="1=update, 2=commission, 3=popular")
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class ConversionReportRequest(BaseModel):
    """Request for conversion report."""
    start_time: int = Field(..., description="Unix timestamp start")
    end_time: int = Field(..., description="Unix timestamp end")
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=50, ge=1, le=100)
