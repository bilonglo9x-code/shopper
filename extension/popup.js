/**
 * Popup script - handles UI interactions and orchestrates scraping.
 */

let currentPageInfo = null;
let scrapedData = null;
let isRunning = false;

// ── UI helpers ──

const $ = (sel) => document.querySelector(sel);
const show = (el) => el.classList.add('active');
const hide = (el) => el.classList.remove('active');

function showError(msg) {
  const el = $('#errorMessage');
  el.textContent = msg;
  show(el);
}

function hideError() {
  hide($('#errorMessage'));
}

function setProgress(text, pct = -1) {
  show($('#progressSection'));
  $('#progressText').textContent = text;
  if (pct >= 0) {
    $('#progressBar').style.width = `${Math.min(pct, 100)}%`;
  }
}

function hideProgress() {
  hide($('#progressSection'));
}

function updatePageInfo(info) {
  currentPageInfo = info;
  const badge = $('#pageBadge');
  const text = $('#pageText');

  badge.className = `badge badge-${info.type}`;
  badge.textContent = info.type.toUpperCase();

  switch (info.type) {
    case 'product':
      text.textContent = `Product: shop=${info.shopId}, item=${info.itemId}`;
      break;
    case 'search':
      text.textContent = `Search: "${info.keyword}"`;
      break;
    case 'shop':
      text.textContent = info.shopId ? `Shop ID: ${info.shopId}` : `Shop: ${info.username}`;
      break;
    case 'category':
      text.textContent = `Category ID: ${info.categoryId}`;
      break;
    default:
      text.textContent = 'Not a recognized Shopee page';
  }
}

function showResults(data) {
  scrapedData = data;
  const section = $('#resultsSection');
  const summary = $('#resultSummary');
  show(section);

  let html = '';
  if (data.type === 'search') {
    html = `
      <div class="stat"><span>Keyword</span><span class="stat-value">${data.keyword}</span></div>
      <div class="stat"><span>Total Results</span><span class="stat-value">${(data.total_count || 0).toLocaleString()}</span></div>
      <div class="stat"><span>Items Scraped</span><span class="stat-value">${data.items.length}</span></div>
    `;
  } else if (data.type === 'shop') {
    html = `
      <div class="stat"><span>Shop</span><span class="stat-value">${data.shop?.name || 'N/A'}</span></div>
      <div class="stat"><span>Followers</span><span class="stat-value">${(data.shop?.follower_count || 0).toLocaleString()}</span></div>
      <div class="stat"><span>Items Scraped</span><span class="stat-value">${data.items.length}</span></div>
    `;
  } else if (data.type === 'category') {
    html = `
      <div class="stat"><span>Category ID</span><span class="stat-value">${data.category_id}</span></div>
      <div class="stat"><span>Items Scraped</span><span class="stat-value">${data.items.length}</span></div>
    `;
  } else {
    // Single product
    html = `
      <div class="stat"><span>Product</span><span class="stat-value">${(data.name || '').substring(0, 30)}...</span></div>
      <div class="stat"><span>Price</span><span class="stat-value">${data.price?.price_min?.toLocaleString() || data.price?.price?.toLocaleString() || 'N/A'}</span></div>
      <div class="stat"><span>Sold</span><span class="stat-value">${(data.sold || 0).toLocaleString()}</span></div>
      <div class="stat"><span>Rating</span><span class="stat-value">${data.rating?.rating_star?.toFixed(1) || 'N/A'}/5</span></div>
      <div class="stat"><span>Reviews</span><span class="stat-value">${data.reviews?.length || 0}</span></div>
      <div class="stat"><span>Images</span><span class="stat-value">${data.images?.length || 0}</span></div>
      <div class="stat"><span>Variants</span><span class="stat-value">${data.models?.length || 0}</span></div>
    `;

    if (data.reviews?.length > 0) {
      $('#btnExportReviews').style.display = '';
    }
  }

  if (data.items) {
    const totalReviews = data.items.reduce((sum, p) => sum + (p.reviews?.length || 0), 0);
    if (totalReviews > 0) {
      html += `<div class="stat"><span>Total Reviews</span><span class="stat-value">${totalReviews}</span></div>`;
      $('#btnExportReviews').style.display = '';
    }
  }

  summary.innerHTML = html;
}

function setButtonsDisabled(disabled) {
  isRunning = disabled;
  $('#btnScrape').disabled = disabled;
  $('#btnScrapeAll').disabled = disabled;
  $('#btnManualScrape').disabled = disabled;
}

// ── Scraping logic ──

async function runInPage(funcCode, args = []) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  // First inject the API library
  await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    files: ['lib/shopee-api.js'],
    world: 'MAIN',
  });

  // Then run the function
  const results = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: funcCode,
    args: args,
    world: 'MAIN',
  });

  return results[0]?.result;
}

async function scrapeCurrentPage(deep = false) {
  if (!currentPageInfo || currentPageInfo.type === 'unknown') {
    showError('Not a recognized Shopee page. Use the Manual Input tab.');
    return;
  }

  hideError();
  hide($('#resultsSection'));
  setButtonsDisabled(true);

  const maxItems = parseInt($('#maxItems').value) || 0;
  const includeReviews = $('#includeReviews').checked;
  const maxReviews = parseInt($('#maxReviews').value) || 50;
  const sortBy = $('#sortBy').value;

  try {
    let result;

    if (currentPageInfo.type === 'product') {
      setProgress('Scraping product...', 10);
      result = await runInPage(
        async (shopId, itemId, opts) => {
          return await window.ShopeeAPI.scrapeProduct(shopId, itemId, opts);
        },
        [currentPageInfo.shopId, currentPageInfo.itemId, { includeReviews, maxReviews }]
      );
      setProgress('Done!', 100);

    } else if (currentPageInfo.type === 'search') {
      setProgress(`Searching: "${currentPageInfo.keyword}"...`, 10);
      result = await runInPage(
        async (keyword, opts) => {
          return await window.ShopeeAPI.scrapeSearch(keyword, opts);
        },
        [currentPageInfo.keyword, { maxItems, sortBy }]
      );

      if (deep && result?.items?.length > 0) {
        setProgress('Deep scraping products...', 30);
        const enriched = await runInPage(
          async (items, opts) => {
            return await window.ShopeeAPI.batchScrapeProducts(items, opts);
          },
          [result.items, { includeReviews, maxReviews }]
        );
        result.items = enriched;
      }
      setProgress('Done!', 100);

    } else if (currentPageInfo.type === 'shop') {
      setProgress('Scraping shop...', 10);
      result = await runInPage(
        async (shopId, opts) => {
          return await window.ShopeeAPI.scrapeShop(shopId, opts);
        },
        [currentPageInfo.shopId, { maxItems, sortBy }]
      );

      if (deep && result?.items?.length > 0) {
        setProgress('Deep scraping products...', 30);
        const enriched = await runInPage(
          async (items, opts) => {
            return await window.ShopeeAPI.batchScrapeProducts(items, opts);
          },
          [result.items, { includeReviews, maxReviews }]
        );
        result.items = enriched;
      }
      setProgress('Done!', 100);

    } else if (currentPageInfo.type === 'category') {
      setProgress('Scraping category...', 10);
      result = await runInPage(
        async (categoryId, opts) => {
          return await window.ShopeeAPI.scrapeCategory(categoryId, opts);
        },
        [currentPageInfo.categoryId, { maxItems, sortBy }]
      );

      if (deep && result?.items?.length > 0) {
        setProgress('Deep scraping products...', 30);
        const enriched = await runInPage(
          async (items, opts) => {
            return await window.ShopeeAPI.batchScrapeProducts(items, opts);
          },
          [result.items, { includeReviews, maxReviews }]
        );
        result.items = enriched;
      }
      setProgress('Done!', 100);
    }

    if (result) {
      showResults(result);
    }
  } catch (e) {
    showError(e.message || 'Scraping failed');
    console.error('Scrape error:', e);
  } finally {
    setButtonsDisabled(false);
    setTimeout(hideProgress, 2000);
  }
}

function detectLinkLocal(url) {
  const patterns = {
    product: [/-i\.(\d+)\.(\d+)/, /\/product\/(\d+)\/(\d+)/],
    shop: [/\/shop\/(\d+)/],
    category: [/-cat\.(\d+)/],
    search: [/\/search\?.*keyword=([^&]+)/],
  };

  for (const p of patterns.product) {
    const m = url.match(p);
    if (m) return { type: 'product', shopId: parseInt(m[1]), itemId: parseInt(m[2]) };
  }
  for (const p of patterns.category) {
    const m = url.match(p);
    if (m) return { type: 'category', categoryId: parseInt(m[1]) };
  }
  for (const p of patterns.search) {
    const m = url.match(p);
    if (m) return { type: 'search', keyword: decodeURIComponent(m[1].replace(/\+/g, ' ')) };
  }
  for (const p of patterns.shop) {
    const m = url.match(p);
    if (m) return { type: 'shop', shopId: parseInt(m[1]) };
  }
  return { type: 'search', keyword: url };
}

// ── Export handlers ──

function getExportFilename(ext) {
  if (!scrapedData) return `shopper_data.${ext}`;
  const ts = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);

  if (scrapedData.type === 'search') {
    return `shopee_search_${scrapedData.keyword?.replace(/\s+/g, '_').substring(0, 20)}_${ts}.${ext}`;
  } else if (scrapedData.type === 'shop') {
    return `shopee_shop_${scrapedData.shop?.name?.replace(/\s+/g, '_').substring(0, 20) || scrapedData.shop?.shop_id}_${ts}.${ext}`;
  } else if (scrapedData.type === 'category') {
    return `shopee_category_${scrapedData.category_id}_${ts}.${ext}`;
  } else {
    return `shopee_product_${scrapedData.item_id}_${ts}.${ext}`;
  }
}

function escapeCsvValue(v) {
  const s = String(v ?? '');
  return s.includes(',') || s.includes('"') || s.includes('\n') ? `"${s.replace(/"/g, '""')}"` : s;
}

function buildCsvString(rows) {
  if (rows.length === 0) return '';
  const headers = Object.keys(rows[0]);
  return [headers.join(','), ...rows.map(r => headers.map(h => escapeCsvValue(r[h])).join(','))].join('\n');
}

function triggerDownload(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  chrome.downloads.download({ url, filename, saveAs: true });
}

// ── Initialization ──

document.addEventListener('DOMContentLoaded', async () => {
  // Detect current page
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab?.url) {
      const isShopee = /shopee\.(vn|sg|co\.(id|th)|com\.(my|br|mx|co)|tw|ph|cl)/.test(tab.url);

      if (isShopee) {
        const detected = detectLinkLocal(tab.url);
        updatePageInfo(detected);
        $('#shopeeContent').style.display = '';
        $('#notShopee').style.display = 'none';
      } else {
        updatePageInfo({ type: 'unknown' });
        $('#shopeeContent').style.display = 'none';
        $('#notShopee').style.display = '';
      }
    }
  } catch (e) {
    console.error('Detection error:', e);
    updatePageInfo({ type: 'unknown' });
  }

  // Tab switching
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      $(`#tab-${tab.dataset.tab}`).classList.add('active');
    });
  });

  // Scrape buttons
  $('#btnScrape').addEventListener('click', () => scrapeCurrentPage(false));
  $('#btnScrapeAll').addEventListener('click', () => scrapeCurrentPage(true));
  $('#btnManualScrape').addEventListener('click', async () => {
    const input = $('#manualInput').value.trim();
    if (!input) { showError('Enter a URL or keyword'); return; }
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const domain = $('#manualDomain').value;
    const detected = detectLinkLocal(input);
    let targetUrl;
    if (detected.type === 'product') {
      targetUrl = `https://${domain}/product/${detected.shopId}/${detected.itemId}`;
    } else if (detected.type === 'search') {
      targetUrl = `https://${domain}/search?keyword=${encodeURIComponent(detected.keyword)}`;
    } else if (input.startsWith('http')) {
      targetUrl = input;
    } else {
      targetUrl = `https://${domain}/search?keyword=${encodeURIComponent(input)}`;
    }
    await chrome.tabs.update(tab.id, { url: targetUrl });
    window.close();
  });

  // Export JSON
  $('#btnExportJSON').addEventListener('click', () => {
    if (!scrapedData) return;
    triggerDownload(JSON.stringify(scrapedData, null, 2), getExportFilename('json'), 'application/json');
  });

  // Export CSV
  $('#btnExportCSV').addEventListener('click', () => {
    if (!scrapedData) return;
    const items = scrapedData.items || [scrapedData];
    const rows = items.map(p => ({
      item_id: p.item_id || '',
      shop_id: p.shop_id || '',
      name: p.name || '',
      price: p.price?.price_min || p.price_min || p.price || '',
      price_max: p.price?.price_max || p.price_max || '',
      discount: p.price?.discount || p.discount || '',
      sold: p.sold || 0,
      stock: p.stock || 0,
      rating: p.rating?.rating_star || p.rating || '',
      reviews_count: p.reviews?.length || 0,
      url: p.url || '',
      shop_name: p.shop?.name || '',
    }));
    triggerDownload(buildCsvString(rows), getExportFilename('csv'), 'text/csv;charset=utf-8');
  });

  // Export Reviews CSV
  $('#btnExportReviews').addEventListener('click', () => {
    if (!scrapedData) return;
    const items = scrapedData.items || [scrapedData];
    const reviews = [];
    for (const p of items) {
      if (p.reviews) {
        for (const r of p.reviews) {
          reviews.push({
            item_id: p.item_id,
            product_name: p.name || '',
            author: r.author,
            rating: r.rating,
            comment: r.comment,
            time: r.time,
            model: r.model || '',
            likes: r.likes || 0,
            images: r.images?.length || 0,
            videos: r.videos?.length || 0,
          });
        }
      }
    }
    if (reviews.length === 0) return;
    triggerDownload(buildCsvString(reviews), getExportFilename('reviews.csv'), 'text/csv;charset=utf-8');
  });
});
