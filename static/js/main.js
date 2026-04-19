/* ══════════════════════════════════════════
   智能多维热榜 · 前端主逻辑 v3.0
   ══════════════════════════════════════════ */

// ── 状态 ──────────────────────────────────
const state = {
  currentDate: null,
  currentTimeMode: 'today',
  activeSource: 'all',
  activeTag: '全部',
  allItems: [],
  autoRefreshTimer: null,
  deferredPrompt: null,
  availableDates: [],
  weekDates: [],
  hiddenPlatforms: [],  // 用户隐藏的平台
  platformConfig: {},   // 平台配置
};

// ── DOM ───────────────────────────────────
const $ = (id) => document.getElementById(id);
const feedContainer = $('feedContainer');
const loadingState  = $('loadingState');
const errorState    = $('errorState');
const updateTime    = $('updateTime');
const statsCount    = $('statsCount');
const refreshBtn    = $('refreshBtn');
const shareBtn      = $('shareBtn');
const toast         = $('toast');
const searchInput   = $('searchInput');
const searchClear   = $('searchClear');
const installTopBtn = $('installTopBtn');
const modalOverlay  = $('modalOverlay');
const modalCard     = $('modalCard');
const modalClose    = $('modalClose');
const modalRank     = $('modalRank');
const modalTitle    = $('modalTitle');
const modalTags     = $('modalTags');
const modalSummary  = $('modalSummary');
const modalMeta     = $('modalMeta');
const modalLink     = $('modalLink');
const installOverlay = $('installOverlay');
const installClose   = $('installClose');
const installSteps   = $('installSteps');
const installActionBtn = $('installActionBtn');
const settingsBtn    = $('settingsBtn');
const settingsOverlay = $('settingsOverlay');
const settingsClose   = $('settingsClose');
const settingsPlatforms = $('settingsPlatforms');
const settingsSaveBtn  = $('settingsSaveBtn');
const sourceTabs     = $('sourceTabs');
const tagStrip       = $('tagStrip');
const timeStrip      = $('timeStrip');
const datePillsInline = $('datePillsInline');

// ── 浏览器检测 ───────────────────────────────
function detectBrowser() {
  const ua = navigator.userAgent;
  const isWeChat = /MicroMessenger/i.test(ua);
  const isQQ = /\bQQ\b/i.test(ua) && !isWeChat;
  const isIOS = /iPhone|iPad|iPod/i.test(ua);
  const isAndroid = /Android/i.test(ua);
  const isSafari = /Safari/i.test(ua) && !/Chrome/i.test(ua) && !isWeChat;
  const isChrome = /Chrome/i.test(ua) && !isWeChat && !isQQ;
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches
    || navigator.standalone === true;
  return { isWeChat, isQQ, isIOS, isAndroid, isSafari, isChrome, isStandalone };
}

// ── PWA 安装引导 ─────────────────────────────
function showInstallGuide() {
  const browser = detectBrowser();
  if (browser.isStandalone) { showToast('已安装为APP，无需重复安装'); return; }

  let stepsHTML = '';
  let showActionBtn = false;

  if (browser.isWeChat) {
    stepsHTML = `
      <div class="install-step"><span class="install-step-num">1</span><div class="install-step-text">点击右上角 <strong>···</strong> 三个点<span class="step-hint">在微信顶部或底部菜单栏</span></div></div>
      <div class="install-step"><span class="install-step-num">2</span><div class="install-step-text">选择 <strong>「在浏览器中打开」</strong><span class="step-hint">选择 Safari（iOS）或 Chrome（Android）</span></div></div>
      <div class="install-step"><span class="install-step-num">3</span><div class="install-step-text">在浏览器中打开后，再点击安装按钮</div></div>
    `;
  } else if (browser.isIOS && browser.isSafari) {
    stepsHTML = `
      <div class="install-step"><span class="install-step-num">1</span><div class="install-step-text">点击底部 <strong>分享按钮</strong><span class="step-hint">方框里有个向上箭头的图标</span></div></div>
      <div class="install-step"><span class="install-step-num">2</span><div class="install-step-text">向下滑动，找到 <strong>「添加到主屏幕」</strong></div></div>
      <div class="install-step"><span class="install-step-num">3</span><div class="install-step-text">点击 <strong>「添加」</strong>，即可在桌面看到图标</div></div>
    `;
  } else if (browser.isAndroid && browser.isChrome) {
    if (state.deferredPrompt) { showActionBtn = true; }
    else {
      stepsHTML = `
        <div class="install-step"><span class="install-step-num">1</span><div class="install-step-text">点击浏览器右上角 <strong>菜单按钮</strong><span class="step-hint">三个竖点图标</span></div></div>
        <div class="install-step"><span class="install-step-num">2</span><div class="install-step-text">选择 <strong>「添加到主屏幕」</strong> 或 <strong>「安装应用」</strong></div></div>
        <div class="install-step"><span class="install-step-num">3</span><div class="install-step-text">点击 <strong>「安装」</strong>，桌面即可看到图标</div></div>
      `;
    }
  } else {
    if (state.deferredPrompt) { showActionBtn = true; }
    else {
      stepsHTML = `
        <div class="install-step"><span class="install-step-num">1</span><div class="install-step-text">点击浏览器地址栏右侧 <strong>安装图标</strong><span class="step-hint">或菜单中选择「安装每日热点」</span></div></div>
        <div class="install-step"><span class="install-step-num">2</span><div class="install-step-text">点击 <strong>「安装」</strong> 即可像APP一样使用</div></div>
      `;
    }
  }

  installSteps.innerHTML = stepsHTML;
  installActionBtn.style.display = showActionBtn ? 'flex' : 'none';
  installOverlay.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeInstallGuide() {
  installOverlay.classList.add('hidden');
  document.body.style.overflow = '';
}

async function doNativeInstall() {
  if (!state.deferredPrompt) return;
  state.deferredPrompt.prompt();
  const { outcome } = await state.deferredPrompt.userChoice;
  if (outcome === 'accepted') showToast('APP 安装成功！');
  state.deferredPrompt = null;
  closeInstallGuide();
}

// ── 日期工具 ───────────────────────────────
function toDateStr(d) { return d.toISOString().split('T')[0]; }

function formatTime(ts) {
  if (!ts) return '--:--';
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')} 更新`;
}

function formatHot(val) {
  if (!val || val === 0) return '';
  if (val >= 100000000) return `${(val/100000000).toFixed(1)}亿`;
  if (val >= 10000)     return `${Math.round(val/10000)}万`;
  return `${val}`;
}

// ── 平台配置 ───────────────────────────────
const defaultSourceConfig = {
  weibo:        { label: '微博',     color: '#E6162D' },
  baidu:        { label: '百度',     color: '#4E6EF2' },
  douyin:       { label: '抖音',     color: '#FE2C55' },
  kuaishou:     { label: '快手',     color: '#FF4906' },
  bilibili:     { label: 'B站',      color: '#00A1D6' },
  ithome:       { label: 'IT之家',   color: '#D63031' },
  sina_finance: { label: '新浪财经', color: '#F39C12' },
  pengpai:      { label: '澎湃新闻', color: '#2ECC71' },
};

function sourceDot(src) {
  const cfg = defaultSourceConfig[src] || { label: src, color: '#888' };
  return `<span class="source-tag"><span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:${cfg.color}"></span>${cfg.label}</span>`;
}

// ── 渲染平台 Tab ────────────────────────────
function renderSourceTabs() {
  let html = `<button class="tab active" data-source="all"><span class="tab-icon">🌐</span><span class="tab-label">全部</span></button>`;
  for (const [src, cfg] of Object.entries(defaultSourceConfig)) {
    if (state.hiddenPlatforms.includes(src)) continue;
    html += `<button class="tab" data-source="${src}"><span class="tab-icon" style="color:${cfg.color}">●</span><span class="tab-label">${cfg.label}</span></button>`;
  }
  sourceTabs.innerHTML = html;

  // 绑定事件
  sourceTabs.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', () => {
      sourceTabs.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.activeSource = btn.dataset.source;
      applyFilter();
    });
  });
}

// ── 渲染日期 pill（内联在时间条右侧） ──────
function renderDatePills() {
  const wd = ['日','一','二','三','四','五','六'];
  const today = toDateStr(new Date());
  const yesterday = toDateStr(new Date(Date.now() - 86400000));

  let html = '';
  state.weekDates.forEach(dateStr => {
    const d = new Date(dateStr + 'T00:00:00');
    const dayNum = d.getDate();
    const hasData = state.availableDates.includes(dateStr);
    const isActive = dateStr === state.currentDate && state.currentTimeMode === 'custom';

    let label = `${dayNum}日`;
    const classes = [
      'mini-pill',
      isActive ? 'mini-pill-active' : '',
      hasData ? 'has-data' : '',
    ].filter(Boolean).join(' ');

    html += `<button class="${classes}" data-date="${dateStr}" title="${d.getMonth()+1}月${dayNum}日 周${wd[d.getDay()]}">${label}</button>`;
  });
  datePillsInline.innerHTML = html;

  datePillsInline.querySelectorAll('.mini-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      state.currentTimeMode = 'custom';
      state.currentDate = btn.dataset.date;
      // 清除时间条按钮的active
      timeStrip.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
      renderDatePills();
      loadHotspots(state.currentDate);
    });
  });
}

// ── 渲染热点列表 ───────────────────────────
function renderList(items) {
  if (!items || items.length === 0) {
    const today = toDateStr(new Date());
    const isHistory = state.currentDate !== today;
    const emptyMsg = isHistory
      ? `<div style="font-size:36px;margin-bottom:12px">📋</div><div>该日暂无历史数据</div><div style="font-size:12px;margin-top:6px;opacity:0.6">历史数据随每日定时抓取自动积累</div>`
      : `<div style="font-size:36px;margin-bottom:12px">📭</div><div>暂无热点数据</div>`;
    feedContainer.innerHTML = `<div style="text-align:center;padding:60px 20px;color:var(--text-3)">${emptyMsg}</div>`;
    statsCount.textContent = '0 条';
    return;
  }
  statsCount.textContent = `${items.length} 条`;

  const listHTML = items.map((item, idx) => {
    const rk = idx === 0 ? 'top-1' : idx === 1 ? 'top-2' : idx === 2 ? 'top-3' : '';
    const cat = `cat-${item.category || '热点'}`;
    const hot = formatHot(item.hot_value);
    const summary = item.summary || '';
    const tagsHtml = renderItemTags(item.tags);

    return `<a class="hotspot-item" href="javascript:void(0)" onclick="openDetail(${idx})">
      <div class="rank-badge ${rk}">${item.rank || idx+1}</div>
      <div class="item-content">
        <div class="item-title">${escapeHtml(item.title)}</div>
        ${tagsHtml ? `<div class="item-tags">${tagsHtml}</div>` : ''}
        ${summary ? `<div class="item-summary">${escapeHtml(summary)}</div>` : ''}
        <div class="item-meta">
          ${sourceDot(item.source)}
          ${hot ? `<span class="hot-value">🔥 ${hot}</span>` : ''}
        </div>
      </div>
      <span class="category-pill ${cat}">${item.category || '热点'}</span>
    </a>`;
  }).join('');

  feedContainer.innerHTML = `<ul class="hotspot-list">${listHTML}</ul>`;
}

function renderItemTags(tagsStr) {
  if (!tagsStr) return '';
  let tags;
  try { tags = JSON.parse(tagsStr); } catch(e) { tags = tagsStr.split(','); }
  if (!Array.isArray(tags) || tags.length === 0) return '';
  return tags.map(t => `<span class="item-tag">${escapeHtml(t)}</span>`).join('');
}

function escapeHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── 详情弹窗 ───────────────────────────────
function getFilteredItems() {
  let items = state.allItems;
  const src = state.activeSource;
  if (src !== 'all') items = items.filter(i => i.source === src);
  const tag = state.activeTag;
  if (tag !== '全部') {
    items = items.filter(i => {
      let itemTags = [];
      try { itemTags = JSON.parse(i.tags || '[]'); } catch(e) { itemTags = []; }
      return itemTags.includes(tag) || (i.category || '') === tag;
    });
  }
  return items;
}

function openDetail(idx) {
  const items = getFilteredItems();
  const item = items[idx];
  if (!item) return;

  modalRank.textContent = `#${item.rank || idx+1}`;
  modalTitle.textContent = item.title || '';

  // 标签
  let tagsHTML = '';
  const cat = item.category || '热点';
  tagsHTML += `<span class="category-pill cat-${cat}" style="font-size:12px">${cat}</span>`;
  if (item.tags) {
    let kws = item.tags;
    try { kws = JSON.parse(kws); } catch(e) { kws = kws.split(','); }
    if (Array.isArray(kws)) {
      kws.forEach(k => { tagsHTML += `<span class="modal-tag">${escapeHtml(k)}</span>`; });
    }
  }
  if (item.keywords) {
    let kws = item.keywords;
    try { kws = JSON.parse(kws); } catch(e) { kws = kws.split(','); }
    if (Array.isArray(kws)) {
      kws.forEach(k => { if (!tagsHTML.includes(escapeHtml(k))) tagsHTML += `<span class="modal-tag">${escapeHtml(k)}</span>`; });
    }
  }
  modalTags.innerHTML = tagsHTML;

  modalSummary.innerHTML = item.summary || '暂无摘要';

  let metaHTML = sourceDot(item.source);
  if (item.hot_value) metaHTML += `<span class="hot-value">🔥 ${formatHot(item.hot_value)}</span>`;
  modalMeta.innerHTML = metaHTML;

  modalLink.href = item.url || '#';
  modalLink.style.display = item.url ? '' : 'none';

  modalOverlay.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  modalOverlay.classList.add('hidden');
  document.body.style.overflow = '';
}

// ── 筛选 ───────────────────────────────────
function applyFilter() {
  const filtered = getFilteredItems();
  renderList(filtered);
}

// ── 搜索 ───────────────────────────────────
function handleSearch() {
  const q = searchInput.value.trim().toLowerCase();
  searchClear.classList.toggle('hidden', !q);
  if (!q) { applyFilter(); return; }
  const filtered = state.allItems.filter(i =>
    (i.title || '').toLowerCase().includes(q) ||
    (i.summary || '').toLowerCase().includes(q) ||
    (i.category || '').includes(q)
  );
  renderList(filtered);
}

// ── 带超时的 fetch ──────────────────────────
async function fetchWithTimeout(url, timeout = 10000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const res = await fetch(url, { signal: controller.signal });
    clearTimeout(timer);
    return res;
  } catch (e) {
    clearTimeout(timer);
    throw e;
  }
}

// ── 加载数据 ───────────────────────────────
async function loadHotspots(dateStr, silent = false) {
  if (!silent) {
    loadingState.classList.remove('hidden');
    errorState.classList.add('hidden');
    feedContainer.innerHTML = '';
  }
  try {
    const source = state.activeSource !== 'all' ? state.activeSource : '';
    const tag = state.activeTag !== '全部' ? state.activeTag : '';
    let url = `/api/hotspots?date=${dateStr}`;
    if (source) url += `&source=${source}`;
    if (tag) url += `&tag=${tag}`;

    const res = await fetchWithTimeout(url, 12000);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.allItems = data.items || [];
    updateTime.textContent = formatTime(data.last_updated);
    loadingState.classList.add('hidden');
    errorState.classList.add('hidden');
    applyFilter();
  } catch (err) {
    console.error('加载失败:', err);
    loadingState.classList.add('hidden');
    if (!silent) errorState.classList.remove('hidden');
  }
}

// ── 时间切换 ───────────────────────────────
function generateWeekDates() {
  const dates = [];
  const today = new Date();
  for (let i = 0; i < 7; i++) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    dates.push(toDateStr(d));
  }
  return dates;
}

async function fetchAvailableDates() {
  try {
    const res = await fetch('/api/dates?limit=7');
    if (!res.ok) return [];
    const data = await res.json();
    return data.dates || [];
  } catch (e) { return []; }
}

function setTimeMode(mode) {
  state.currentTimeMode = mode;
  const today = toDateStr(new Date());

  // 更新时间条按钮样式
  timeStrip.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
  const activeBtn = timeStrip.querySelector(`.time-btn[data-time="${mode}"]`);
  if (activeBtn) activeBtn.classList.add('active');

  // 计算目标日期
  let targetDate;
  switch (mode) {
    case 'today': targetDate = today; break;
    case 'yesterday': targetDate = toDateStr(new Date(Date.now() - 86400000)); break;
    case 'day_before': targetDate = toDateStr(new Date(Date.now() - 2*86400000)); break;
    case 'week': targetDate = 'week'; break;
    default: targetDate = today;
  }

  state.currentDate = targetDate === 'week' ? today : targetDate;
  renderDatePills();
  loadHotspots(targetDate);
}

// ── 平台设置弹窗 ────────────────────────────
function showSettings() {
  let html = '';
  for (const [src, cfg] of Object.entries(defaultSourceConfig)) {
    const checked = !state.hiddenPlatforms.includes(src) ? 'checked' : '';
    html += `
      <label class="platform-toggle">
        <span class="platform-dot" style="background:${cfg.color}"></span>
        <span class="platform-name">${cfg.label}</span>
        <input type="checkbox" data-source="${src}" ${checked} />
        <span class="toggle-slider"></span>
      </label>
    `;
  }
  settingsPlatforms.innerHTML = html;
  settingsOverlay.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeSettings() {
  settingsOverlay.classList.add('hidden');
  document.body.style.overflow = '';
}

function saveSettings() {
  const checkboxes = settingsPlatforms.querySelectorAll('input[type="checkbox"]');
  const hidden = [];
  checkboxes.forEach(cb => {
    if (!cb.checked) hidden.push(cb.dataset.source);
  });
  state.hiddenPlatforms = hidden;
  localStorage.setItem('hiddenPlatforms', JSON.stringify(hidden));

  // 如果当前选中的平台被隐藏了，切回全部
  if (hidden.includes(state.activeSource)) {
    state.activeSource = 'all';
  }

  renderSourceTabs();
  applyFilter();
  closeSettings();
  showToast('平台设置已保存');
}

// ── 自动刷新 ───────────────────────────────
function startAutoRefresh() {
  if (state.autoRefreshTimer) clearInterval(state.autoRefreshTimer);
  state.autoRefreshTimer = setInterval(() => {
    const today = toDateStr(new Date());
    if (state.currentDate === today) loadHotspots(today, true);
  }, 5 * 60 * 1000);
}

// ── Toast ──────────────────────────────────
function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2500);
}

// ── 分享 ───────────────────────────────────
function copyLink() {
  const url = window.location.href;
  const browser = detectBrowser();
  if (browser.isWeChat) {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(url).then(() => showToast('链接已复制，可粘贴分享'));
    } else { fallbackCopy(url); }
  } else if (navigator.share) {
    navigator.share({ title: 'PrenceYours 2026 · 智能多维热榜', url }).catch(() => {});
  } else if (navigator.clipboard) {
    navigator.clipboard.writeText(url).then(() => showToast('链接已复制！'));
  } else { fallbackCopy(url); }
}

function fallbackCopy(text) {
  const ta = document.createElement('textarea');
  ta.value = text; document.body.appendChild(ta);
  ta.select(); document.execCommand('copy'); document.body.removeChild(ta);
  showToast('链接已复制！');
}

// ── PWA 安装事件 ───────────────────────────
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  state.deferredPrompt = e;
});
window.addEventListener('appinstalled', () => {
  showToast('APP 安装成功！');
  state.deferredPrompt = null;
});

// ── 粒子背景 ───────────────────────────────
function initParticles() {
  const canvas = $('particleCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let w, h, particles = [];

  function resize() { w = canvas.width = window.innerWidth; h = canvas.height = window.innerHeight; }
  resize();
  window.addEventListener('resize', resize);

  const count = Math.min(60, Math.floor(window.innerWidth / 18));
  for (let i = 0; i < count; i++) {
    particles.push({
      x: Math.random() * w, y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.3, vy: (Math.random() - 0.5) * 0.3,
      r: Math.random() * 1.5 + 0.5, a: Math.random() * 0.3 + 0.05,
    });
  }

  function draw() {
    ctx.clearRect(0, 0, w, h);
    for (const p of particles) {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0) p.x = w; if (p.x > w) p.x = 0;
      if (p.y < 0) p.y = h; if (p.y > h) p.y = 0;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(108,99,255,${p.a})`;
      ctx.fill();
    }
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = dx * dx + dy * dy;
        if (dist < 12000) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(108,99,255,${0.06 * (1 - dist / 12000)})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(draw);
  }
  draw();
}

// ── 事件绑定 ───────────────────────────────

// 时间条按钮
timeStrip.querySelectorAll('.time-btn').forEach(btn => {
  btn.addEventListener('click', () => setTimeMode(btn.dataset.time));
});

// 标签筛选按钮
tagStrip.querySelectorAll('.tag-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    tagStrip.querySelectorAll('.tag-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.activeTag = btn.dataset.tag;
    applyFilter();
  });
});

refreshBtn.addEventListener('click', () => {
  refreshBtn.classList.add('spinning');
  fetch('/api/refresh', { method: 'POST' })
    .then(res => res.json())
    .then(data => {
      showToast('刷新已触发');
      // 等待3秒后自动加载新数据
      setTimeout(() => {
        loadHotspots(state.currentDate, true)
          .finally(() => refreshBtn.classList.remove('spinning'));
      }, 3000);
    })
    .catch(() => { showToast('刷新失败，请重试'); refreshBtn.classList.remove('spinning'); });
});

shareBtn.addEventListener('click', copyLink);
installTopBtn.addEventListener('click', showInstallGuide);
installClose.addEventListener('click', closeInstallGuide);
installOverlay.addEventListener('click', (e) => { if (e.target === installOverlay) closeInstallGuide(); });
installActionBtn.addEventListener('click', doNativeInstall);

settingsBtn.addEventListener('click', showSettings);
settingsClose.addEventListener('click', closeSettings);
settingsOverlay.addEventListener('click', (e) => { if (e.target === settingsOverlay) closeSettings(); });
settingsSaveBtn.addEventListener('click', saveSettings);

searchInput.addEventListener('input', handleSearch);
searchClear.addEventListener('click', () => { searchInput.value = ''; searchClear.classList.add('hidden'); applyFilter(); });

modalClose.addEventListener('click', closeModal);
modalOverlay.addEventListener('click', (e) => { if (e.target === modalOverlay) closeModal(); });

document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { closeModal(); closeInstallGuide(); closeSettings(); } });

// ── 版本更新检测 ─────────────────────────────
let _currentVersion = null;
async function checkVersionUpdate() {
  try {
    const res = await fetch('/api/version');
    if (!res.ok) return;
    const data = await res.json();
    const newVer = data.version;
    if (!_currentVersion) { _currentVersion = newVer; return; }
    if (_currentVersion !== newVer) {
      _currentVersion = newVer;
      if ('serviceWorker' in navigator) {
        const reg = await navigator.serviceWorker.getRegistration();
        if (reg) reg.update();
      }
      showToast('有新版本，已自动更新');
      setTimeout(() => location.reload(), 1500);
    }
  } catch (e) {}
}

// ── 初始化 ─────────────────────────────────
(async function init() {
  // 从localStorage加载隐藏平台
  try {
    const saved = localStorage.getItem('hiddenPlatforms');
    if (saved) state.hiddenPlatforms = JSON.parse(saved);
  } catch(e) {}

  state.weekDates = generateWeekDates();
  state.currentDate = toDateStr(new Date());

  // 并行加载：dates和hotspots同时请求
  renderSourceTabs();
  const [dates] = await Promise.all([
    fetchAvailableDates(),
    (async () => { setTimeMode('today'); })()  // 这会触发loadHotspots
  ]);
  state.availableDates = dates;
  renderDatePills();

  startAutoRefresh();
  initParticles();

  checkVersionUpdate();
  setInterval(checkVersionUpdate, 3 * 60 * 1000);
  setInterval(async () => {
    state.availableDates = await fetchAvailableDates();
    renderDatePills();
  }, 10 * 60 * 1000);
})();
