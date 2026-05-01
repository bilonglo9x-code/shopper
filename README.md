# Shopper - Công cụ thu thập dữ liệu Shopee

Ứng dụng hỗ trợ cào dữ liệu từ Shopee, tự động nhận diện link và thu thập đầy đủ thông tin sản phẩm.

## Tính năng

### Tự động nhận diện link
- **Sản phẩm**: `https://shopee.vn/Product-Name-i.{shop_id}.{item_id}`
- **Shop**: `https://shopee.vn/{shop_username}` hoặc `https://shopee.vn/shop/{shop_id}`
- **Danh mục**: `https://shopee.vn/Category-Name-cat.{category_id}`
- **Tìm kiếm**: `https://shopee.vn/search?keyword={keyword}` hoặc nhập trực tiếp từ khóa
- Hỗ trợ tất cả domain Shopee: VN, SG, MY, TH, TW, ID, PH, BR, MX, CO, CL

### Thu thập thông tin sản phẩm
- Tên, mô tả, thương hiệu
- Thuộc tính sản phẩm (chất liệu, xuất xứ, ...)
- Phân loại/biến thể (màu sắc, kích cỡ, ...) với giá từng biến thể
- Giá bán, giá gốc, giảm giá
- Doanh thu, số lượt bán (historical_sold)
- Hình ảnh, video sản phẩm
- Đánh giá (nội dung, số sao, hình ảnh, video)
- Thời gian đăng sản phẩm
- Thông tin shop (tên, rating, followers, ...)

### Thu thập hàng loạt
- Tìm kiếm sản phẩm theo keyword
- Thu thập sản phẩm theo danh mục
- Thu thập tất cả sản phẩm của 1 shop
- Hỗ trợ phân trang tự động

### Xuất dữ liệu
- JSON (đầy đủ chi tiết)
- CSV (dạng bảng phẳng)
- CSV riêng cho reviews

## Cài đặt

```bash
# Clone repo
git clone https://github.com/bilonglo9x-code/shopper.git
cd shopper

# Cài đặt dependencies
pip install -e .
```

Yêu cầu: Python >= 3.10

## Sử dụng

### CLI

```bash
# Thu thập 1 sản phẩm
shopper scrape "https://shopee.vn/Product-Name-i.123456.789012"

# Thu thập sản phẩm kèm reviews
shopper scrape "https://shopee.vn/Product-Name-i.123456.789012" --reviews --max-reviews 100

# Tìm kiếm theo keyword
shopper scrape "áo thun nam" --max-items 100

# Thu thập sản phẩm từ 1 shop
shopper scrape "https://shopee.vn/shopname" --max-items 50

# Thu thập sản phẩm theo danh mục
shopper scrape "https://shopee.vn/Thoi-Trang-Nam-cat.11035567" --max-items 100

# Xuất ra CSV
shopper scrape "áo thun nam" -o results.csv -f csv

# Xuất ra JSON
shopper scrape "áo thun nam" -o results.json

# Nhận diện loại link
shopper detect "https://shopee.vn/Product-i.123.456"

# Xem thông tin hỗ trợ
shopper info
```

### Tùy chọn

| Option | Mô tả |
|--------|--------|
| `--output, -o` | Đường dẫn file xuất |
| `--format, -f` | Định dạng: `json` (mặc định) hoặc `csv` |
| `--domain, -d` | Domain Shopee (mặc định: `shopee.vn`) |
| `--max-items, -m` | Số lượng sản phẩm tối đa (0 = tất cả) |
| `--reviews, -r` | Thu thập reviews |
| `--max-reviews` | Số reviews tối đa mỗi sản phẩm (mặc định: 50) |
| `--sort, -s` | Sắp xếp: `relevancy`, `ctime`, `sales`, `price` |
| `--verbose, -v` | Hiển thị chi tiết |

### Sử dụng trong Python

```python
import asyncio
from shopper.collectors.scraper import ShopeeScraper

async def main():
    async with ShopeeScraper(domain="shopee.vn") as scraper:
        # Tự động nhận diện và thu thập
        result = await scraper.scrape(
            "https://shopee.vn/Product-i.123.456",
            include_reviews=True,
            max_reviews=50,
        )

        # Hoặc thu thập theo keyword
        search = await scraper.scrape_search("áo thun nam", max_items=100)

        # Hoặc thu thập từ shop
        shop = await scraper.scrape_shop(shop_id=123456, max_items=50)

asyncio.run(main())
```

### Nhận diện link

```python
from shopper.parsers.link_parser import detect_input

# Tự động nhận diện
result = detect_input("https://shopee.vn/Product-i.123.456")
print(result.link_type)  # "product"
print(result.shop_id)    # 123
print(result.item_id)    # 456

result = detect_input("áo thun nam")
print(result.link_type)  # "search"
print(result.keyword)    # "áo thun nam"
```

## Chrome Extension

Extension Chrome cho phép thu thập dữ liệu Shopee trực tiếp từ trình duyệt, sử dụng phiên đăng nhập sẵn có để vượt qua các hạn chế anti-bot.

### Cài đặt Extension

1. Mở `chrome://extensions` trong Chrome
2. Bật **Developer mode** (góc trên bên phải)
3. Nhấn **Load unpacked** → chọn thư mục `extension/`
4. Extension "Shopper" sẽ xuất hiện trong thanh công cụ

### Sử dụng Extension

1. **Đăng nhập Shopee** trong trình duyệt (bắt buộc)
2. Mở trang Shopee (sản phẩm, tìm kiếm, shop, hoặc danh mục)
3. Nhấn vào icon Extension "Shopper" trên thanh công cụ
4. Extension tự động nhận diện loại trang:
   - **PRODUCT**: Trang chi tiết sản phẩm
   - **SEARCH**: Trang kết quả tìm kiếm
   - **SHOP**: Trang shop
   - **CATEGORY**: Trang danh mục
5. Cấu hình tùy chọn (max items, reviews, sort)
6. Nhấn **Scrape Data** để thu thập cơ bản, hoặc **Deep Scrape** để thu thập chi tiết từng sản phẩm
7. Xuất kết quả: **Export JSON**, **Export CSV**, hoặc **Reviews CSV**

### Tab Manual Input

Cho phép nhập URL hoặc keyword trực tiếp, chọn domain Shopee, và scrape mà không cần navigate thủ công.

### Tính năng Extension

| Tính năng | Mô tả |
|-----------|--------|
| Nhận diện trang | Tự động detect loại trang Shopee đang mở |
| Scrape sản phẩm | Thu thập đầy đủ: tên, giá, biến thể, hình ảnh, reviews |
| Scrape tìm kiếm | Thu thập danh sách sản phẩm theo keyword |
| Scrape shop | Thu thập tất cả sản phẩm của shop |
| Scrape danh mục | Thu thập sản phẩm theo category |
| Deep Scrape | Thu thập chi tiết từng sản phẩm trong danh sách |
| Export JSON | Xuất dữ liệu đầy đủ dạng JSON |
| Export CSV | Xuất dữ liệu dạng bảng CSV |
| Reviews CSV | Xuất riêng reviews ra file CSV |

## API Server

Server REST API để quản lý scraping tasks và tạo affiliate links.

### Khởi động Server

```bash
# Khởi động server (mặc định port 8000)
shopper server

# Tùy chỉnh port
shopper server --port 3000

# Chế độ development (auto-reload)
shopper server --reload
```

API docs tự động tại: `http://localhost:8000/docs`

### Scraping API

```bash
# Tạo task scraping (chạy background)
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"url": "áo thun nam", "max_items": 50}'

# Xem trạng thái task
curl http://localhost:8000/api/tasks/{task_id}

# Lấy kết quả khi hoàn thành
curl http://localhost:8000/api/tasks/{task_id}/result

# Scrape trực tiếp (đồng bộ, chờ kết quả)
curl -X POST http://localhost:8000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://shopee.vn/Product-i.123.456", "include_reviews": true}'

# Nhận diện link
curl "http://localhost:8000/api/detect?url=https://shopee.vn/Product-i.123.456"
```

### Shopee Affiliate API

Tạo affiliate links từ chương trình Shopee Affiliate. Yêu cầu `app_id` và `secret` từ [Shopee Affiliate Portal](https://affiliate.shopee.vn/open_api/list).

```bash
# 1. Cấu hình credentials
curl -X POST http://localhost:8000/api/affiliate/config \
  -H "Content-Type: application/json" \
  -d '{"app_id": "YOUR_APP_ID", "secret": "YOUR_SECRET", "region": "vn"}'

# 2. Tạo affiliate link (1 hoặc nhiều URL)
curl -X POST http://localhost:8000/api/affiliate/links \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://shopee.vn/product/123/456"],
    "sub_ids": ["campaign1", "source1"]
  }'

# 3. Tìm sản phẩm có hoa hồng cao
curl -X POST http://localhost:8000/api/affiliate/product-offers \
  -H "Content-Type: application/json" \
  -d '{"keyword": "áo thun nam", "sort_type": 5, "limit": 20}'

# 4. Tìm shop có commission cao
curl -X POST http://localhost:8000/api/affiliate/shop-offers \
  -H "Content-Type: application/json" \
  -d '{"sort_type": 2, "limit": 20}'

# 5. Xem báo cáo conversion
curl -X POST http://localhost:8000/api/affiliate/conversion-report \
  -H "Content-Type: application/json" \
  -d '{"start_time": 1714521600, "end_time": 1714608000}'
```

### API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|--------|
| GET | `/health` | Kiểm tra trạng thái server |
| POST | `/api/tasks` | Tạo scraping task (background) |
| GET | `/api/tasks` | Danh sách tasks |
| GET | `/api/tasks/{id}` | Trạng thái task |
| GET | `/api/tasks/{id}/result` | Kết quả task |
| DELETE | `/api/tasks/{id}` | Xóa task |
| POST | `/api/scrape` | Scrape đồng bộ |
| GET | `/api/detect` | Nhận diện link |
| POST | `/api/affiliate/config` | Cấu hình affiliate |
| GET | `/api/affiliate/status` | Trạng thái affiliate |
| POST | `/api/affiliate/links` | Tạo affiliate links |
| POST | `/api/affiliate/product-offers` | Tìm product offers |
| POST | `/api/affiliate/shop-offers` | Tìm shop offers |
| POST | `/api/affiliate/conversion-report` | Báo cáo conversion |

## Cấu trúc dự án

```
shopper/
├── src/shopper/           # Python app
│   ├── __init__.py
│   ├── cli.py              # CLI interface (Typer)
│   ├── constants.py         # Constants, enums, config
│   ├── models.py            # Pydantic data models
│   ├── api/
│   │   └── client.py        # Shopee API client (httpx async)
│   ├── collectors/
│   │   ├── product.py       # Product data parser
│   │   └── scraper.py       # Main scraper orchestrator
│   ├── exporters/
│   │   └── exporter.py      # JSON/CSV exporters
│   ├── parsers/
│   │   └── link_parser.py   # URL parser & auto-detection
│   ├── server/              # FastAPI server
│   │   ├── app.py           # API endpoints
│   │   ├── models.py        # Request/response models
│   │   └── storage.py       # Task storage
│   └── affiliate/           # Shopee Affiliate client
│       └── client.py        # GraphQL API + SHA256 auth
├── extension/             # Chrome Extension
│   ├── manifest.json        # Manifest V3 config
│   ├── popup.html           # Popup UI
│   ├── popup.js             # Popup logic
│   ├── content.js           # Content script
│   ├── background.js        # Service worker
│   ├── lib/
│   │   ├── shopee-api.js    # Shopee API library
│   │   └── exporter.js      # Export utilities
│   └── icons/               # Extension icons
├── tests/
├── pyproject.toml
└── README.md
```

## Dữ liệu thu thập

### Thông tin sản phẩm
| Trường | Mô tả |
|--------|--------|
| `name` | Tên sản phẩm |
| `description` | Mô tả chi tiết |
| `brand` | Thương hiệu |
| `price_info` | Giá bán, giá gốc, giảm giá |
| `tier_variations` | Phân loại (màu, size, ...) |
| `models` | Biến thể với giá từng loại |
| `attributes` | Thuộc tính (chất liệu, xuất xứ, ...) |
| `images` | Danh sách URL hình ảnh |
| `video_url` | URL video sản phẩm |
| `rating_summary` | Tóm tắt đánh giá (sao, số lượng) |
| `historical_sold` | Tổng số đã bán |
| `reviews` | Danh sách đánh giá chi tiết |
| `ctime` | Thời gian đăng sản phẩm |
| `shop_info` | Thông tin shop bán |

### Thông tin review
| Trường | Mô tả |
|--------|--------|
| `rating_star` | Số sao (1-5) |
| `comment` | Nội dung đánh giá |
| `author_username` | Người đánh giá |
| `model_name` | Phân loại đã mua |
| `images` | Hình ảnh đánh giá |
| `videos` | Video đánh giá |
| `liked_count` | Số lượt thích |
| `tags` | Nhãn đánh giá |

## License

MIT
