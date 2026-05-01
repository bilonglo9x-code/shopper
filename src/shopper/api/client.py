"""Shopee API client for fetching data."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from shopper.constants import (
    DEFAULT_DOMAIN,
    DEFAULT_HEADERS,
    DEFAULT_RATING_LIMIT,
    DEFAULT_SEARCH_LIMIT,
    DEFAULT_SHOP_ITEMS_LIMIT,
    MAX_RETRIES,
    REQUEST_DELAY,
    RETRY_DELAY,
    RatingFilter,
    SortBy,
    SortOrder,
)

logger = logging.getLogger(__name__)


class ShopeeAPIError(Exception):
    """Raised when Shopee API returns an error."""

    def __init__(self, message: str, status_code: int = 0, response_data: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class ShopeeClient:
    """Async HTTP client for Shopee's internal API."""

    def __init__(
        self,
        domain: str = DEFAULT_DOMAIN,
        cookies: dict[str, str] | None = None,
        proxy: str | None = None,
        request_delay: float = REQUEST_DELAY,
    ):
        self.domain = domain
        self.base_url = f"https://{domain}"
        self.request_delay = request_delay
        self._cookies = cookies or {}
        self._proxy = proxy
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {**DEFAULT_HEADERS, "Referer": self.base_url + "/"}
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                cookies=self._cookies,
                proxy=self._proxy,
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
                http2=True,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: object):
        await self.close()

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request with retry logic."""
        client = await self._get_client()
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                if attempt > 0:
                    await asyncio.sleep(RETRY_DELAY * attempt)

                if method.upper() == "GET":
                    response = await client.get(path, params=params)
                else:
                    response = await client.post(path, params=params, json=json_data)

                if response.status_code == 429:
                    logger.warning("Rate limited, waiting before retry...")
                    await asyncio.sleep(RETRY_DELAY * (attempt + 2))
                    continue

                response.raise_for_status()
                data = response.json()

                if self.request_delay > 0:
                    await asyncio.sleep(self.request_delay)

                return data

            except httpx.HTTPStatusError as e:
                last_error = ShopeeAPIError(
                    f"HTTP {e.response.status_code}: {path}",
                    status_code=e.response.status_code,
                )
                logger.warning(
                    "Request failed (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, last_error
                )
            except (httpx.RequestError, httpx.DecodingError) as e:
                last_error = ShopeeAPIError(f"Request error: {e}")
                logger.warning(
                    "Request error (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, e
                )

        raise last_error or ShopeeAPIError("Unknown error after retries")

    # ── Product APIs ──

    async def get_item(self, shop_id: int, item_id: int) -> dict[str, Any]:
        """Get product detail via /api/v4/item/get."""
        data = await self._request(
            "GET",
            "/api/v4/item/get",
            params={"shopid": shop_id, "itemid": item_id},
        )
        return data.get("data", data)

    async def get_item_detail(self, shop_id: int, item_id: int) -> dict[str, Any]:
        """Get full product detail via /api/v4/pdp/get_pc."""
        data = await self._request(
            "GET",
            "/api/v4/pdp/get_pc",
            params={"shop_id": shop_id, "item_id": item_id},
        )
        return data.get("data", data)

    # ── Rating / Review APIs ──

    async def get_ratings(
        self,
        shop_id: int,
        item_id: int,
        offset: int = 0,
        limit: int = DEFAULT_RATING_LIMIT,
        rating_filter: RatingFilter = RatingFilter.ALL,
    ) -> dict[str, Any]:
        """Get product ratings/reviews."""
        params: dict[str, Any] = {
            "shopid": shop_id,
            "itemid": item_id,
            "offset": offset,
            "limit": limit,
            "type": rating_filter.value,
            "flag": 1,
            "filter": 0,
        }
        data = await self._request("GET", "/api/v4/item/get_ratings", params=params)
        return data.get("data", data)

    async def get_all_ratings(
        self,
        shop_id: int,
        item_id: int,
        max_reviews: int = 0,
        rating_filter: RatingFilter = RatingFilter.ALL,
    ) -> list[dict[str, Any]]:
        """Get all ratings for a product with pagination."""
        all_ratings: list[dict[str, Any]] = []
        offset = 0
        limit = DEFAULT_RATING_LIMIT

        while True:
            data = await self.get_ratings(
                shop_id, item_id, offset=offset, limit=limit, rating_filter=rating_filter
            )

            ratings = data.get("ratings", [])
            if not ratings:
                break

            all_ratings.extend(ratings)
            logger.info("Fetched %d reviews (total: %d)", len(ratings), len(all_ratings))

            if max_reviews > 0 and len(all_ratings) >= max_reviews:
                all_ratings = all_ratings[:max_reviews]
                break

            if len(ratings) < limit:
                break

            offset += limit

        return all_ratings

    # ── Search APIs ──

    async def search_items(
        self,
        keyword: str,
        offset: int = 0,
        limit: int = DEFAULT_SEARCH_LIMIT,
        sort_by: SortBy = SortBy.RELEVANCY,
        order: SortOrder = SortOrder.DESC,
        rating_filter: int | None = None,
        price_min: int | None = None,
        price_max: int | None = None,
    ) -> dict[str, Any]:
        """Search for items by keyword."""
        params: dict[str, Any] = {
            "by": sort_by.value,
            "keyword": keyword,
            "limit": limit,
            "newest": offset,
            "order": order.value,
            "page_type": "search",
            "scenario": "PAGE_GLOBAL_SEARCH",
            "version": 2,
        }
        if rating_filter is not None:
            params["rating_filter"] = rating_filter
        if price_min is not None:
            params["price_min"] = price_min * 100000
        if price_max is not None:
            params["price_max"] = price_max * 100000

        data = await self._request("GET", "/api/v4/search/search_items", params=params)
        return data

    async def search_all(
        self,
        keyword: str,
        max_items: int = 0,
        sort_by: SortBy = SortBy.RELEVANCY,
        order: SortOrder = SortOrder.DESC,
    ) -> dict[str, Any]:
        """Search all items for a keyword with pagination."""
        all_items: list[dict[str, Any]] = []
        offset = 0
        limit = DEFAULT_SEARCH_LIMIT
        total_count = 0

        while True:
            data = await self.search_items(
                keyword, offset=offset, limit=limit, sort_by=sort_by, order=order
            )

            items = data.get("items", [])
            if total_count == 0:
                total_count = data.get("total_count", 0)

            if not items:
                break

            all_items.extend(items)
            logger.info("Search: fetched %d items (total: %d)", len(items), len(all_items))

            if max_items > 0 and len(all_items) >= max_items:
                all_items = all_items[:max_items]
                break

            if len(items) < limit:
                break

            offset += limit

        return {"items": all_items, "total_count": total_count}

    # ── Shop APIs ──

    async def get_shop_info(self, shop_id: int) -> dict[str, Any]:
        """Get shop information."""
        data = await self._request(
            "GET",
            "/api/v4/product/get_shop_info",
            params={"shopid": shop_id},
        )
        return data.get("data", data)

    async def get_shop_by_username(self, username: str) -> dict[str, Any]:
        """Get shop info by username via search/resolve."""
        data = await self._request(
            "GET",
            "/api/v4/shop/get_shop_detail",
            params={"username": username},
        )
        return data.get("data", data)

    async def get_shop_items(
        self,
        shop_id: int,
        offset: int = 0,
        limit: int = DEFAULT_SHOP_ITEMS_LIMIT,
        sort_by: SortBy = SortBy.SALES,
        order: SortOrder = SortOrder.DESC,
    ) -> dict[str, Any]:
        """Get items from a shop."""
        params: dict[str, Any] = {
            "shopid": shop_id,
            "offset": offset,
            "limit": limit,
            "order": order.value,
            "sort_by": sort_by.value,
        }
        data = await self._request("GET", "/api/v4/search/search_items", params=params)
        return data

    async def get_all_shop_items(
        self,
        shop_id: int,
        max_items: int = 0,
        sort_by: SortBy = SortBy.SALES,
    ) -> list[dict[str, Any]]:
        """Get all items from a shop with pagination."""
        all_items: list[dict[str, Any]] = []
        offset = 0
        limit = DEFAULT_SHOP_ITEMS_LIMIT

        while True:
            data = await self.get_shop_items(
                shop_id, offset=offset, limit=limit, sort_by=sort_by
            )

            items = data.get("items", [])
            if not items:
                break

            all_items.extend(items)
            logger.info("Shop items: fetched %d items (total: %d)", len(items), len(all_items))

            if max_items > 0 and len(all_items) >= max_items:
                all_items = all_items[:max_items]
                break

            if len(items) < limit:
                break

            offset += limit

        return all_items

    # ── Category APIs ──

    async def get_category_list(self) -> dict[str, Any]:
        """Get the full category tree."""
        data = await self._request("GET", "/api/v2/category_list/get")
        return data

    async def search_by_category(
        self,
        category_id: int,
        offset: int = 0,
        limit: int = DEFAULT_SEARCH_LIMIT,
        sort_by: SortBy = SortBy.RELEVANCY,
        order: SortOrder = SortOrder.DESC,
    ) -> dict[str, Any]:
        """Search items by category."""
        params: dict[str, Any] = {
            "by": sort_by.value,
            "limit": limit,
            "match_id": category_id,
            "newest": offset,
            "order": order.value,
            "page_type": "search",
            "scenario": "PAGE_CATEGORY",
            "version": 2,
        }
        data = await self._request("GET", "/api/v4/search/search_items", params=params)
        return data
