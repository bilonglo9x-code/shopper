"""Shopee Affiliate Open API client.

Implements SHA256 signature authentication and GraphQL mutations/queries
for the Shopee Affiliate program.

Requires: app_id and secret from Shopee Affiliate portal.
Docs: https://affiliate.shopee.vn/open_api/list
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any

import httpx

# Affiliate API endpoints per region
AFFILIATE_API_HOSTS: dict[str, str] = {
    "vn": "open-api.affiliate.shopee.vn",
    "sg": "open-api.affiliate.shopee.sg",
    "my": "open-api.affiliate.shopee.com.my",
    "th": "open-api.affiliate.shopee.co.th",
    "tw": "open-api.affiliate.shopee.tw",
    "id": "open-api.affiliate.shopee.co.id",
    "ph": "open-api.affiliate.shopee.ph",
    "br": "open-api.affiliate.shopee.com.br",
    "mx": "open-api.affiliate.shopee.com.mx",
    "co": "open-api.affiliate.shopee.com.co",
    "cl": "open-api.affiliate.shopee.cl",
}

DEFAULT_AFFILIATE_REGION = "vn"


def _generate_signature(app_id: str, secret: str, timestamp: int) -> str:
    """Generate SHA256 HMAC signature for Shopee Affiliate API.

    Format: SHA256 Credential={app_id}, Signature={hmac}, Timestamp={ts}
    The payload to sign is: {app_id}{timestamp}
    """
    payload = f"{app_id}{timestamp}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"SHA256 Credential={app_id}, Signature={sig}, Timestamp={timestamp}"


class ShopeeAffiliateClient:
    """Client for Shopee Affiliate Open API (GraphQL)."""

    def __init__(
        self,
        app_id: str,
        secret: str,
        region: str = DEFAULT_AFFILIATE_REGION,
    ) -> None:
        self.app_id = app_id
        self.secret = secret
        host = AFFILIATE_API_HOSTS.get(region, AFFILIATE_API_HOSTS[DEFAULT_AFFILIATE_REGION])
        self.base_url = f"https://{host}/graphql"
        self._client = httpx.AsyncClient(timeout=30)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> ShopeeAffiliateClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def _execute(self, query: str, variables: dict[str, Any] | None = None) -> dict:
        """Execute a GraphQL query/mutation with signed auth."""
        timestamp = int(time.time())
        auth = _generate_signature(self.app_id, self.secret, timestamp)

        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        resp = await self._client.post(
            self.base_url,
            json=payload,
            headers={
                "Authorization": auth,
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        result = resp.json()

        if "errors" in result:
            raise ShopeeAffiliateError(result["errors"])
        return result.get("data", {})

    # ── Link Generation ──

    async def generate_short_link(
        self,
        origin_url: str,
        sub_ids: list[str] | None = None,
    ) -> str:
        """Generate a single affiliate short link.

        Args:
            origin_url: Original Shopee product/page URL.
            sub_ids: Optional list of up to 5 sub IDs for tracking.

        Returns:
            Short affiliate link (e.g. https://shope.ee/abc123).
        """
        query = """mutation GenerateShortLink($input: GenerateShortLinkInput!) {
    generateShortLink(input: $input) {
        shortLink
    }
}"""
        variables: dict[str, Any] = {"input": {"originUrl": origin_url}}
        if sub_ids:
            variables["input"]["subIds"] = sub_ids[:5]
        data = await self._execute(query, variables=variables)
        return data["generateShortLink"]["shortLink"]

    async def generate_batch_short_links(
        self,
        urls: list[str],
        sub_ids: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """Generate multiple affiliate short links in one request.

        Args:
            urls: List of original Shopee URLs.
            sub_ids: Optional sub IDs applied to all links.

        Returns:
            List of dicts with 'originUrl' and 'shortLink'.
        """
        query = """mutation GenerateBatchShortLink($input: GenerateBatchShortLinkInput!) {
    generateBatchShortLink(input: $input) {
        shortLinks {
            originUrl
            shortLink
        }
    }
}"""
        variables: dict[str, Any] = {"input": {"originUrls": urls}}
        if sub_ids:
            variables["input"]["subIds"] = sub_ids[:5]
        data = await self._execute(query, variables=variables)
        return data["generateBatchShortLink"]["shortLinks"]

    # ── Offer Lists ──

    async def get_product_offers(
        self,
        keyword: str | None = None,
        shop_id: int | None = None,
        item_id: int | None = None,
        sort_type: int = 2,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """Get product offer list with commission info.

        Args:
            keyword: Search by product name.
            shop_id: Filter by shop.
            item_id: Filter by item.
            sort_type: 1=relevant, 2=sales, 3=price desc, 4=price asc, 5=commission desc.
            page: Page number.
            limit: Items per page.
        """
        query = """query ProductOfferV2(
    $keyword: String, $shopId: Int64, $itemId: Int64,
    $sortType: Int, $page: Int, $limit: Int
) {
    productOfferV2(
        keyword: $keyword, shopId: $shopId, itemId: $itemId,
        sortType: $sortType, page: $page, limit: $limit
    ) {
        nodes {
            itemId
            commissionRate
            sellerCommissionRate
            shopeeCommissionRate
            commission
            sales
            priceMin
            priceMax
            productName
            imageUrl
            offerLink
            ratingStar
            productCatIds
            shopId
            shopName
            shopType
        }
        pageInfo {
            page
            limit
            hasNextPage
        }
    }
}"""
        variables: dict[str, Any] = {
            "sortType": sort_type,
            "page": page,
            "limit": limit,
        }
        if keyword:
            variables["keyword"] = keyword
        if shop_id:
            variables["shopId"] = shop_id
        if item_id:
            variables["itemId"] = item_id
        return await self._execute(query, variables=variables)

    async def get_shop_offers(
        self,
        keyword: str | None = None,
        shop_id: int | None = None,
        sort_type: int = 2,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """Get shop offer list.

        Args:
            keyword: Search by shop name.
            shop_id: Filter by shop ID.
            sort_type: 1=update time, 2=commission desc, 3=popularity.
            page: Page number.
            limit: Items per page.
        """
        query = """query ShopOfferV2(
    $keyword: String, $shopId: Int64,
    $sortType: Int, $page: Int, $limit: Int
) {
    shopOfferV2(
        keyword: $keyword, shopId: $shopId,
        sortType: $sortType, page: $page, limit: $limit
    ) {
        nodes {
            shopId
            shopName
            commissionRate
            imageUrl
            offerLink
            originalLink
            ratingStar
            shopType
            remainingBudget
            periodStartTime
            periodEndTime
            sellerCommCoveRatio
        }
        pageInfo {
            page
            limit
            hasNextPage
        }
    }
}"""
        variables: dict[str, Any] = {
            "sortType": sort_type,
            "page": page,
            "limit": limit,
        }
        if keyword:
            variables["keyword"] = keyword
        if shop_id:
            variables["shopId"] = shop_id
        return await self._execute(query, variables=variables)

    # ── Reports ──

    async def get_conversion_report(
        self,
        start_time: int,
        end_time: int,
        page: int = 1,
        limit: int = 50,
    ) -> dict:
        """Get conversion report for a time range.

        Args:
            start_time: Unix timestamp start.
            end_time: Unix timestamp end.
            page: Page number.
            limit: Items per page.
        """
        query = """query ConversionReport(
    $startTime: Int64!, $endTime: Int64!, $page: Int, $limit: Int
) {
    conversionReport(
        startTime: $startTime, endTime: $endTime,
        page: $page, limit: $limit
    ) {
        nodes {
            conversionId
            itemId
            shopId
            itemName
            commissionRate
            commission
            orderAmount
            conversionTime
            clickTime
            status
            subIds
        }
        pageInfo {
            page
            limit
            hasNextPage
        }
    }
}"""
        variables = {
            "startTime": start_time,
            "endTime": end_time,
            "page": page,
            "limit": limit,
        }
        return await self._execute(query, variables=variables)


class ShopeeAffiliateError(Exception):
    """Error from Shopee Affiliate API."""

    def __init__(self, errors: list[dict]) -> None:
        self.errors = errors
        messages = [e.get("message", str(e)) for e in errors]
        super().__init__(f"Shopee Affiliate API error: {'; '.join(messages)}")
