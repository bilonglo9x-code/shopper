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

## Cấu trúc dự án

```
shopper/
├── src/shopper/
│   ├── __init__.py
│   ├── cli.py              # CLI interface (Typer)
│   ├── constants.py         # Constants, enums, config
│   ├── models.py            # Pydantic data models
│   ├── api/
│   │   ├── __init__.py
│   │   └── client.py        # Shopee API client (httpx async)
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── product.py       # Product data parser
│   │   └── scraper.py       # Main scraper orchestrator
│   ├── exporters/
│   │   ├── __init__.py
│   │   └── exporter.py      # JSON/CSV exporters
│   └── parsers/
│       ├── __init__.py
│       └── link_parser.py   # URL parser & auto-detection
├── tests/
│   ├── test_link_parser.py
│   ├── test_product_parser.py
│   └── test_exporter.py
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
