/**
 * Shopee API client - runs in browser context with user's cookies.
 */

const SHOPEE_DOMAINS = {
  vn: 'shopee.vn', sg: 'shopee.sg', my: 'shopee.com.my',
  th: 'shopee.co.th', tw: 'shopee.tw', id: 'shopee.co.id',
  ph: 'shopee.ph', br: 'shopee.com.br', mx: 'shopee.com.mx',
  co: 'shopee.com.co', cl: 'shopee.cl',
};

const REQUEST_DELAY = 500;
const MAX_RETRIES = 3;

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function getDomain() {
  return location.hostname;
}

function getBaseUrl() {
  return `https://${getDomain()}`;
}

async function apiGet(path, params = {}, retries = MAX_RETRIES) {
  const url = new URL(path, getBaseUrl());
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) url.searchParams.set(k, v);
  });

  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const resp = await fetch(url.toString(), {
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
      });
      if (!resp.ok) {
        if (attempt < retries) {
          await sleep(1000 * attempt);
          continue;
        }
        throw new Error(`HTTP ${resp.status}: ${path}`);
      }
      const data = await resp.json();
      if (data.error && data.error !== 0) {
        if (attempt < retries) {
          await sleep(1000 * attempt);
          continue;
        }
        throw new Error(`API error ${data.error}: ${data.error_msg || path}`);
      }
      return data;
    } catch (e) {
      if (attempt >= retries) throw e;
      await sleep(1000 * attempt);
    }
  }
}

// ── Link detection ──

const LINK_PATTERNS = {
  product: [
    /-i\.(\d+)\.(\d+)/,                    // shopee.vn/Name-i.shopId.itemId
    /\/product\/(\d+)\/(\d+)/,              // shopee.vn/product/shopId/itemId
  ],
  shop: [
    /\/shop\/(\d+)/,                        // shopee.vn/shop/123
  ],
  category: [
    /-cat\.(\d+)/,                          // shopee.vn/Name-cat.123
  ],
  search: [
    /\/search\?.*keyword=([^&]+)/,          // shopee.vn/search?keyword=xxx
  ],
};

function detectLink(url) {
  for (const pattern of LINK_PATTERNS.product) {
    const m = url.match(pattern);
    if (m) return { type: 'product', shopId: parseInt(m[1]), itemId: parseInt(m[2]) };
  }
  for (const pattern of LINK_PATTERNS.category) {
    const m = url.match(pattern);
    if (m) return { type: 'category', categoryId: parseInt(m[1]) };
  }
  for (const pattern of LINK_PATTERNS.search) {
    const m = url.match(pattern);
    if (m) return { type: 'search', keyword: decodeURIComponent(m[1].replace(/\+/g, ' ')) };
  }
  for (const pattern of LINK_PATTERNS.shop) {
    const m = url.match(pattern);
    if (m) return { type: 'shop', shopId: parseInt(m[1]) };
  }
  // Check if it's a shop username URL (e.g. /username without other patterns)
  const pathMatch = url.match(/shopee\.[^/]+\/([a-zA-Z0-9_.]+)(?:\?|$)/);
  if (pathMatch && !url.includes('/search') && !pathMatch[1].match(/^(seller|buyer|m|cart|checkout|coins)/)) {
    return { type: 'shop', username: pathMatch[1] };
  }
  return { type: 'unknown' };
}

// ── Product scraping ──

async function scrapeProduct(shopId, itemId, opts = {}) {
  const { includeReviews = true, maxReviews = 50, onProgress } = opts;

  if (onProgress) onProgress('Fetching product info...');
  const itemData = await apiGet('/api/v4/item/get', { shopid: shopId, itemid: itemId });
  const item = itemData.data;
  if (!item) throw new Error('Product not found');

  // Try PDP endpoint for more details
  let pdpData = null;
  try {
    pdpData = await apiGet('/api/v4/pdp/get_pc', {
      shop_id: shopId, item_id: itemId, sku_id: 0,
    });
  } catch { /* optional */ }

  const product = parseProduct(item, pdpData?.data);

  // Fetch shop info
  if (onProgress) onProgress('Fetching shop info...');
  try {
    const shopData = await apiGet('/api/v4/product/get_shop_info', { shopid: shopId });
    product.shop = parseShopInfo(shopData.data);
  } catch { /* optional */ }

  // Fetch reviews
  if (includeReviews && maxReviews > 0) {
    if (onProgress) onProgress('Fetching reviews...');
    product.reviews = await fetchAllReviews(shopId, itemId, maxReviews, onProgress);
  }

  return product;
}

function parseProduct(item, pdpDetail = null) {
  const domain = getDomain();
  const priceDiv = item.price_before_discount ? 100000 : 100000;

  const product = {
    item_id: item.itemid,
    shop_id: item.shopid,
    name: item.name,
    description: item.description || (pdpDetail?.product?.description) || '',
    brand: item.brand || '',
    url: `https://${domain}/product/${item.shopid}/${item.itemid}`,
    price: {
      price: item.price / 100000,
      price_min: item.price_min / 100000,
      price_max: item.price_max / 100000,
      price_before_discount: item.price_before_discount ? item.price_before_discount / 100000 : null,
      price_min_before_discount: item.price_min_before_discount ? item.price_min_before_discount / 100000 : null,
      price_max_before_discount: item.price_max_before_discount ? item.price_max_before_discount / 100000 : null,
      discount: item.raw_discount || item.discount || null,
      currency: item.currency || 'VND',
    },
    rating: {
      rating_star: item.item_rating?.rating_star || 0,
      rating_count: item.item_rating?.rating_count || [0,0,0,0,0,0],
      rcount_with_context: item.item_rating?.rcount_with_context || 0,
      rcount_with_image: item.item_rating?.rcount_with_image || 0,
    },
    sold: item.historical_sold || item.sold || 0,
    stock: item.stock || 0,
    view_count: item.view_count || 0,
    liked_count: item.liked_count || 0,
    ctime: item.ctime ? new Date(item.ctime * 1000).toISOString() : null,
    condition: item.condition === 1 ? 'new' : 'used',
    status: item.status,
    images: (item.images || []).map(img =>
      img.startsWith('http') ? img : `https://down-vn.img.susercontent.com/file/${img}`
    ),
    video: item.video_info_list?.[0]?.default_format?.url || null,
    attributes: (item.attributes || []).map(a => ({
      name: a.name, value: a.value,
    })),
    tier_variations: (item.tier_variations || []).map(tv => ({
      name: tv.name,
      options: tv.options,
      images: tv.images || [],
    })),
    models: (item.models || []).map(m => ({
      name: m.name,
      price: m.price / 100000,
      price_before_discount: m.price_before_discount ? m.price_before_discount / 100000 : null,
      stock: m.stock,
      sold: m.sold || 0,
      sku: m.item_model_id || m.modelid,
    })),
    categories: item.categories || item.fe_categories || [],
    shop: { shop_id: item.shopid },
    reviews: [],
  };

  return product;
}

function parseShopInfo(data) {
  if (!data) return null;
  return {
    shop_id: data.shopid || data.shop_id,
    name: data.name || data.shop_name || '',
    username: data.account?.username || data.username || '',
    location: data.shop_location || '',
    follower_count: data.follower_count || 0,
    item_count: data.item_count || 0,
    rating_star: data.rating_star || 0,
    response_rate: data.response_rate || 0,
    response_time: data.response_time || 0,
    is_official: data.is_official_shop || false,
    is_preferred: data.is_preferred_plus_seller || false,
    url: `https://${getDomain()}/shop/${data.shopid || data.shop_id}`,
  };
}

// ── Reviews ──

async function fetchAllReviews(shopId, itemId, maxReviews = 50, onProgress) {
  const reviews = [];
  const limit = Math.min(maxReviews, 50);
  let offset = 0;

  while (reviews.length < maxReviews) {
    if (onProgress) onProgress(`Fetching reviews ${reviews.length + 1}-${Math.min(reviews.length + limit, maxReviews)}...`);
    await sleep(REQUEST_DELAY);

    try {
      const data = await apiGet('/api/v4/item/get_ratings', {
        filter: 0, flag: 1,
        itemid: itemId, shopid: shopId,
        limit, offset, type: 0,
      });

      const ratings = data.data?.ratings || [];
      if (ratings.length === 0) break;

      for (const r of ratings) {
        if (reviews.length >= maxReviews) break;
        reviews.push({
          author: r.author_username || '',
          rating: r.rating_star,
          comment: r.comment || '',
          time: r.ctime ? new Date(r.ctime * 1000).toISOString() : null,
          images: (r.images || []).map(img =>
            img.startsWith('http') ? img : `https://down-vn.img.susercontent.com/file/${img}`
          ),
          videos: (r.videos || []).map(v => v.url || v),
          likes: r.like_count || 0,
          model: r.product_items?.[0]?.model_name || '',
        });
      }

      offset += ratings.length;
      if (ratings.length < limit) break;
    } catch (e) {
      console.warn('Failed to fetch reviews:', e);
      break;
    }
  }

  return reviews;
}

// ── Search ──

async function scrapeSearch(keyword, opts = {}) {
  const { maxItems = 60, sortBy = 'relevancy', includeReviews = false, maxReviews = 10, onProgress } = opts;

  if (onProgress) onProgress(`Searching: "${keyword}"...`);

  const items = [];
  let newest = 0;
  const limit = 60;
  let totalCount = 0;

  while (items.length < maxItems || maxItems === 0) {
    await sleep(REQUEST_DELAY);
    const data = await apiGet('/api/v4/search/search_items', {
      by: sortBy, keyword, limit,
      newest, order: 'desc',
      page_type: 'search',
      scenario: 'PAGE_GLOBAL_SEARCH',
      version: 2,
    });

    totalCount = data.total_count || 0;
    const resultItems = data.items || [];
    if (resultItems.length === 0) break;

    for (const ri of resultItems) {
      if (maxItems > 0 && items.length >= maxItems) break;
      const basic = ri.item_basic;
      items.push({
        item_id: basic.itemid,
        shop_id: basic.shopid,
        name: basic.name,
        price: basic.price / 100000,
        price_min: basic.price_min / 100000,
        price_max: basic.price_max / 100000,
        discount: basic.raw_discount || null,
        sold: basic.historical_sold || basic.sold || 0,
        stock: basic.stock || 0,
        rating: basic.item_rating?.rating_star || 0,
        image: basic.image ? `https://down-vn.img.susercontent.com/file/${basic.image}` : '',
        location: basic.shop_location || '',
        url: `https://${getDomain()}/product/${basic.shopid}/${basic.itemid}`,
      });
    }

    newest += resultItems.length;
    if (onProgress) onProgress(`Found ${items.length} items...`);
    if (resultItems.length < limit) break;
  }

  return {
    type: 'search',
    keyword,
    total_count: totalCount || items.length,
    items,
  };
}

// ── Shop scraping ──

async function scrapeShop(shopId, opts = {}) {
  const { maxItems = 0, sortBy = 'pop', includeReviews = false, maxReviews = 10, onProgress } = opts;

  if (onProgress) onProgress('Fetching shop info...');
  const shopData = await apiGet('/api/v4/product/get_shop_info', { shopid: shopId });
  const shop = parseShopInfo(shopData.data);

  if (onProgress) onProgress('Fetching shop products...');
  const items = [];
  let newest = 0;
  const limit = 30;

  while (true) {
    if (maxItems > 0 && items.length >= maxItems) break;
    await sleep(REQUEST_DELAY);

    const data = await apiGet('/api/v4/search/search_items', {
      by: sortBy, limit, newest,
      order: 'desc', page_type: 'shop',
      scenario: 'PAGE_OTHERS',
      match_id: shopId,
      version: 2,
    });

    const resultItems = data.items || [];
    if (resultItems.length === 0) break;

    for (const ri of resultItems) {
      if (maxItems > 0 && items.length >= maxItems) break;
      const basic = ri.item_basic;
      items.push({
        item_id: basic.itemid,
        shop_id: basic.shopid,
        name: basic.name,
        price: basic.price / 100000,
        price_min: basic.price_min / 100000,
        price_max: basic.price_max / 100000,
        sold: basic.historical_sold || 0,
        stock: basic.stock || 0,
        rating: basic.item_rating?.rating_star || 0,
        image: basic.image ? `https://down-vn.img.susercontent.com/file/${basic.image}` : '',
        url: `https://${getDomain()}/product/${basic.shopid}/${basic.itemid}`,
      });
    }

    newest += resultItems.length;
    if (onProgress) onProgress(`Fetched ${items.length} products...`);
    if (resultItems.length < limit) break;
  }

  return { type: 'shop', shop, items, total_items: shop?.item_count || items.length };
}

// ── Category scraping ──

async function scrapeCategory(categoryId, opts = {}) {
  const { maxItems = 60, sortBy = 'relevancy', onProgress } = opts;

  if (onProgress) onProgress('Fetching category products...');
  const items = [];
  let newest = 0;
  const limit = 60;

  while (true) {
    if (maxItems > 0 && items.length >= maxItems) break;
    await sleep(REQUEST_DELAY);

    const data = await apiGet('/api/v4/search/search_items', {
      by: sortBy, limit, newest,
      match_id: categoryId,
      order: 'desc', page_type: 'search',
      scenario: 'PAGE_CATEGORY',
      version: 2,
    });

    const resultItems = data.items || [];
    if (resultItems.length === 0) break;

    for (const ri of resultItems) {
      if (maxItems > 0 && items.length >= maxItems) break;
      const basic = ri.item_basic;
      items.push({
        item_id: basic.itemid,
        shop_id: basic.shopid,
        name: basic.name,
        price: basic.price / 100000,
        sold: basic.historical_sold || 0,
        rating: basic.item_rating?.rating_star || 0,
        image: basic.image ? `https://down-vn.img.susercontent.com/file/${basic.image}` : '',
        url: `https://${getDomain()}/product/${basic.shopid}/${basic.itemid}`,
      });
    }

    newest += resultItems.length;
    if (onProgress) onProgress(`Fetched ${items.length} products...`);
    if (resultItems.length < limit) break;
  }

  return { type: 'category', category_id: categoryId, items, total_count: items.length };
}

// ── Batch product scraping (enrich search/shop results) ──

async function batchScrapeProducts(items, opts = {}) {
  const { includeReviews = true, maxReviews = 10, onProgress } = opts;
  const results = [];

  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    if (onProgress) onProgress(`Scraping product ${i + 1}/${items.length}: ${item.name?.substring(0, 40)}...`);
    try {
      await sleep(REQUEST_DELAY);
      const product = await scrapeProduct(item.shop_id, item.item_id, {
        includeReviews, maxReviews,
        onProgress: null,
      });
      results.push(product);
    } catch (e) {
      console.warn(`Failed to scrape product ${item.item_id}:`, e);
      results.push({ ...item, _error: e.message });
    }
  }

  return results;
}

// Export for use by content script and popup
if (typeof window !== 'undefined') {
  window.ShopeeAPI = {
    detectLink, scrapeProduct, scrapeSearch, scrapeShop,
    scrapeCategory, batchScrapeProducts, fetchAllReviews,
    getDomain, SHOPEE_DOMAINS,
  };
}
