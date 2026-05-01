"""Main scraper - orchestrates API calls and data collection."""

from __future__ import annotations

import logging
from typing import Any

from shopper.api.client import ShopeeClient
from shopper.collectors.product import (
    parse_product,
    parse_review,
    parse_search_item,
    parse_shop_info,
)
from shopper.constants import DEFAULT_DOMAIN, LinkType, RatingFilter, SortBy, SortOrder
from shopper.models import (
    CategoryResult,
    ParsedLink,
    Product,
    SearchResult,
    ShopDetail,
)
from shopper.parsers.link_parser import detect_input, parse_link

logger = logging.getLogger(__name__)


class ShopeeScraper:
    """High-level scraper that handles URL detection and data collection."""

    def __init__(
        self,
        domain: str = DEFAULT_DOMAIN,
        cookies: dict[str, str] | None = None,
        proxy: str | None = None,
        request_delay: float = 1.0,
    ):
        self.domain = domain
        self._cookies = cookies
        self._proxy = proxy
        self._request_delay = request_delay
        self.client = ShopeeClient(
            domain=domain,
            cookies=cookies,
            proxy=proxy,
            request_delay=request_delay,
        )

    async def close(self):
        await self.client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: object):
        await self.close()

    # ── Auto-detect and scrape ──

    async def scrape(
        self,
        url_or_keyword: str,
        max_items: int = 0,
        include_reviews: bool = False,
        max_reviews: int = 50,
        sort_by: SortBy = SortBy.RELEVANCY,
    ) -> Product | SearchResult | ShopDetail | CategoryResult:
        """Auto-detect input type and scrape accordingly."""
        parsed = detect_input(url_or_keyword)
        logger.info("Detected link type: %s", parsed.link_type)

        domain = parsed.domain or self.domain
        if domain != self.domain:
            await self.client.close()
            self.client = ShopeeClient(
                domain=domain,
                cookies=self._cookies,
                proxy=self._proxy,
                request_delay=self._request_delay,
            )
            self.domain = domain

        if parsed.link_type == LinkType.PRODUCT:
            assert parsed.shop_id is not None and parsed.item_id is not None
            return await self.scrape_product(
                parsed.shop_id,
                parsed.item_id,
                include_reviews=include_reviews,
                max_reviews=max_reviews,
            )
        elif parsed.link_type == LinkType.SEARCH:
            keyword = parsed.keyword or ""
            return await self.scrape_search(
                keyword,
                max_items=max_items,
                sort_by=sort_by,
                include_reviews=include_reviews,
                max_reviews=max_reviews,
            )
        elif parsed.link_type == LinkType.SHOP:
            if parsed.shop_id:
                return await self.scrape_shop(
                    parsed.shop_id,
                    max_items=max_items,
                    include_reviews=include_reviews,
                    max_reviews=max_reviews,
                )
            elif parsed.keyword:
                return await self.scrape_shop_by_username(
                    parsed.keyword,
                    max_items=max_items,
                    include_reviews=include_reviews,
                    max_reviews=max_reviews,
                )
            else:
                raise ValueError("Shop link without shop_id or username")
        elif parsed.link_type == LinkType.CATEGORY:
            assert parsed.category_id is not None
            return await self.scrape_category(
                parsed.category_id,
                max_items=max_items,
                sort_by=sort_by,
                include_reviews=include_reviews,
                max_reviews=max_reviews,
            )
        else:
            raise ValueError(f"Cannot scrape link type: {parsed.link_type}")

    # ── Product scraping ──

    async def scrape_product(
        self,
        shop_id: int,
        item_id: int,
        include_reviews: bool = False,
        max_reviews: int = 50,
    ) -> Product:
        """Scrape full product details."""
        logger.info("Scraping product: shop_id=%d, item_id=%d", shop_id, item_id)

        raw_data = await self.client.get_item(shop_id, item_id)
        product = parse_product(raw_data, domain=self.domain)

        # Try to get more detail from pdp endpoint
        try:
            detail_data = await self.client.get_item_detail(shop_id, item_id)
            if detail_data:
                detail_product = parse_product(detail_data, domain=self.domain)
                # Merge additional info
                if not product.description and detail_product.description:
                    product.description = detail_product.description
                if not product.video_url and detail_product.video_url:
                    product.video_url = detail_product.video_url
                if not product.models and detail_product.models:
                    product.models = detail_product.models
        except Exception as e:
            logger.debug("Could not fetch pdp detail: %s", e)

        # Fetch shop info if not included
        if product.shop_info.shop_id == 0:
            try:
                shop_data = await self.client.get_shop_info(shop_id)
                product.shop_info = parse_shop_info(shop_data)
            except Exception as e:
                logger.debug("Could not fetch shop info: %s", e)

        # Fetch reviews
        if include_reviews:
            product.reviews = await self._fetch_reviews(shop_id, item_id, max_reviews)

        return product

    async def _fetch_reviews(
        self,
        shop_id: int,
        item_id: int,
        max_reviews: int = 50,
        rating_filter: RatingFilter = RatingFilter.ALL,
    ) -> list[Any]:
        """Fetch reviews for a product."""
        logger.info("Fetching reviews for item %d...", item_id)
        try:
            raw_ratings = await self.client.get_all_ratings(
                shop_id, item_id, max_reviews=max_reviews, rating_filter=rating_filter
            )
            return [parse_review(r) for r in raw_ratings]
        except Exception as e:
            logger.warning("Could not fetch reviews: %s", e)
            return []

    # ── Search scraping ──

    async def scrape_search(
        self,
        keyword: str,
        max_items: int = 0,
        sort_by: SortBy = SortBy.RELEVANCY,
        order: SortOrder = SortOrder.DESC,
        include_reviews: bool = False,
        max_reviews: int = 10,
    ) -> SearchResult:
        """Search for products by keyword."""
        logger.info("Searching for: %s", keyword)
        data = await self.client.search_all(
            keyword, max_items=max_items, sort_by=sort_by, order=order
        )

        items = [parse_search_item(item, domain=self.domain) for item in data.get("items", [])]

        # Optionally enrich with full details
        if include_reviews:
            for i, product in enumerate(items):
                if product.shop_id and product.item_id:
                    logger.info("Enriching product %d/%d", i + 1, len(items))
                    try:
                        full = await self.scrape_product(
                            product.shop_id,
                            product.item_id,
                            include_reviews=True,
                            max_reviews=max_reviews,
                        )
                        items[i] = full
                    except Exception as e:
                        logger.warning("Could not enrich product: %s", e)

        return SearchResult(
            keyword=keyword,
            total_count=data.get("total_count", len(items)),
            items=items,
        )

    # ── Shop scraping ──

    async def scrape_shop(
        self,
        shop_id: int,
        max_items: int = 0,
        sort_by: SortBy = SortBy.SALES,
        include_reviews: bool = False,
        max_reviews: int = 10,
    ) -> ShopDetail:
        """Scrape all products from a shop."""
        logger.info("Scraping shop: %d", shop_id)

        shop_data = await self.client.get_shop_info(shop_id)
        shop_info = parse_shop_info(shop_data)

        raw_items = await self.client.get_all_shop_items(
            shop_id, max_items=max_items, sort_by=sort_by
        )
        items = [parse_search_item(item, domain=self.domain) for item in raw_items]

        if include_reviews:
            for i, product in enumerate(items):
                if product.shop_id and product.item_id:
                    logger.info("Enriching shop product %d/%d", i + 1, len(items))
                    try:
                        full = await self.scrape_product(
                            product.shop_id,
                            product.item_id,
                            include_reviews=True,
                            max_reviews=max_reviews,
                        )
                        items[i] = full
                    except Exception as e:
                        logger.warning("Could not enrich product: %s", e)

        return ShopDetail(
            shop_info=shop_info,
            items=items,
            total_items=shop_info.item_count,
        )

    async def scrape_shop_by_username(
        self,
        username: str,
        max_items: int = 0,
        include_reviews: bool = False,
        max_reviews: int = 10,
    ) -> ShopDetail:
        """Scrape shop by username."""
        logger.info("Looking up shop username: %s", username)
        shop_data = await self.client.get_shop_by_username(username)
        shop_id = shop_data.get("shopid", shop_data.get("shop_id", 0))
        if not shop_id:
            raise ValueError(f"Could not find shop with username: {username}")
        return await self.scrape_shop(
            shop_id,
            max_items=max_items,
            include_reviews=include_reviews,
            max_reviews=max_reviews,
        )

    # ── Category scraping ──

    async def scrape_category(
        self,
        category_id: int,
        max_items: int = 0,
        sort_by: SortBy = SortBy.RELEVANCY,
        order: SortOrder = SortOrder.DESC,
        include_reviews: bool = False,
        max_reviews: int = 10,
    ) -> CategoryResult:
        """Scrape products from a category."""
        logger.info("Scraping category: %d", category_id)

        all_items: list[Product] = []
        offset = 0
        limit = 60
        total_count = 0

        while True:
            data = await self.client.search_by_category(
                category_id, offset=offset, limit=limit, sort_by=sort_by, order=order
            )

            items = data.get("items", [])
            if total_count == 0:
                total_count = data.get("total_count", 0)

            if not items:
                break

            parsed = [parse_search_item(item, domain=self.domain) for item in items]
            all_items.extend(parsed)

            if max_items > 0 and len(all_items) >= max_items:
                all_items = all_items[:max_items]
                break

            if len(items) < limit:
                break

            offset += limit

        if include_reviews:
            for i, product in enumerate(all_items):
                if product.shop_id and product.item_id:
                    logger.info("Enriching category product %d/%d", i + 1, len(all_items))
                    try:
                        full = await self.scrape_product(
                            product.shop_id,
                            product.item_id,
                            include_reviews=True,
                            max_reviews=max_reviews,
                        )
                        all_items[i] = full
                    except Exception as e:
                        logger.warning("Could not enrich product: %s", e)

        return CategoryResult(
            category_id=category_id,
            total_count=total_count,
            items=all_items,
        )

    # ── Utility ──

    def parse_url(self, url: str) -> ParsedLink:
        """Parse a URL and detect its type."""
        return parse_link(url)

    def detect(self, text: str) -> ParsedLink:
        """Auto-detect input type."""
        return detect_input(text)
