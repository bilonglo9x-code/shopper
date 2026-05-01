/**
 * Export utilities - JSON and CSV download.
 */

function downloadFile(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function exportJSON(data, filename = 'shopper_data.json') {
  const json = JSON.stringify(data, null, 2);
  downloadFile(json, filename, 'application/json');
  return json.length;
}

function flattenProduct(p) {
  return {
    item_id: p.item_id,
    shop_id: p.shop_id,
    name: p.name,
    description: (p.description || '').substring(0, 500),
    brand: p.brand || '',
    url: p.url,
    price: p.price?.price || p.price || '',
    price_min: p.price?.price_min || p.price_min || '',
    price_max: p.price?.price_max || p.price_max || '',
    price_before_discount: p.price?.price_before_discount || '',
    discount: p.price?.discount || p.discount || '',
    currency: p.price?.currency || 'VND',
    rating_star: p.rating?.rating_star || p.rating || '',
    sold: p.sold || 0,
    stock: p.stock || 0,
    view_count: p.view_count || '',
    liked_count: p.liked_count || '',
    created_at: p.ctime || '',
    condition: p.condition || '',
    images_count: p.images?.length || 0,
    video: p.video || '',
    variants_count: p.models?.length || 0,
    attributes_count: p.attributes?.length || 0,
    reviews_count: p.reviews?.length || 0,
    shop_name: p.shop?.name || '',
    shop_rating: p.shop?.rating_star || '',
    shop_followers: p.shop?.follower_count || '',
    shop_location: p.shop?.location || p.location || '',
  };
}

function flattenReview(r, productName, itemId) {
  return {
    item_id: itemId,
    product_name: productName,
    author: r.author,
    rating: r.rating,
    comment: r.comment,
    time: r.time,
    model: r.model || '',
    likes: r.likes || 0,
    images_count: r.images?.length || 0,
    videos_count: r.videos?.length || 0,
  };
}

function toCSV(rows) {
  if (rows.length === 0) return '';
  const headers = Object.keys(rows[0]);
  const escape = (val) => {
    const str = String(val ?? '');
    if (str.includes(',') || str.includes('"') || str.includes('\n')) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  };
  const lines = [headers.join(',')];
  for (const row of rows) {
    lines.push(headers.map(h => escape(row[h])).join(','));
  }
  return lines.join('\n');
}

function exportCSV(data, filename = 'shopper_data.csv') {
  let rows;
  if (Array.isArray(data)) {
    rows = data.map(p => flattenProduct(p));
  } else if (data.type === 'search' || data.type === 'category') {
    rows = data.items.map(p => flattenProduct(p));
  } else if (data.type === 'shop') {
    rows = data.items.map(p => flattenProduct(p));
  } else {
    rows = [flattenProduct(data)];
  }

  const csv = toCSV(rows);
  downloadFile(csv, filename, 'text/csv;charset=utf-8');
  return rows.length;
}

function exportReviewsCSV(data, filename = 'shopper_reviews.csv') {
  const reviews = [];
  const products = Array.isArray(data) ? data : (data.items || [data]);

  for (const p of products) {
    if (p.reviews) {
      for (const r of p.reviews) {
        reviews.push(flattenReview(r, p.name, p.item_id));
      }
    }
  }

  if (reviews.length === 0) return 0;
  const csv = toCSV(reviews);
  downloadFile(csv, filename, 'text/csv;charset=utf-8');
  return reviews.length;
}

if (typeof window !== 'undefined') {
  window.ShopeeExporter = { exportJSON, exportCSV, exportReviewsCSV, downloadFile };
}
