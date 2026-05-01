/* ── Shopper Web UI ── */

const API = '';  // Same origin

// ── Navigation ──

function navigateTo(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  document.querySelector(`[data-page="${page}"]`).classList.add('active');
  if (page === 'dashboard') refreshDashboard();
  if (page === 'tasks') loadTasks();
  if (page === 'affiliate') checkAffiliateStatus();
}

document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', e => {
    e.preventDefault();
    navigateTo(item.dataset.page);
  });
});

// ── Toast Notifications ──

function toast(msg, type = 'info') {
  const container = document.getElementById('toastContainer');
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => { el.remove(); }, 4000);
}

// ── API Helpers ──

async function api(path, opts = {}) {
  const url = API + path;
  const config = { headers: { 'Content-Type': 'application/json' }, ...opts };
  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }
  const resp = await fetch(url, config);
  const data = await resp.json();
  if (!resp.ok) {
    throw new Error(data.detail || `HTTP ${resp.status}`);
  }
  return data;
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

function formatTime(iso) {
  if (!iso) return '--';
  const d = new Date(iso);
  return d.toLocaleString('vi-VN', { hour12: false });
}

function statusBadge(status) {
  return `<span class="badge badge-${status}">${status}</span>`;
}

// ── Server Status ──

async function checkServer() {
  const el = document.getElementById('serverStatus');
  try {
    const data = await api('/health');
    el.innerHTML = '<span class="status-dot online"></span><span>Server online</span>';
    return data;
  } catch {
    el.innerHTML = '<span class="status-dot offline"></span><span>Offline</span>';
    return null;
  }
}

// ── Dashboard ──

async function refreshDashboard() {
  const health = await checkServer();
  if (!health) return;

  document.getElementById('statAffiliate').textContent =
    health.affiliate_configured ? 'Đã kết nối' : 'Chưa cấu hình';

  try {
    const tasks = await api('/api/tasks?limit=100');
    document.getElementById('statTotalTasks').textContent = tasks.length;
    document.getElementById('statRunning').textContent =
      tasks.filter(t => t.status === 'running' || t.status === 'pending').length;
    document.getElementById('statCompleted').textContent =
      tasks.filter(t => t.status === 'completed').length;

    const recent = tasks.slice(0, 5);
    const el = document.getElementById('recentTasks');
    if (recent.length === 0) {
      el.innerHTML = '<div class="empty-state">Chưa có task nào</div>';
    } else {
      el.innerHTML = recent.map(t => taskItemHtml(t)).join('');
    }
  } catch {
    // Ignore task loading errors
  }
}

function taskItemHtml(t) {
  return `<div class="task-item" onclick="viewTask('${esc(t.task_id)}')">
    <span class="task-type">${esc(t.task_type || 'unknown')}</span>
    ${statusBadge(t.status)}
    <span class="task-url" title="${esc(t.url)}">${esc(t.url)}</span>
    <span class="task-time">${formatTime(t.created_at)}</span>
    <span class="task-actions">
      <button class="btn btn-sm btn-danger" onclick="event.stopPropagation(); deleteTask('${esc(t.task_id)}')" title="Xóa">&times;</button>
    </span>
  </div>`;
}

// ── Scraping ──

async function submitScrape(e) {
  e.preventDefault();
  const btn = document.getElementById('btnSubmitScrape');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Đang tạo task...';

  try {
    const body = getScrapeBody();
    const result = await api('/api/tasks', { method: 'POST', body });
    toast(`Task đã tạo: ${result.task_id}`, 'success');
    navigateTo('tasks');
  } catch (err) {
    toast('Lỗi: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg> Bắt đầu thu thập`;
  }
}

async function submitScrapeSync() {
  const btn = document.querySelector('.btn-secondary');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Đang thu thập...';

  try {
    const body = getScrapeBody();
    const result = await api('/api/scrape', { method: 'POST', body });
    document.getElementById('scrapeResultCard').style.display = '';
    const el = document.getElementById('scrapeResult');

    if (result.data) {
      window._lastScrapeResult = result.data;
      el.innerHTML = `
        <div style="margin-bottom:12px">
          <strong>Tổng items:</strong> ${result.total_items}
        </div>
        <pre class="code-block">${esc(JSON.stringify(result.data, null, 2))}</pre>
      `;
    } else {
      el.innerHTML = '<div class="empty-state">Không có dữ liệu</div>';
    }
    toast('Thu thập hoàn tất!', 'success');
  } catch (err) {
    toast('Lỗi: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Thu thập ngay (chờ kết quả)`;
  }
}

function getScrapeBody() {
  return {
    url: document.getElementById('scrapeUrl').value,
    domain: document.getElementById('scrapeDomain').value,
    max_items: parseInt(document.getElementById('scrapeMaxItems').value) || 0,
    include_reviews: document.getElementById('scrapeReviews').checked,
    max_reviews: parseInt(document.getElementById('scrapeMaxReviews').value) || 50,
    sort_by: document.getElementById('scrapeSortBy').value,
    generate_affiliate_links: document.getElementById('scrapeAffiliate').checked,
  };
}

function exportResult(format) {
  if (!window._lastScrapeResult) return;
  const data = window._lastScrapeResult;
  let blob, filename;
  if (format === 'json') {
    blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    filename = `shopper-result-${Date.now()}.json`;
  } else {
    const csv = jsonToCsv(data);
    blob = new Blob([csv], { type: 'text/csv' });
    filename = `shopper-result-${Date.now()}.csv`;
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

function jsonToCsv(data) {
  const items = Array.isArray(data) ? data : (data.items || [data]);
  if (items.length === 0) return '';
  const keys = Object.keys(items[0]).filter(k => typeof items[0][k] !== 'object');
  const rows = [keys.join(',')];
  for (const item of items) {
    rows.push(keys.map(k => {
      const v = item[k];
      if (v == null) return '';
      const s = String(v);
      return s.includes(',') || s.includes('"') || s.includes('\n')
        ? '"' + s.replace(/"/g, '""') + '"' : s;
    }).join(','));
  }
  return rows.join('\n');
}

// ── Tasks ──

async function loadTasks() {
  const filter = document.getElementById('taskFilter').value;
  const params = filter ? `?status=${filter}` : '';
  try {
    const tasks = await api('/api/tasks' + params);
    const el = document.getElementById('tasksList');
    if (tasks.length === 0) {
      el.innerHTML = '<div class="empty-state">Không có task nào</div>';
    } else {
      el.innerHTML = tasks.map(t => taskItemHtml(t)).join('');
    }
  } catch (err) {
    toast('Lỗi tải tasks: ' + err.message, 'error');
  }
}

async function viewTask(taskId) {
  try {
    const task = await api(`/api/tasks/${taskId}`);
    let resultHtml = '';
    if (task.status === 'completed' || task.status === 'failed') {
      try {
        const result = await api(`/api/tasks/${taskId}/result`);
        if (result.data) {
          resultHtml = `
            <h3 style="margin: 16px 0 8px">Dữ liệu</h3>
            <pre class="code-block">${esc(JSON.stringify(result.data, null, 2))}</pre>
          `;
        }
      } catch { /* Result not ready */ }
    }

    document.getElementById('taskModalBody').innerHTML = `
      <table class="data-table">
        <tr><td><strong>Task ID</strong></td><td>${esc(task.task_id)}</td></tr>
        <tr><td><strong>Trạng thái</strong></td><td>${statusBadge(task.status)}</td></tr>
        <tr><td><strong>Loại</strong></td><td>${esc(task.task_type || '--')}</td></tr>
        <tr><td><strong>URL</strong></td><td>${esc(task.url)}</td></tr>
        <tr><td><strong>Tạo lúc</strong></td><td>${formatTime(task.created_at)}</td></tr>
        <tr><td><strong>Hoàn thành</strong></td><td>${formatTime(task.completed_at)}</td></tr>
        <tr><td><strong>Tổng items</strong></td><td>${task.total_items}</td></tr>
        ${task.error ? `<tr><td><strong>Lỗi</strong></td><td style="color:var(--red)">${esc(task.error)}</td></tr>` : ''}
      </table>
      ${resultHtml}
    `;
    document.getElementById('taskModal').classList.add('active');
  } catch (err) {
    toast('Lỗi: ' + err.message, 'error');
  }
}

async function deleteTask(taskId) {
  if (!confirm('Xóa task này?')) return;
  try {
    await api(`/api/tasks/${taskId}`, { method: 'DELETE' });
    toast('Đã xóa task', 'success');
    loadTasks();
    refreshDashboard();
  } catch (err) {
    toast('Lỗi xóa: ' + err.message, 'error');
  }
}

function closeModal() {
  document.getElementById('taskModal').classList.remove('active');
}

// Close modal on outside click
document.getElementById('taskModal').addEventListener('click', e => {
  if (e.target === e.currentTarget) closeModal();
});

// ── Affiliate ──

async function checkAffiliateStatus() {
  try {
    const data = await api('/api/affiliate/status');
    const badge = document.getElementById('affiliateBadge');
    if (data.configured) {
      badge.textContent = 'Đã kết nối';
      badge.className = 'badge badge-completed';
    } else {
      badge.textContent = 'Chưa cấu hình';
      badge.className = 'badge badge-failed';
    }
  } catch { /* ignore */ }
}

async function configAffiliate(e) {
  e.preventDefault();
  try {
    await api('/api/affiliate/config', {
      method: 'POST',
      body: {
        app_id: document.getElementById('affAppId').value,
        secret: document.getElementById('affSecret').value,
        region: document.getElementById('affRegion').value,
      },
    });
    toast('Đã cấu hình affiliate!', 'success');
    checkAffiliateStatus();
  } catch (err) {
    toast('Lỗi: ' + err.message, 'error');
  }
}

async function generateLinks(e) {
  e.preventDefault();
  const urlsText = document.getElementById('affUrls').value.trim();
  if (!urlsText) return toast('Nhập ít nhất 1 URL', 'error');

  const urls = urlsText.split('\n').map(u => u.trim()).filter(Boolean);
  const subIdsText = document.getElementById('affSubIds').value.trim();
  const sub_ids = subIdsText ? subIdsText.split(',').map(s => s.trim()) : null;

  try {
    const data = await api('/api/affiliate/links', {
      method: 'POST',
      body: { urls, sub_ids },
    });

    const resultEl = document.getElementById('affiliateLinksResult');
    resultEl.style.display = '';
    const tbody = document.querySelector('#linksTable tbody');
    tbody.innerHTML = data.links.map(l => `
      <tr>
        <td style="max-width:250px;overflow:hidden;text-overflow:ellipsis">${esc(l.original_url)}</td>
        <td><a href="${esc(l.affiliate_url)}" target="_blank">${esc(l.affiliate_url)}</a></td>
        <td><button class="btn btn-sm" onclick="navigator.clipboard.writeText('${esc(l.affiliate_url)}'); toast('Đã copy!', 'success')">Copy</button></td>
      </tr>
    `).join('');
    toast(`Đã tạo ${data.total} affiliate links!`, 'success');
  } catch (err) {
    toast('Lỗi: ' + err.message, 'error');
  }
}

async function searchProductOffers(e) {
  e.preventDefault();
  try {
    const data = await api('/api/affiliate/product-offers', {
      method: 'POST',
      body: {
        keyword: document.getElementById('offerKeyword').value || null,
        sort_type: parseInt(document.getElementById('offerSort').value),
        limit: parseInt(document.getElementById('offerLimit').value),
      },
    });

    const el = document.getElementById('productOffersResult');
    const nodes = data.productOfferV2?.nodes || [];
    if (nodes.length === 0) {
      el.innerHTML = '<div class="empty-state">Không tìm thấy sản phẩm nào</div>';
      return;
    }

    el.innerHTML = `
      <table class="data-table">
        <thead><tr>
          <th>Sản phẩm</th><th>Giá</th><th>Đã bán</th><th>Hoa hồng</th><th>Link</th>
        </tr></thead>
        <tbody>
          ${nodes.map(n => `<tr>
            <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis">${esc(n.productName || n.itemId)}</td>
            <td>${n.priceMin || '--'}</td>
            <td>${n.sales || 0}</td>
            <td style="color:var(--green);font-weight:600">${((parseFloat(n.commissionRate) || 0) * 100).toFixed(1)}%</td>
            <td>${n.offerLink ? `<a href="${esc(n.offerLink)}" target="_blank">Link</a>` : '--'}</td>
          </tr>`).join('')}
        </tbody>
      </table>
    `;
    toast(`Tìm thấy ${nodes.length} sản phẩm`, 'success');
  } catch (err) {
    toast('Lỗi: ' + err.message, 'error');
  }
}

// ── Link Detection ──

async function detectLink(e) {
  e.preventDefault();
  const url = document.getElementById('detectUrl').value;
  try {
    const data = await api('/api/detect?url=' + encodeURIComponent(url));
    const el = document.getElementById('detectResult');
    el.style.display = '';

    const fields = [
      { label: 'Loại', value: data.link_type, highlight: true },
      { label: 'Domain', value: data.domain || '--' },
      { label: 'Shop ID', value: data.shop_id || '--' },
      { label: 'Item ID', value: data.item_id || '--' },
      { label: 'Category ID', value: data.category_id || '--' },
      { label: 'Keyword', value: data.keyword || '--' },
    ];

    document.getElementById('detectResultGrid').innerHTML = fields.map(f => `
      <div class="detect-item">
        <div class="detect-item-label">${esc(f.label)}</div>
        <div class="detect-item-value" ${f.highlight ? 'style="color:var(--primary);font-size:1.2rem"' : ''}>${esc(String(f.value))}</div>
      </div>
    `).join('');

    toast('Nhận diện thành công!', 'success');
  } catch (err) {
    toast('Lỗi: ' + err.message, 'error');
  }
}

// ── Auto-refresh running tasks ──

let refreshInterval;

function startAutoRefresh() {
  if (refreshInterval) return;
  refreshInterval = setInterval(async () => {
    const activePage = document.querySelector('.page.active');
    if (activePage?.id === 'page-tasks') loadTasks();
    if (activePage?.id === 'page-dashboard') refreshDashboard();
  }, 5000);
}

// ── Init ──

checkServer();
refreshDashboard();
startAutoRefresh();
