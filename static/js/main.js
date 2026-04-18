/* ══════════════════════════════════════════
   每日热点 · 前端主逻辑 · 抖音风格
   ══════════════════════════════════════════ */

// ── 状态 ──────────────────────────────────
const state = {
  currentDate: null,
  activeSource: 'all',
  allItems: [],
  autoRefreshTimer: null,
  deferredPrompt: null,   // PWA 安装提示
  availableDates: [],     // 有数据的日期列表
  weekDates: [],          // 最近7天日期列表
};

// ── DOM ───────────────────────────────────
const $ = (id) => document.getElementById(id);
const feedContainer = $('feedContainer');
const loadingState  = $('loadingState');
const errorState    = $('errorState');
const dateLabel     = $('dateLabel');
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
const datePills     = $('datePills');

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

  // 已是 standalone 模式，不需要安装引导
  if (browser.isStandalone) {
    showToast('已安装为APP，无需重复安装');
    return;
  }

  let stepsHTML = '';
  let showActionBtn = false;

  if (browser.isWeChat) {
    // 微信内置浏览器：引导用系统浏览器打开
    stepsHTML = `
      <div class="install-step">
        <span class="install-step-num">1</span>
        <div class="install-step-text">
          点击右上角 <strong>···</strong> 三个点
          <span class="step-hint">在微信顶部或底部菜单栏</span>
        </div>
      </div>
      <div class="install-step">
        <span class="install-step-num">2</span>
        <div class="install-step-text">
          选择 <strong>「在浏览器中打开」</strong>
          <span class="step-hint">选择 Safari（iOS）或 Chrome（Android）</span>
        </div>
      </div>
      <div class="install-step">
        <span class="install-step-num">3</span>
        <div class="install-step-text">
          在浏览器中打开后，再点击安装按钮
        </div>
      </div>
    `;
  } else if (browser.isIOS && browser.isSafari) {
    // iOS Safari：添加到主屏幕
    stepsHTML = `
      <div class="install-step">
        <span class="install-step-num">1</span>
        <div class="install-step-text">
          点击底部 <strong>分享按钮</strong>
          <span class="step-hint">方框里有个向上箭头的图标</span>
        </div>
      </div>
      <div class="install-step">
        <span class="install-step-num">2</span>
        <div class="install-step-text">
          向下滑动，找到 <strong>「添加到主屏幕」</strong>
        </div>
      </div>
      <div class="install-step">
        <span class="install-step-num">3</span>
        <div class="install-step-text">
          点击 <strong>「添加」</strong>，即可在桌面看到每日热点图标
        </div>
      </div>
    `;
  } else if (browser.isAndroid && browser.isChrome) {
    // Android Chrome：优先用 beforeinstallprompt，否则手动引导
    if (state.deferredPrompt) {
      showActionBtn = true;
    } else {
      stepsHTML = `
        <div class="install-step">
          <span class="install-step-num">1</span>
          <div class="install-step-text">
            点击浏览器右上角 <strong>菜单按钮</strong>
            <span class="step-hint">三个竖点图标</span>
          </div>
        </div>
        <div class="install-step">
          <span class="install-step-num">2</span>
          <div class="install-step-text">
            选择 <strong>「添加到主屏幕」</strong> 或 <strong>「安装应用」</strong>
          </div>
        </div>
        <div class="install-step">
          <span class="install-step-num">3</span>
          <div class="install-step-text">
            点击 <strong>「安装」</strong>，桌面即可看到图标
          </div>
        </div>
      `;
    }
  } else if (browser.isQQ) {
    // QQ内置浏览器
    stepsHTML = `
      <div class="install-step">
        <span class="install-step-num">1</span>
        <div class="install-step-text">
          点击右上角 <strong>···</strong> 三个点
        </div>
      </div>
      <div class="install-step">
        <span class="install-step-num">2</span>
        <div class="install-step-text">
          选择 <strong>「在浏览器中打开」</strong>
        </div>
      </div>
      <div class="install-step">
        <span class="install-step-num">3</span>
        <div class="install-step-text">
          在浏览器中再点击安装按钮
        </div>
      </div>
    `;
  } else {
    // 桌面 Chrome/Edge 等
    if (state.deferredPrompt) {
      showActionBtn = true;
    } else {
      stepsHTML = `
        <div class="install-step">
          <span class="install-step-num">1</span>
          <div class="install-step-text">
            点击浏览器地址栏右侧 <strong>安装图标</strong>
            <span class="step-hint">或者菜单中选择「安装每日热点」</span>
          </div>
        </div>
        <div class="install-step">
          <span class="install-step-num">2</span>
          <div class="install-step-text">
            点击 <strong>「安装」</strong> 即可像APP一样使用
          </div>
        </div>
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

function formatDateLabel(dateStr) {
  const today     = toDateStr(new Date());
  const yesterday = toDateStr(new Date(Date.now() - 86400000));
  const d = new Date(dateStr + 'T00:00:00');
  const wd = ['日','一','二','三','四','五','六'];
  const base = `${d.getMonth()+1}月${d.getDate()}日 周${wd[d.getDay()]}`;
  if (dateStr === today)     return `今天 · ${base}`;
  if (dateStr === yesterday) return `昨天 · ${base}`;
  return base;
}

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
const sourceLabel = { weibo:'微博', baidu:'百度', zhihu:'知乎', douyin:'抖音', kuaishou:'快手' };
const sourceColor = { weibo:'#E6162D', baidu:'#4E6EF2', zhihu:'#0084FF', douyin:'#FE2C55', kuaishou:'#FF4906' };

function sourceDot(src) {
  const c = sourceColor[src] || '#888';
  const l = sourceLabel[src] || src;
  return `<span class="source-tag"><span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:${c}"></span>${l}</span>`;
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
    const url = item.url || '#';

    return `<a class="hotspot-item" href="javascript:void(0)" onclick="openDetail(${idx})">
      <div class="rank-badge ${rk}">${item.rank || idx+1}</div>
      <div class="item-content">
        <div class="item-title">${escapeHtml(item.title)}</div>
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

function escapeHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── 详情弹窗 ───────────────────────────────
function getFilteredItems() {
  const src = state.activeSource;
  return src === 'all' ? state.allItems : state.allItems.filter(i => i.source === src);
}

function openDetail(idx) {
  const items = getFilteredItems();
  const item = items[idx];
  if (!item) return;

  modalRank.textContent = `#${item.rank || idx+1}`;
  modalTitle.textContent = item.title || '';

  // 关键词标签
  let tagsHTML = '';
  const cat = item.category || '热点';
  tagsHTML += `<span class="category-pill cat-${cat}" style="font-size:12px">${cat}</span>`;
  if (item.keywords) {
    let kws = item.keywords;
    if (typeof kws === 'string') { try { kws = JSON.parse(kws); } catch(e) { kws = kws.split(','); } }
    if (Array.isArray(kws)) {
      kws.forEach(k => { tagsHTML += `<span class="modal-tag">${escapeHtml(k)}</span>`; });
    }
  }
  modalTags.innerHTML = tagsHTML;

  // 摘要
  const summaryText = item.summary || '暂无摘要';
  modalSummary.innerHTML = summaryText;

  // Meta
  let metaHTML = sourceDot(item.source);
  if (item.hot_value) metaHTML += `<span class="hot-value">🔥 ${formatHot(item.hot_value)}</span>`;
  modalMeta.innerHTML = metaHTML;

  // 链接
  modalLink.href = item.url || '#';
  if (!item.url) modalLink.style.display = 'none';
  else modalLink.style.display = '';

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

// ── 加载数据 ───────────────────────────────
async function loadHotspots(dateStr, silent = false) {
  if (!silent) {
    loadingState.classList.remove('hidden');
    errorState.classList.add('hidden');
    feedContainer.innerHTML = '';
  }
  try {
    const res = await fetch(`/api/hotspots?date=${dateStr}`);
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

// ── 日期切换 ───────────────────────────────

/** 生成最近7天的日期列表（从今天往前推6天） */
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

/** 获取有数据的日期列表 */
async function fetchAvailableDates() {
  try {
    const res = await fetch('/api/dates?limit=7');
    if (!res.ok) return [];
    const data = await res.json();
    return data.dates || [];
  } catch (e) {
    console.error('获取日期列表失败:', e);
    return [];
  }
}

/** 渲染7天日期pill */
function renderDatePills() {
  const wd = ['日','一','二','三','四','五','六'];
  const today = toDateStr(new Date());
  const yesterday = toDateStr(new Date(Date.now() - 86400000));

  let html = '';
  state.weekDates.forEach(dateStr => {
    const d = new Date(dateStr + 'T00:00:00');
    const dayNum = d.getDate();
    const weekDay = wd[d.getDay()];
    const hasData = state.availableDates.includes(dateStr);
    const isActive = dateStr === state.currentDate;
    const isToday = dateStr === today;
    const isYesterday = dateStr === yesterday;

    // 显示标签：今天/昨天/X日
    let label;
    if (isToday) label = '今天';
    else if (isYesterday) label = '昨天';
    else label = `${dayNum}日`;

    const classes = [
      'pill',
      isActive ? 'pill-active' : '',
      hasData ? 'has-data' : '',
      (!hasData && !isActive) ? 'pill-empty' : '',
    ].filter(Boolean).join(' ');

    html += `<button class="${classes}" data-date="${dateStr}" title="${d.getMonth()+1}月${dayNum}日 周${weekDay}">
      <span class="pill-dot"></span>${label}
    </button>`;
  });
  datePills.innerHTML = html;

  // 绑定pill点击事件
  datePills.querySelectorAll('.pill').forEach(btn => {
    btn.addEventListener('click', () => {
      const dateStr = btn.dataset.date;
      const hasData = state.availableDates.includes(dateStr);
      if (dateStr !== state.currentDate) {
        setDate(dateStr);
      }
    });
  });
}

function setDate(dateStr) {
  state.currentDate = dateStr;
  dateLabel.textContent = formatDateLabel(dateStr);
  renderDatePills();
  loadHotspots(dateStr);
}

function changeDate(delta) {
  const d = new Date(state.currentDate + 'T00:00:00');
  d.setDate(d.getDate() + delta);
  const nd = toDateStr(d);
  if (nd > toDateStr(new Date())) { showToast('已经是最新了'); return; }
  setDate(nd);
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
    // 微信内：提示复制链接
    if (navigator.clipboard) {
      navigator.clipboard.writeText(url).then(() => showToast('链接已复制，可粘贴分享'));
    } else {
      fallbackCopy(url);
    }
  } else if (navigator.share) {
    navigator.share({ title: 'PrenceYours 2026 · 实时热搜', url }).catch(() => {});
  } else if (navigator.clipboard) {
    navigator.clipboard.writeText(url).then(() => showToast('链接已复制！'));
  } else {
    fallbackCopy(url);
  }
}

function fallbackCopy(text) {
  const ta = document.createElement('textarea');
  ta.value = text; document.body.appendChild(ta);
  ta.select(); document.execCommand('copy');
  document.body.removeChild(ta);
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

  function resize() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize);

  const count = Math.min(60, Math.floor(window.innerWidth / 18));
  for (let i = 0; i < count; i++) {
    particles.push({
      x: Math.random() * w, y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      r: Math.random() * 1.5 + 0.5,
      a: Math.random() * 0.3 + 0.05,
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
    // 连线
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
$('prevDay').addEventListener('click', () => changeDate(-1));
$('nextDay').addEventListener('click', () => changeDate(1));

document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.activeSource = btn.dataset.source;
    applyFilter();
  });
});

refreshBtn.addEventListener('click', () => {
  refreshBtn.classList.add('spinning');
  fetch('/api/refresh', { method: 'POST' })
    .then(res => res.json())
    .then(data => {
      if (data.status === 'ok') {
        showToast('刷新成功');
        loadHotspots(state.currentDate);
      } else {
        showToast('刷新失败：' + (data.message || '未知错误'));
      }
    })
    .catch(() => showToast('刷新失败，请重试'))
    .finally(() => {
      setTimeout(() => refreshBtn.classList.remove('spinning'), 600);
    });
});

shareBtn.addEventListener('click', copyLink);

// 安装按钮（右上角常驻）
installTopBtn.addEventListener('click', showInstallGuide);
installClose.addEventListener('click', closeInstallGuide);
installOverlay.addEventListener('click', (e) => {
  if (e.target === installOverlay) closeInstallGuide();
});
installActionBtn.addEventListener('click', doNativeInstall);

searchInput.addEventListener('input', handleSearch);
searchClear.addEventListener('click', () => {
  searchInput.value = '';
  searchClear.classList.add('hidden');
  applyFilter();
});

modalClose.addEventListener('click', closeModal);
modalOverlay.addEventListener('click', (e) => {
  if (e.target === modalOverlay) closeModal();
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeModal();
    closeInstallGuide();
  }
});

// ── 版本更新检测 ─────────────────────────────
let _currentVersion = null;

async function checkVersionUpdate() {
  try {
    const res = await fetch('/api/version');
    if (!res.ok) return;
    const data = await res.json();
    const newVer = data.version;

    if (!_currentVersion) {
      _currentVersion = newVer;
      return;
    }

    if (_currentVersion !== newVer) {
      // 版本号变了，提示刷新并更新SW缓存
      _currentVersion = newVer;
      if ('serviceWorker' in navigator) {
        const reg = await navigator.serviceWorker.getRegistration();
        if (reg) {
          reg.update(); // 触发SW更新
        }
      }
      showToast('有新版本，已自动更新');
      setTimeout(() => location.reload(), 1500);
    }
  } catch (e) {
    // 静默失败
  }
}

// ── 初始化 ─────────────────────────────────
(async function init() {
  const today = toDateStr(new Date());
  state.weekDates = generateWeekDates();
  state.availableDates = await fetchAvailableDates();
  setDate(today);
  startAutoRefresh();
  initParticles();
  // 每3分钟检测一次版本更新
  checkVersionUpdate();
  setInterval(checkVersionUpdate, 3 * 60 * 1000);
  // 每10分钟刷新一次日期列表（检查哪些天有数据）
  setInterval(async () => {
    state.availableDates = await fetchAvailableDates();
    renderDatePills();
  }, 10 * 60 * 1000);
})();
