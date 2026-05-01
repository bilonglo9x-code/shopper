"""Tests for the product data parser."""

from shopper.collectors.product import (
    parse_attributes,
    parse_model_variants,
    parse_price_info,
    parse_product,
    parse_rating_summary,
    parse_review,
    parse_shop_info,
    parse_tier_variations,
)


class TestParsePriceInfo:
    def test_basic_price(self):
        data = {
            "price": 10000000000,
            "price_min": 8000000000,
            "price_max": 15000000000,
            "price_before_discount": 20000000000,
            "currency": "VND",
        }
        result = parse_price_info(data)
        assert result.price == 100000.0
        assert result.price_min == 80000.0
        assert result.price_max == 150000.0
        assert result.price_before_discount == 200000.0
        assert result.currency == "VND"

    def test_zero_price(self):
        result = parse_price_info({})
        assert result.price == 0
        assert result.price_min == 0


class TestParseTierVariations:
    def test_empty(self):
        assert parse_tier_variations(None) == []
        assert parse_tier_variations([]) == []

    def test_with_variations(self):
        data = [
            {"name": "Color", "options": ["Red", "Blue"], "images": ["abc123"]},
            {"name": "Size", "options": ["S", "M", "L"], "images": None},
        ]
        result = parse_tier_variations(data)
        assert len(result) == 2
        assert result[0].name == "Color"
        assert result[0].options == ["Red", "Blue"]
        assert len(result[0].images) == 1
        assert result[1].name == "Size"


class TestParseModelVariants:
    def test_empty(self):
        assert parse_model_variants(None) == []

    def test_with_models(self):
        data = [
            {
                "name": "Red,S",
                "price": 10000000000,
                "price_before_discount": 15000000000,
                "stock": 100,
                "sold": 50,
                "sku": "SKU001",
                "extinfo": {"tier_index": [0, 0]},
            }
        ]
        result = parse_model_variants(data)
        assert len(result) == 1
        assert result[0].name == "Red,S"
        assert result[0].price == 100000.0
        assert result[0].stock == 100
        assert result[0].tier_index == [0, 0]


class TestParseAttributes:
    def test_empty(self):
        assert parse_attributes(None) == []

    def test_with_attrs(self):
        data = [
            {"name": "Brand", "value": "Nike"},
            {"name": "Material", "value": "Cotton"},
        ]
        result = parse_attributes(data)
        assert len(result) == 2
        assert result[0].name == "Brand"
        assert result[0].value == "Nike"


class TestParseRatingSummary:
    def test_basic(self):
        data = {
            "item_rating": {
                "rating_star": 4.8,
                "rating_count": [1000, 5, 10, 20, 65, 900],
                "rcount_with_context": 500,
                "rcount_with_image": 200,
            }
        }
        result = parse_rating_summary(data)
        assert result.rating_star == 4.8
        assert len(result.rating_count) == 6

    def test_missing_rating(self):
        result = parse_rating_summary({})
        assert result.rating_star == 0


class TestParseShopInfo:
    def test_none(self):
        result = parse_shop_info(None)
        assert result.shop_id == 0

    def test_with_data(self):
        data = {
            "shopid": 123,
            "name": "Test Shop",
            "username": "testshop",
            "is_official_shop": True,
            "follower_count": 5000,
            "rating_star": 4.9,
        }
        result = parse_shop_info(data)
        assert result.shop_id == 123
        assert result.name == "Test Shop"
        assert result.is_official_shop is True


class TestParseReview:
    def test_basic_review(self):
        data = {
            "cmtid": 1001,
            "orderid": 2001,
            "rating_star": 5,
            "comment": "Great product!",
            "author_username": "user123",
            "author_portrait": "portrait_hash",
            "images": ["img1", "img2"],
            "videos": [],
            "like_count": 10,
            "ctime": 1700000000,
            "product_items": [{"model_name": "Red,L"}],
            "tags": [{"tag_description": "Good quality"}],
        }
        result = parse_review(data)
        assert result.comment_id == 1001
        assert result.rating_star == 5
        assert result.comment == "Great product!"
        assert len(result.images) == 2
        assert result.model_name == "Red,L"
        assert result.tags == ["Good quality"]


class TestParseProduct:
    def test_basic_product(self):
        data = {
            "itemid": 123,
            "shopid": 456,
            "name": "Test Product",
            "description": "A test product",
            "brand": "TestBrand",
            "price": 5000000000,
            "price_min": 5000000000,
            "price_max": 10000000000,
            "images": ["hash1", "hash2"],
            "item_rating": {"rating_star": 4.5, "rating_count": [100]},
            "historical_sold": 500,
            "stock": 200,
            "ctime": 1700000000,
        }
        result = parse_product(data, domain="shopee.vn")
        assert result.item_id == 123
        assert result.shop_id == 456
        assert result.name == "Test Product"
        assert len(result.images) == 2
        assert result.historical_sold == 500

    def test_nested_item_data(self):
        data = {
            "item": {
                "itemid": 789,
                "shopid": 101,
                "name": "Nested Product",
            }
        }
        result = parse_product(data)
        assert result.item_id == 789
        assert result.name == "Nested Product"
