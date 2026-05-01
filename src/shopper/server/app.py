"""FastAPI server for Shopper - scraping management and affiliate links."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from shopper.affiliate.client import ShopeeAffiliateClient, ShopeeAffiliateError
from shopper.collectors.scraper import ShopeeScraper
from shopper.constants import SortBy
from shopper.models import CategoryResult, Product, SearchResult, ShopDetail
from shopper.parsers.link_parser import detect_input
from shopper.server.models import (
    AffiliateConfigRequest,
    AffiliateLink,
    ConversionReportRequest,
    GenerateLinkRequest,
    GenerateLinkResponse,
    ProductOfferRequest,
    ScrapeRequest,
    ShopOfferRequest,
    TaskResponse,
    TaskResult,
    TaskStatus,
    TaskType,
)
from shopper.server.storage import TaskStore

logger = logging.getLogger(__name__)

# Global state
_store = TaskStore(persist_path=Path("data/tasks.json"))
_affiliate_client: ShopeeAffiliateClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Application lifespan: startup and shutdown."""
    logger.info("Shopper API server starting...")
    yield
    if _affiliate_client:
        await _affiliate_client.close()
    logger.info("Shopper API server stopped.")


app = FastAPI(
    title="Shopper API",
    description=(
        "API server for Shopee data collection and affiliate link generation.\n\n"
        "## Features\n"
        "- Scraping task management (create, list, get results, delete)\n"
        "- Shopee Affiliate link generation (single & batch)\n"
        "- Product & shop offer discovery\n"
        "- Conversion report retrieval"
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helper ──


def _detect_task_type(url: str) -> TaskType | None:
    parsed = detect_input(url)
    type_map = {
        "product": TaskType.PRODUCT,
        "search": TaskType.SEARCH,
        "shop": TaskType.SHOP,
        "category": TaskType.CATEGORY,
    }
    return type_map.get(parsed.link_type)


def _serialize_result(result: Any) -> tuple[dict | list, int]:
    """Serialize scraper result to dict and item count."""
    if isinstance(result, Product):
        return result.model_dump(mode="json"), 1
    if isinstance(result, SearchResult):
        data = result.model_dump(mode="json")
        return data, len(result.items)
    if isinstance(result, ShopDetail):
        data = result.model_dump(mode="json")
        return data, len(result.items)
    if isinstance(result, CategoryResult):
        data = result.model_dump(mode="json")
        return data, len(result.items)
    return {}, 0


async def _run_scrape_task(task_id: str, req: ScrapeRequest) -> None:
    """Background task to run a scraping job."""
    _store.set_running(task_id)
    try:
        async with ShopeeScraper(domain=req.domain) as scraper:
            result = await scraper.scrape(
                req.url,
                max_items=req.max_items,
                include_reviews=req.include_reviews,
                max_reviews=req.max_reviews,
                sort_by=SortBy(req.sort_by),
            )

        data, total = _serialize_result(result)

        # Auto-generate affiliate links if requested
        if req.generate_affiliate_links and _affiliate_client:
            data = await _enrich_with_affiliate_links(data, result)

        _store.set_completed(task_id, data, total)
    except Exception as e:
        logger.error("Task %s failed: %s", task_id, e)
        _store.set_failed(task_id, str(e))


async def _enrich_with_affiliate_links(data: dict, result: Any) -> dict:
    """Add affiliate links to scraped data."""
    if not _affiliate_client:
        return data

    urls_to_convert = []
    if isinstance(result, Product) and result.url:
        urls_to_convert.append(result.url)
    elif hasattr(result, "items"):
        for item in result.items:
            if hasattr(item, "url") and item.url:
                urls_to_convert.append(item.url)

    if not urls_to_convert:
        return data

    try:
        if len(urls_to_convert) == 1:
            short = await _affiliate_client.generate_short_link(urls_to_convert[0])
            data["affiliate_link"] = short
        else:
            batch = await _affiliate_client.generate_batch_short_links(urls_to_convert)
            url_map = {r["originUrl"]: r["shortLink"] for r in batch}
            if "items" in data:
                for item in data["items"]:
                    url = item.get("url", "")
                    if url in url_map:
                        item["affiliate_link"] = url_map[url]
    except Exception:
        logger.warning("Failed to generate affiliate links", exc_info=True)

    return data


# ── Static files ──

_static_dir = Path(__file__).parent / "static"
if _static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")


@app.get("/", include_in_schema=False)
async def root():
    """Serve the web UI."""
    index = _static_dir / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "Shopper API", "docs": "/docs"}


# ── Health ──


@app.get("/health", tags=["System"])
async def health_check():
    """Check server health."""
    return {
        "status": "ok",
        "affiliate_configured": _affiliate_client is not None,
        "tasks_count": len(_store._tasks),
    }


# ── Scraping Task Endpoints ──


@app.post("/api/tasks", response_model=TaskResponse, tags=["Scraping"])
async def create_task(req: ScrapeRequest, bg: BackgroundTasks):
    """Create a new scraping task.

    The task runs in the background. Use GET /api/tasks/{task_id} to check status
    and GET /api/tasks/{task_id}/result to get the data when completed.
    """
    task_type = _detect_task_type(req.url)
    task_id = _store.create_task(req.url, task_type)
    bg.add_task(_run_scrape_task, task_id, req)
    return _store.get_task(task_id)


@app.get("/api/tasks", response_model=list[TaskResponse], tags=["Scraping"])
async def list_tasks(
    status: TaskStatus | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List all scraping tasks, optionally filtered by status."""
    return _store.list_tasks(status=status, limit=limit, offset=offset)


@app.get("/api/tasks/{task_id}", response_model=TaskResponse, tags=["Scraping"])
async def get_task(task_id: str):
    """Get task status by ID."""
    task = _store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.get("/api/tasks/{task_id}/result", response_model=TaskResult, tags=["Scraping"])
async def get_task_result(task_id: str):
    """Get full task result including scraped data."""
    result = _store.get_task_result(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    if result.status == TaskStatus.PENDING or result.status == TaskStatus.RUNNING:
        raise HTTPException(status_code=202, detail="Task still in progress")
    return result


@app.delete("/api/tasks/{task_id}", tags=["Scraping"])
async def delete_task(task_id: str):
    """Delete a task and its data."""
    if not _store.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": True}


# ── Scrape (synchronous, blocking) ──


@app.post("/api/scrape", tags=["Scraping"])
async def scrape_now(req: ScrapeRequest):
    """Run a scraping job synchronously and return results immediately.

    For large scraping jobs, prefer POST /api/tasks for background processing.
    """
    try:
        async with ShopeeScraper(domain=req.domain) as scraper:
            result = await scraper.scrape(
                req.url,
                max_items=req.max_items,
                include_reviews=req.include_reviews,
                max_reviews=req.max_reviews,
                sort_by=SortBy(req.sort_by),
            )
        data, total = _serialize_result(result)

        if req.generate_affiliate_links and _affiliate_client:
            data = await _enrich_with_affiliate_links(data, result)

        return {"status": "ok", "total_items": total, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Affiliate Configuration ──


@app.post("/api/affiliate/config", tags=["Affiliate"])
async def configure_affiliate(req: AffiliateConfigRequest):
    """Configure Shopee Affiliate API credentials.

    Required before using any affiliate endpoints.
    Get your app_id and secret from: https://affiliate.shopee.vn/open_api/list
    """
    global _affiliate_client
    if _affiliate_client:
        await _affiliate_client.close()
    _affiliate_client = ShopeeAffiliateClient(
        app_id=req.app_id,
        secret=req.secret,
        region=req.region,
    )
    return {"status": "ok", "message": "Affiliate credentials configured"}


@app.get("/api/affiliate/status", tags=["Affiliate"])
async def affiliate_status():
    """Check if affiliate credentials are configured."""
    return {
        "configured": _affiliate_client is not None,
        "region": getattr(_affiliate_client, "base_url", None),
    }


# ── Affiliate Link Generation ──


@app.post(
    "/api/affiliate/links",
    response_model=GenerateLinkResponse,
    tags=["Affiliate"],
)
async def generate_affiliate_links(req: GenerateLinkRequest):
    """Generate affiliate tracking links from Shopee URLs.

    Supports single and batch link generation (up to 50 URLs).
    Sub IDs can be used for campaign tracking.
    """
    if not _affiliate_client:
        raise HTTPException(
            status_code=400,
            detail="Affiliate not configured. POST /api/affiliate/config first.",
        )

    try:
        links = []
        if len(req.urls) == 1:
            short = await _affiliate_client.generate_short_link(
                req.urls[0], sub_ids=req.sub_ids
            )
            links.append(AffiliateLink(original_url=req.urls[0], affiliate_url=short))
        else:
            batch = await _affiliate_client.generate_batch_short_links(
                req.urls, sub_ids=req.sub_ids
            )
            for item in batch:
                links.append(
                    AffiliateLink(
                        original_url=item["originUrl"],
                        affiliate_url=item["shortLink"],
                    )
                )
        return GenerateLinkResponse(links=links, total=len(links))
    except ShopeeAffiliateError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Affiliate Offers ──


@app.post("/api/affiliate/product-offers", tags=["Affiliate"])
async def get_product_offers(req: ProductOfferRequest):
    """Search product offers with commission info.

    Find products with high affiliate commissions.
    """
    if not _affiliate_client:
        raise HTTPException(
            status_code=400,
            detail="Affiliate not configured. POST /api/affiliate/config first.",
        )
    try:
        return await _affiliate_client.get_product_offers(
            keyword=req.keyword,
            shop_id=req.shop_id,
            item_id=req.item_id,
            sort_type=req.sort_type,
            page=req.page,
            limit=req.limit,
        )
    except ShopeeAffiliateError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/affiliate/shop-offers", tags=["Affiliate"])
async def get_shop_offers(req: ShopOfferRequest):
    """Search shop offers with commission info.

    Find shops with high affiliate commission rates.
    """
    if not _affiliate_client:
        raise HTTPException(
            status_code=400,
            detail="Affiliate not configured. POST /api/affiliate/config first.",
        )
    try:
        return await _affiliate_client.get_shop_offers(
            keyword=req.keyword,
            shop_id=req.shop_id,
            sort_type=req.sort_type,
            page=req.page,
            limit=req.limit,
        )
    except ShopeeAffiliateError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Affiliate Reports ──


@app.post("/api/affiliate/conversion-report", tags=["Affiliate"])
async def get_conversion_report(req: ConversionReportRequest):
    """Get affiliate conversion report for a date range.

    Track your affiliate earnings and conversion performance.
    """
    if not _affiliate_client:
        raise HTTPException(
            status_code=400,
            detail="Affiliate not configured. POST /api/affiliate/config first.",
        )
    try:
        return await _affiliate_client.get_conversion_report(
            start_time=req.start_time,
            end_time=req.end_time,
            page=req.page,
            limit=req.limit,
        )
    except ShopeeAffiliateError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Link Detection Utility ──


@app.get("/api/detect", tags=["Utilities"])
async def detect_link(url: str):
    """Detect Shopee link type and extract IDs.

    Returns the detected type (product/search/shop/category) and extracted parameters.
    """
    parsed = detect_input(url)
    return parsed.model_dump(mode="json")
