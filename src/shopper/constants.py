"""Constants for Shopee scraper."""

from enum import Enum

SHOPEE_DOMAINS: dict[str, str] = {
    "vn": "shopee.vn",
    "sg": "shopee.sg",
    "my": "shopee.com.my",
    "th": "shopee.co.th",
    "tw": "shopee.tw",
    "id": "shopee.co.id",
    "ph": "shopee.ph",
    "br": "shopee.com.br",
    "mx": "shopee.com.mx",
    "co": "shopee.com.co",
    "cl": "shopee.cl",
}

DEFAULT_DOMAIN = "shopee.vn"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

SHOPEE_IMAGE_BASE = "https://down-vn.img.susercontent.com/file/"
SHOPEE_VIDEO_BASE = "https://cvf.shopee.vn/file/"

DEFAULT_SEARCH_LIMIT = 60
DEFAULT_RATING_LIMIT = 15
DEFAULT_SHOP_ITEMS_LIMIT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2.0
REQUEST_DELAY = 1.0


class LinkType(str, Enum):
    PRODUCT = "product"
    SHOP = "shop"
    CATEGORY = "category"
    SEARCH = "search"
    DAILY_DISCOVER = "daily_discover"
    COLLECTION = "collection"
    UNKNOWN = "unknown"


class SortBy(str, Enum):
    RELEVANCY = "relevancy"
    CTIME = "ctime"
    SALES = "sales"
    PRICE = "price"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class RatingFilter(int, Enum):
    ALL = 0
    ONE_STAR = 1
    TWO_STARS = 2
    THREE_STARS = 3
    FOUR_STARS = 4
    FIVE_STARS = 5
    WITH_COMMENT = 6
    WITH_MEDIA = 7
