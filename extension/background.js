/**
 * Background service worker - handles long-running scrape tasks.
 */

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'contentReady') {
    // Content script loaded on a Shopee page
    chrome.action.setBadgeBackgroundColor({ color: '#EE4D2D' });
    if (msg.page?.type && msg.page.type !== 'unknown') {
      chrome.action.setBadgeText({
        text: msg.page.type.charAt(0).toUpperCase(),
        tabId: sender.tab?.id,
      });
    }
  }
});

// Handle download requests from popup
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'download') {
    const blob = new Blob([msg.content], { type: msg.mimeType || 'application/json' });
    const reader = new FileReader();
    reader.onload = () => {
      chrome.downloads.download({
        url: reader.result,
        filename: msg.filename || 'shopper_data.json',
        saveAs: true,
      }, (downloadId) => {
        sendResponse({ downloadId });
      });
    };
    reader.readAsDataURL(blob);
    return true;
  }
});
