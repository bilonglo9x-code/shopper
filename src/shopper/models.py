"""Data models for Shopee scraper."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PriceInfo(BaseModel):
    price: float = 0
    price_min: float = 0
    price_max: float = 0
    price_before_discount: float = 0
    price_min_before_discount: float = 0
    price_max_before_discount: float = 0
    discount: str = ""
    currency: str = ""


class TierVariation(BaseModel):
    name: str = ""
    options: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)


class ModelVariant(BaseModel):
    name: str = ""
    price: float = 0
    price_before_discount: float = 0
    stock: int = 0
    sold: int = 0
    tier_index: list[int] = Field(default_factory=list)
    sku: str = ""


class ProductAttribute(BaseModel):
    name: str = ""
    value: str = ""


class RatingSummary(BaseModel):
    rating_star: float = 0
    rating_count: list[int] = Field(default_factory=list)
    rcount_with_context: int = 0
    rcount_with_image: int = 0


class ShopInfo(BaseModel):
    shop_id: int = 0
    name: str = ""
    username: str = ""
    is_official_shop: bool = False
    is_preferred_plus_seller: bool = False
    follower_count: int = 0
    item_count: int = 0
    rating_star: float = 0
    rating_good: int = 0
    rating_normal: int = 0
    rating_bad: int = 0
    response_rate: int = 0
    response_time: int = 0
    shop_location: str = ""
    joined_time: int = 0
    cover: str = ""
    description: str = ""


class ReviewMedia(BaseModel):
    url: str = ""
    media_type: str = ""


class Review(BaseModel):
    comment_id: int = 0
    order_id: int = 0
    rating_star: int = 0
    comment: str = ""
    author_username: str = ""
    author_portrait: str = ""
    model_name: str = ""
    images: list[str] = Field(default_factory=list)
    videos: list[ReviewMedia] = Field(default_factory=list)
    liked_count: int = 0
    ctime: int = 0
    editable: bool = False
    tags: list[str] = Field(default_factory=list)


class Product(BaseModel):
    item_id: int = 0
    shop_id: int = 0
    name: str = ""
    description: str = ""
    brand: str = ""
    category_id: int = 0
    categories: list[dict[str, str | int]] = Field(default_factory=list)
    price_info: PriceInfo = Field(default_factory=PriceInfo)
    tier_variations: list[TierVariation] = Field(default_factory=list)
    models: list[ModelVariant] = Field(default_factory=list)
    attributes: list[ProductAttribute] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    video_url: str = ""
    video_thumbnail: str = ""
    rating_summary: RatingSummary = Field(default_factory=RatingSummary)
    historical_sold: int = 0
    sold: int = 0
    stock: int = 0
    liked_count: int = 0
    view_count: int = 0
    condition: str = ""
    status: int = 0
    ctime: int = 0
    shop_info: ShopInfo = Field(default_factory=ShopInfo)
    reviews: list[Review] = Field(default_factory=list)
    url: str = ""


class SearchResult(BaseModel):
    keyword: str = ""
    total_count: int = 0
    items: list[Product] = Field(default_factory=list)


class ShopDetail(BaseModel):
    shop_info: ShopInfo = Field(default_factory=ShopInfo)
    items: list[Product] = Field(default_factory=list)
    total_items: int = 0


class CategoryResult(BaseModel):
    category_id: int = 0
    category_name: str = ""
    total_count: int = 0
    items: list[Product] = Field(default_factory=list)


class ParsedLink(BaseModel):
    link_type: str = ""
    domain: str = ""
    shop_id: int | None = None
    item_id: int | None = None
    category_id: int | None = None
    keyword: str | None = None
    original_url: str = ""
