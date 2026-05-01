"""Tests for the link parser module."""

from shopper.constants import LinkType
from shopper.parsers.link_parser import detect_input, parse_link


class TestParseLink:
    def test_product_url_standard(self):
        url = "https://shopee.vn/Product-Name-i.123456.789012"
        result = parse_link(url)
        assert result.link_type == LinkType.PRODUCT
        assert result.shop_id == 123456
        assert result.item_id == 789012
        assert result.domain == "shopee.vn"

    def test_product_url_short(self):
        url = "https://shopee.vn/product/123456/789012"
        result = parse_link(url)
        assert result.link_type == LinkType.PRODUCT
        assert result.shop_id == 123456
        assert result.item_id == 789012

    def test_product_url_a_format(self):
        url = "https://shopee.vn/a-i.123456.789012"
        result = parse_link(url)
        assert result.link_type == LinkType.PRODUCT
        assert result.shop_id == 123456
        assert result.item_id == 789012

    def test_category_url(self):
        url = "https://shopee.vn/Thoi-Trang-Nam-cat.11035567"
        result = parse_link(url)
        assert result.link_type == LinkType.CATEGORY
        assert result.category_id == 11035567

    def test_shop_url_by_id(self):
        url = "https://shopee.vn/shop/123456"
        result = parse_link(url)
        assert result.link_type == LinkType.SHOP
        assert result.shop_id == 123456

    def test_shop_url_by_username(self):
        url = "https://shopee.vn/myshopname"
        result = parse_link(url)
        assert result.link_type == LinkType.SHOP
        assert result.keyword == "myshopname"

    def test_search_url(self):
        url = "https://shopee.vn/search?keyword=ao+thun+nam"
        result = parse_link(url)
        assert result.link_type == LinkType.SEARCH
        assert result.keyword == "ao thun nam"

    def test_different_domain(self):
        url = "https://shopee.sg/Product-i.111.222"
        result = parse_link(url)
        assert result.link_type == LinkType.PRODUCT
        assert result.domain == "shopee.sg"
        assert result.shop_id == 111
        assert result.item_id == 222

    def test_non_shopee_url(self):
        url = "https://example.com/something"
        result = parse_link(url)
        assert result.link_type == LinkType.UNKNOWN

    def test_url_without_scheme(self):
        url = "shopee.vn/Product-i.100.200"
        result = parse_link(url)
        assert result.link_type == LinkType.PRODUCT
        assert result.shop_id == 100
        assert result.item_id == 200

    def test_product_url_with_query_params(self):
        url = "https://shopee.vn/Product-Name-i.123.456?sp_atk=abc&xptdk=def"
        result = parse_link(url)
        assert result.link_type == LinkType.PRODUCT
        assert result.shop_id == 123
        assert result.item_id == 456

    def test_indonesia_domain(self):
        url = "https://shopee.co.id/product/111/222"
        result = parse_link(url)
        assert result.link_type == LinkType.PRODUCT
        assert result.domain == "shopee.co.id"

    def test_taiwan_domain(self):
        url = "https://shopee.tw/something-i.999.888"
        result = parse_link(url)
        assert result.link_type == LinkType.PRODUCT
        assert result.domain == "shopee.tw"


class TestDetectInput:
    def test_keyword_input(self):
        result = detect_input("áo thun nam")
        assert result.link_type == LinkType.SEARCH
        assert result.keyword == "áo thun nam"

    def test_url_input(self):
        result = detect_input("https://shopee.vn/Product-i.1.2")
        assert result.link_type == LinkType.PRODUCT

    def test_domain_without_scheme(self):
        result = detect_input("shopee.vn/search?keyword=test")
        assert result.link_type == LinkType.SEARCH

    def test_plain_text_keyword(self):
        result = detect_input("iphone 15 pro max")
        assert result.link_type == LinkType.SEARCH
        assert result.keyword == "iphone 15 pro max"
