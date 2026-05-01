"""Shopee link parser - Auto-detect link type and extract IDs."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from shopper.constants import SHOPEE_DOMAINS, LinkType
from shopper.models import ParsedLink

# Product URL patterns:
# https://shopee.vn/Product-Name-i.{shop_id}.{item_id}
# https://shopee.vn/product/{shop_id}/{item_id}
# https://shopee.vn/a-i.{shop_id}.{item_id}
_PRODUCT_PATTERN_1 = re.compile(r"-i\.(\d+)\.(\d+)")
_PRODUCT_PATTERN_2 = re.compile(r"/product/(\d+)/(\d+)")

# Category URL pattern:
# https://shopee.vn/Category-Name-cat.{category_id}
_CATEGORY_PATTERN = re.compile(r"-cat\.(\d+)")

# Shop URL patterns:
# https://shopee.vn/shop/{shop_id}
# https://shopee.vn/{shop_username} (only username, no dashes for category)
_SHOP_ID_PATTERN = re.compile(r"/shop/(\d+)")

# Search URL pattern:
# https://shopee.vn/search?keyword={keyword}
_SEARCH_PATH = "/search"

# Daily discover
_DAILY_DISCOVER_PATH = "/daily_discover"

# Collection
_COLLECTION_PATTERN = re.compile(r"/collection/(\d+)")


def _get_domain(url: str) -> str:
    """Extract the Shopee domain from a URL."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    for domain in SHOPEE_DOMAINS.values():
        if hostname == domain or hostname.endswith("." + domain):
            return domain
    return hostname


def _is_shopee_url(url: str) -> bool:
    """Check if the URL belongs to a Shopee domain."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    return any(
        hostname == domain or hostname.endswith("." + domain)
        for domain in SHOPEE_DOMAINS.values()
    )


def parse_link(url: str) -> ParsedLink:
    """Parse a Shopee URL and detect its type.

    Supports:
    - Product links (multiple formats)
    - Category links
    - Shop links
    - Search/keyword links
    - Daily discover links
    - Collection links

    Args:
        url: The Shopee URL to parse.

    Returns:
        ParsedLink with the detected type and extracted IDs.
    """
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    if not _is_shopee_url(url):
        return ParsedLink(
            link_type=LinkType.UNKNOWN,
            original_url=url,
        )

    parsed = urlparse(url)
    domain = _get_domain(url)
    path = parsed.path
    query_params = parse_qs(parsed.query)

    # Check product URL (pattern 1: -i.shop_id.item_id)
    match = _PRODUCT_PATTERN_1.search(path)
    if match:
        return ParsedLink(
            link_type=LinkType.PRODUCT,
            domain=domain,
            shop_id=int(match.group(1)),
            item_id=int(match.group(2)),
            original_url=url,
        )

    # Check product URL (pattern 2: /product/shop_id/item_id)
    match = _PRODUCT_PATTERN_2.search(path)
    if match:
        return ParsedLink(
            link_type=LinkType.PRODUCT,
            domain=domain,
            shop_id=int(match.group(1)),
            item_id=int(match.group(2)),
            original_url=url,
        )

    # Check search URL
    if path.rstrip("/") == _SEARCH_PATH:
        keyword = query_params.get("keyword", [""])[0]
        return ParsedLink(
            link_type=LinkType.SEARCH,
            domain=domain,
            keyword=keyword,
            original_url=url,
        )

    # Check daily discover
    if _DAILY_DISCOVER_PATH in path:
        return ParsedLink(
            link_type=LinkType.DAILY_DISCOVER,
            domain=domain,
            original_url=url,
        )

    # Check collection
    match = _COLLECTION_PATTERN.search(path)
    if match:
        return ParsedLink(
            link_type=LinkType.COLLECTION,
            domain=domain,
            category_id=int(match.group(1)),
            original_url=url,
        )

    # Check category URL
    match = _CATEGORY_PATTERN.search(path)
    if match:
        return ParsedLink(
            link_type=LinkType.CATEGORY,
            domain=domain,
            category_id=int(match.group(1)),
            original_url=url,
        )

    # Check shop URL by ID
    match = _SHOP_ID_PATTERN.search(path)
    if match:
        return ParsedLink(
            link_type=LinkType.SHOP,
            domain=domain,
            shop_id=int(match.group(1)),
            original_url=url,
        )

    # Check if it's a shop username page
    # Shop pages have a path like /{username} with no special patterns
    path_parts = [p for p in path.split("/") if p]
    if len(path_parts) == 1 and not path_parts[0].startswith("m/"):
        username = path_parts[0]
        # If it doesn't match product or category patterns, assume it's a shop
        if not _PRODUCT_PATTERN_1.search(username) and not _CATEGORY_PATTERN.search(username):
            return ParsedLink(
                link_type=LinkType.SHOP,
                domain=domain,
                keyword=username,  # store username in keyword field
                original_url=url,
            )

    return ParsedLink(
        link_type=LinkType.UNKNOWN,
        domain=domain,
        original_url=url,
    )


def detect_input(text: str) -> ParsedLink:
    """Auto-detect whether input is a URL, keyword, shop name, etc.

    Args:
        text: User input - can be a URL or a keyword.

    Returns:
        ParsedLink with the detected type.
    """
    text = text.strip()

    # If it looks like a URL
    if text.startswith(("http://", "https://")) or any(
        domain in text for domain in SHOPEE_DOMAINS.values()
    ):
        return parse_link(text)

    # Otherwise, treat as keyword search
    return ParsedLink(
        link_type=LinkType.SEARCH,
        keyword=text,
        original_url=text,
    )
