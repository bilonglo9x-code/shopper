"""Tests for the exporter module."""

import json
import tempfile
from pathlib import Path

from shopper.exporters.exporter import export_csv, export_json, export_reviews_csv
from shopper.models import (
    PriceInfo,
    Product,
    RatingSummary,
    Review,
    SearchResult,
    ShopInfo,
)


def _make_product(item_id: int = 1, name: str = "Test") -> Product:
    return Product(
        item_id=item_id,
        shop_id=100,
        name=name,
        description="desc",
        price_info=PriceInfo(price=50000, price_min=50000, price_max=60000, currency="VND"),
        rating_summary=RatingSummary(rating_star=4.5, rating_count=[100]),
        historical_sold=500,
        shop_info=ShopInfo(shop_id=100, name="Shop"),
    )


class TestExportJson:
    def test_export_product(self):
        product = _make_product()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_json(product, Path(tmpdir) / "test.json")
            assert path.exists()
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            assert data["item_id"] == 1
            assert data["name"] == "Test"

    def test_export_search_result(self):
        result = SearchResult(
            keyword="test",
            total_count=2,
            items=[_make_product(1, "A"), _make_product(2, "B")],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_json(result, Path(tmpdir) / "search.json")
            assert path.exists()
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            assert data["keyword"] == "test"
            assert len(data["items"]) == 2


class TestExportCsv:
    def test_export_product_csv(self):
        product = _make_product()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_csv(product, Path(tmpdir) / "test.csv")
            assert path.exists()
            content = path.read_text(encoding="utf-8-sig")
            assert "item_id" in content
            assert "Test" in content

    def test_export_multiple_products(self):
        products = [_make_product(i, f"Product {i}") for i in range(5)]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_csv(products, Path(tmpdir) / "products.csv")
            assert path.exists()
            lines = path.read_text(encoding="utf-8-sig").strip().split("\n")
            assert len(lines) == 6  # header + 5 rows


class TestExportReviewsCsv:
    def test_export_reviews(self):
        product = _make_product()
        product.reviews = [
            Review(
                comment_id=1,
                rating_star=5,
                comment="Great!",
                author_username="user1",
            ),
            Review(
                comment_id=2,
                rating_star=4,
                comment="Good",
                author_username="user2",
            ),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_reviews_csv(product, Path(tmpdir) / "reviews.csv")
            assert path.exists()
            content = path.read_text(encoding="utf-8-sig")
            assert "Great!" in content
            assert "Good" in content
