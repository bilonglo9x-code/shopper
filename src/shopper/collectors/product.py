"""Product data collector - transforms raw API data into structured models."""

from __future__ import annotations

import logging
from typing import Any

from shopper.constants import SHOPEE_IMAGE_BASE, SHOPEE_VIDEO_BASE
from shopper.models import (
    ModelVariant,
    PriceInfo,
    Product,
    ProductAttribute,
    RatingSummary,
    Review,
    ReviewMedia,
    ShopInfo,
    TierVariation,
)

logger = logging.getLogger(__name__)


def _price_from_raw(raw: int | float) -> float:
    """Convert Shopee raw price (x100000) to actual price."""
    if raw >= 100000:
        return raw / 100000
    return float(raw)


def _build_image_url(image_hash: str) -> str:
    """Build full image URL from hash."""
    if image_hash.startswith("http"):
        return image_hash
    return SHOPEE_IMAGE_BASE + image_hash


def _build_video_url(video_hash: str) -> str:
    """Build full video URL from hash."""
    if video_hash.startswith("http"):
        return video_hash
    return SHOPEE_VIDEO_BASE + video_hash


def parse_price_info(data: dict[str, Any]) -> PriceInfo:
    """Parse price information from raw item data."""
    return PriceInfo(
        price=_price_from_raw(data.get("price", 0)),
        price_min=_price_from_raw(data.get("price_min", 0)),
        price_max=_price_from_raw(data.get("price_max", 0)),
        price_before_discount=_price_from_raw(data.get("price_before_discount", 0)),
        price_min_before_discount=_price_from_raw(data.get("price_min_before_discount", 0)),
        price_max_before_discount=_price_from_raw(data.get("price_max_before_discount", 0)),
        discount=data.get("raw_discount", data.get("discount", "")),
        currency=data.get("currency", ""),
    )


def parse_tier_variations(data: list[dict[str, Any]] | None) -> list[TierVariation]:
    """Parse tier variations (product options like size, color)."""
    if not data:
        return []
    variations = []
    for tier in data:
        images = [_build_image_url(img) for img in (tier.get("images") or []) if img]
        variations.append(
            TierVariation(
                name=tier.get("name", ""),
                options=tier.get("options", []),
                images=images,
            )
        )
    return variations


def parse_model_variants(data: list[dict[str, Any]] | None) -> list[ModelVariant]:
    """Parse model variants (SKU-level info)."""
    if not data:
        return []
    models = []
    for model in data:
        models.append(
            ModelVariant(
                name=model.get("name", ""),
                price=_price_from_raw(model.get("price", 0)),
                price_before_discount=_price_from_raw(
                    model.get("price_before_discount", 0)
                ),
                stock=model.get("stock", 0),
                sold=model.get("sold", 0),
                tier_index=model.get("extinfo", {}).get("tier_index", []),
                sku=model.get("sku", ""),
            )
        )
    return models


def parse_attributes(data: list[dict[str, Any]] | None) -> list[ProductAttribute]:
    """Parse product attributes."""
    if not data:
        return []
    return [
        ProductAttribute(name=attr.get("name", ""), value=attr.get("value", ""))
        for attr in data
    ]


def parse_rating_summary(data: dict[str, Any]) -> RatingSummary:
    """Parse rating summary from item data."""
    item_rating = data.get("item_rating", {})
    return RatingSummary(
        rating_star=item_rating.get("rating_star", 0),
        rating_count=item_rating.get("rating_count", []),
        rcount_with_context=item_rating.get("rcount_with_context", 0),
        rcount_with_image=item_rating.get("rcount_with_image", 0),
    )


def parse_shop_info(data: dict[str, Any] | None) -> ShopInfo:
    """Parse shop information."""
    if not data:
        return ShopInfo()
    return ShopInfo(
        shop_id=data.get("shopid", data.get("shop_id", 0)),
        name=data.get("name", data.get("shop_name", "")),
        username=data.get("username", data.get("account", {}).get("username", "")),
        is_official_shop=data.get("is_official_shop", False),
        is_preferred_plus_seller=data.get("is_preferred_plus_seller", False),
        follower_count=data.get("follower_count", 0),
        item_count=data.get("item_count", 0),
        rating_star=data.get("rating_star", 0),
        rating_good=data.get("rating_good", 0),
        rating_normal=data.get("rating_normal", 0),
        rating_bad=data.get("rating_bad", 0),
        response_rate=data.get("response_rate", 0),
        response_time=data.get("response_time", 0),
        shop_location=data.get("shop_location", ""),
        joined_time=data.get("ctime", data.get("joined_time", 0)),
        cover=data.get("cover", ""),
        description=data.get("description", ""),
    )


def parse_review(data: dict[str, Any]) -> Review:
    """Parse a single review/rating."""
    images = [_build_image_url(img) for img in (data.get("images") or []) if img]
    videos = []
    for vid in data.get("videos") or []:
        url = vid.get("url", "")
        if not url and vid.get("cover", ""):
            url = _build_video_url(vid.get("cover", ""))
        videos.append(ReviewMedia(url=url, media_type="video"))

    author = data.get("author_username", "")
    if not author:
        author = data.get("author_portrait", "")

    return Review(
        comment_id=data.get("cmtid", data.get("comment_id", 0)),
        order_id=data.get("orderid", data.get("order_id", 0)),
        rating_star=data.get("rating_star", 0),
        comment=data.get("comment", ""),
        author_username=author,
        author_portrait=data.get("author_portrait", ""),
        model_name=data.get("product_items", [{}])[0].get("model_name", "")
        if data.get("product_items")
        else "",
        images=images,
        videos=videos,
        liked_count=data.get("like_count", data.get("liked_count", 0)),
        ctime=data.get("ctime", 0),
        tags=[tag.get("tag_description", "") for tag in (data.get("tags") or [])],
    )


def parse_product(data: dict[str, Any], domain: str = "") -> Product:
    """Parse full product data from raw API response."""
    # Handle nested data structure from pdp/get_pc
    item = data
    if "item" in data:
        item = data["item"]

    # Images
    images = [_build_image_url(img) for img in (item.get("images") or []) if img]
    if not images and item.get("image"):
        images = [_build_image_url(item["image"])]

    # Video
    video_url = ""
    video_thumbnail = ""
    video_info = item.get("video_info_list", [])
    if video_info:
        vid = video_info[0]
        default_fmt = vid.get("default_format", {})
        video_url = default_fmt.get("url", vid.get("video_url", ""))
        video_thumbnail = vid.get("thumb_url", "")
    elif item.get("video"):
        video_url = _build_video_url(item["video"])

    # Categories
    categories: list[dict[str, str | int]] = []
    for cat in item.get("categories") or []:
        categories.append(
            {"catid": cat.get("catid", 0), "display_name": cat.get("display_name", "")}
        )
    if not categories and item.get("catid"):
        categories = [{"catid": item["catid"], "display_name": ""}]

    # Description
    description = item.get("description", "")
    if not description:
        desc_info = data.get("product_detail", {})
        description = desc_info.get("description", "")

    # Build URL
    item_id = item.get("itemid", item.get("item_id", 0))
    shop_id = item.get("shopid", item.get("shop_id", 0))
    url = ""
    if domain and item_id and shop_id:
        name_slug = item.get("name", "product").replace(" ", "-")[:80]
        url = f"https://{domain}/{name_slug}-i.{shop_id}.{item_id}"

    return Product(
        item_id=item_id,
        shop_id=shop_id,
        name=item.get("name", ""),
        description=description,
        brand=item.get("brand", ""),
        category_id=item.get("catid", 0),
        categories=categories,
        price_info=parse_price_info(item),
        tier_variations=parse_tier_variations(item.get("tier_variations")),
        models=parse_model_variants(item.get("models")),
        attributes=parse_attributes(item.get("attributes")),
        images=images,
        video_url=video_url,
        video_thumbnail=video_thumbnail,
        rating_summary=parse_rating_summary(item),
        historical_sold=item.get("historical_sold", 0),
        sold=item.get("sold", 0),
        stock=item.get("stock", 0),
        liked_count=item.get("liked_count", 0),
        view_count=item.get("view_count", 0),
        condition=item.get("condition", ""),
        status=item.get("status", 0),
        ctime=item.get("ctime", 0),
        shop_info=parse_shop_info(item.get("shop_info") or data.get("shop_info")),
        url=url,
    )


def parse_search_item(item_data: dict[str, Any], domain: str = "") -> Product:
    """Parse a product from search results (less data than full product)."""
    item = item_data.get("item_basic", item_data)
    return parse_product(item, domain=domain)
