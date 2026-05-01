# Testing Shopper API Server & Affiliate Integration

## Overview
The Shopper app has three components:
1. **Python CLI** (`shopper scrape/detect/info`) — scrapes Shopee data
2. **Chrome Extension** (`extension/`) — browser-based scraping with auth
3. **API Server** (`shopper server`) — FastAPI REST API for task management + affiliate links

## Starting the Server
```bash
pip install -e .
shopper server              # default: 0.0.0.0:8000
shopper server --port 3000  # custom port
shopper server --reload     # dev mode with auto-reload
```

API docs available at `http://localhost:8000/docs` (Swagger UI).

## Key Endpoints to Test

### Health & Utilities
- `GET /health` — server status, affiliate config state, task count
- `GET /api/detect?url=...` — link type detection (product/search/shop/category)

### Scraping Tasks
- `POST /api/tasks` — create background scraping task
- `GET /api/tasks` — list tasks (supports `?status=failed&limit=10`)
- `GET /api/tasks/{id}` — task status
- `GET /api/tasks/{id}/result` — full result with data
- `DELETE /api/tasks/{id}` — delete task
- `POST /api/scrape` — synchronous scrape (blocks until done)

### Affiliate (requires Shopee Affiliate credentials)
- `POST /api/affiliate/config` — configure `app_id` + `secret`
- `GET /api/affiliate/status` — check if configured
- `POST /api/affiliate/links` — generate affiliate short links
- `POST /api/affiliate/product-offers` — search products with commission info
- `POST /api/affiliate/shop-offers` — search shops with commission
- `POST /api/affiliate/conversion-report` — conversion report

## Known Limitations
- **Shopee anti-bot**: Server-side scraping gets HTTP 403 from Shopee. Tasks will complete with `status: failed` and `error: "HTTP 403"`. This is expected behavior — the Chrome Extension is recommended for actual data collection.
- **Affiliate credentials**: Without real `app_id`/`secret` from https://affiliate.shopee.vn/open_api/list, affiliate endpoints return `error [10020]: Invalid Credential`. You can still test the error handling paths.
- **Task storage**: In-memory with optional JSON persistence to `data/tasks.json`. Restarting the server without persistence loses tasks.

## Testing Approach
All server testing is shell-based (curl commands). No browser recording needed.

### Quick Smoke Test
```bash
# Start server
uvicorn shopper.server.app:app --port 8000 &
sleep 2

# Health
curl -s http://localhost:8000/health

# Detect link
curl -s "http://localhost:8000/api/detect?url=https://shopee.vn/Product-i.123.456"

# Create task
curl -s -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"url": "ao thun nam", "max_items": 5}'

# Check affiliate error without config
curl -s -X POST http://localhost:8000/api/affiliate/links \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://shopee.vn/product/1/2"]}'
```

### Unit Tests & Lint
```bash
python -m pytest tests/ -q   # 37+ tests
ruff check src/ tests/        # lint
```

## Devin Secrets Needed
- `SHOPEE_AFFILIATE_APP_ID` — for testing real affiliate link generation (optional)
- `SHOPEE_AFFILIATE_SECRET` — for testing real affiliate API calls (optional)

These are only needed for full affiliate testing. Server and scraping tests work without them.
