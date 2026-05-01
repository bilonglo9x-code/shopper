/**
 * Content script - detects current Shopee page and runs scraping in page context.
 */

function detectCurrentPage() {
  const url = location.href;
  const patterns = {
    product: [/-i\.(\d+)\.(\d+)/, /\/product\/(\d+)\/(\d+)/],
    shop: [/\/shop\/(\d+)/],
    category: [/-cat\.(\d+)/],
    search: [/\/search\?.*keyword=([^&]+)/],
  };

  for (const p of patterns.product) {
    const m = url.match(p);
    if (m) return { type: 'product', shopId: parseInt(m[1]), itemId: parseInt(m[2]), url };
  }
  for (const p of patterns.category) {
    const m = url.match(p);
    if (m) return { type: 'category', categoryId: parseInt(m[1]), url };
  }
  for (const p of patterns.search) {
    const m = url.match(p);
    if (m) return { type: 'search', keyword: decodeURIComponent(m[1].replace(/\+/g, ' ')), url };
  }
  for (const p of patterns.shop) {
    const m = url.match(p);
    if (m) return { type: 'shop', shopId: parseInt(m[1]), url };
  }

  return { type: 'unknown', url };
}

// Inject shopee-api.js into page context via script tag
function injectScript() {
  return new Promise((resolve) => {
    if (document.getElementById('shopper-api-script')) {
      resolve();
      return;
    }
    const script = document.createElement('script');
    script.id = 'shopper-api-script';
    script.src = chrome.runtime.getURL('lib/shopee-api.js');
    script.onload = () => resolve();
    document.head.appendChild(script);
  });
}

// Execute a ShopeeAPI function in page context via custom event
let requestId = 0;
const pendingRequests = new Map();

function callShopeeAPI(funcName, args) {
  return new Promise((resolve, reject) => {
    const id = ++requestId;
    pendingRequests.set(id, { resolve, reject });

    // Dispatch custom event to page context
    window.dispatchEvent(new CustomEvent('shopper-api-call', {
      detail: { id, funcName, args },
    }));

    // Timeout after 120s
    setTimeout(() => {
      if (pendingRequests.has(id)) {
        pendingRequests.delete(id);
        reject(new Error('API call timed out'));
      }
    }, 120000);
  });
}

// Listen for results from page context
window.addEventListener('shopper-api-result', (event) => {
  const { id, result, error } = event.detail;
  const pending = pendingRequests.get(id);
  if (pending) {
    pendingRequests.delete(id);
    if (error) {
      pending.reject(new Error(error));
    } else {
      pending.resolve(result);
    }
  }
});

// Inject the bridge script that listens in page context
function injectBridge() {
  if (document.getElementById('shopper-bridge-script')) {
    return;
  }
  const bridgeScript = document.createElement('script');
  bridgeScript.id = 'shopper-bridge-script';
  bridgeScript.textContent = `
    window.addEventListener('shopper-api-call', async (event) => {
      const { id, funcName, args } = event.detail;
      try {
        const api = window.ShopeeAPI;
        if (!api) throw new Error('ShopeeAPI not loaded');
        const func = api[funcName];
        if (!func) throw new Error('Unknown function: ' + funcName);
        const result = await func(...args);
        window.dispatchEvent(new CustomEvent('shopper-api-result', {
          detail: { id, result },
        }));
      } catch (e) {
        window.dispatchEvent(new CustomEvent('shopper-api-result', {
          detail: { id, error: e.message },
        }));
      }
    });
  `;
  document.head.appendChild(bridgeScript);
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'detectPage') {
    sendResponse(detectCurrentPage());
    return true;
  }

  if (msg.action === 'scrape') {
    (async () => {
      try {
        await injectScript();
        await new Promise(r => setTimeout(r, 100));
        injectBridge();
        await new Promise(r => setTimeout(r, 100));
        const result = await callShopeeAPI(msg.funcName, msg.args);
        sendResponse({ success: true, data: result });
      } catch (e) {
        sendResponse({ success: false, error: e.message });
      }
    })();
    return true; // async response
  }
});

// Notify that content script is ready
chrome.runtime.sendMessage({ action: 'contentReady', page: detectCurrentPage() });
