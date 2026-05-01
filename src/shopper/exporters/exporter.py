"""Data exporters for saving scraped data to various formats."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from shopper.models import CategoryResult, Product, SearchResult, ShopDetail

logger = logging.getLogger(__name__)


def _to_dict(obj: Any) -> Any:
    """Convert pydantic models to dicts recursively."""
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    if isinstance(obj, list):
        return [_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    return obj


def export_json(
    data: Product | SearchResult | ShopDetail | CategoryResult | list[Product],
    output_path: str | Path,
    indent: int = 2,
) -> Path:
    """Export data to JSON file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    serialized = _to_dict(data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(serialized, f, ensure_ascii=False, indent=indent)

    logger.info("Exported JSON to: %s", path)
    return path


def _flatten_product(product: Product) -> dict[str, Any]:
    """Flatten a Product model for CSV export."""
    row: dict[str, Any] = {
        "item_id": product.item_id,
        "shop_id": product.shop_id,
        "name": product.name,
        "description": product.description[:500] if product.description else "",
        "brand": product.brand,
        "category_id": product.category_id,
        "price": product.price_info.price,
        "price_min": product.price_info.price_min,
        "price_max": product.price_info.price_max,
        "price_before_discount": product.price_info.price_before_discount,
        "discount": product.price_info.discount,
        "currency": product.price_info.currency,
        "rating_star": product.rating_summary.rating_star,
        "rating_count_total": (
            product.rating_summary.rating_count[0]
            if product.rating_summary.rating_count
            else 0
        ),
        "rating_with_context": product.rating_summary.rcount_with_context,
        "rating_with_image": product.rating_summary.rcount_with_image,
        "historical_sold": product.historical_sold,
        "sold": product.sold,
        "stock": product.stock,
        "liked_count": product.liked_count,
        "view_count": product.view_count,
        "images_count": len(product.images),
        "images": " | ".join(product.images[:10]),
        "video_url": product.video_url,
        "variants_count": len(product.models),
        "variants": " | ".join(m.name for m in product.models[:20]),
        "attributes": " | ".join(
            f"{a.name}: {a.value}" for a in product.attributes
        ),
        "reviews_count": len(product.reviews),
        "shop_name": product.shop_info.name,
        "shop_rating": product.shop_info.rating_star,
        "shop_follower_count": product.shop_info.follower_count,
        "is_official_shop": product.shop_info.is_official_shop,
        "ctime": product.ctime,
        "url": product.url,
    }
    return row


def export_csv(
    data: Product | SearchResult | ShopDetail | CategoryResult | list[Product],
    output_path: str | Path,
) -> Path:
    """Export data to CSV file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    products: list[Product] = []
    if isinstance(data, Product):
        products = [data]
    elif isinstance(data, SearchResult):
        products = data.items
    elif isinstance(data, ShopDetail):
        products = data.items
    elif isinstance(data, CategoryResult):
        products = data.items
    elif isinstance(data, list):
        products = data

    if not products:
        logger.warning("No products to export")
        return path

    rows = [_flatten_product(p) for p in products]

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    logger.info("Exported %d products to CSV: %s", len(rows), path)
    return path


def export_reviews_csv(
    product: Product,
    output_path: str | Path,
) -> Path:
    """Export reviews to a separate CSV file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not product.reviews:
        logger.warning("No reviews to export")
        return path

    rows = []
    for review in product.reviews:
        rows.append({
            "comment_id": review.comment_id,
            "rating_star": review.rating_star,
            "comment": review.comment,
            "author_username": review.author_username,
            "model_name": review.model_name,
            "images": " | ".join(review.images),
            "videos": " | ".join(v.url for v in review.videos),
            "liked_count": review.liked_count,
            "ctime": review.ctime,
            "tags": " | ".join(review.tags),
            "product_name": product.name,
            "item_id": product.item_id,
            "shop_id": product.shop_id,
        })

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    logger.info("Exported %d reviews to CSV: %s", len(rows), path)
    return path
