/* ═══════════════════════════════════════════════════════════
   RobaContest — Global JS  (main.js)
   Barcha sahifalarda ishlatiladi
   ═══════════════════════════════════════════════════════════ */

'use strict';

/* ═══════════════════════════════════════════════════════════
   CONFIG
═══════════════════════════════════════════════════════════ */
const RC = {
  API_BASE:    window.RC_API_BASE || 'http://localhost:8000/api',
  TOAST_DURATION: 3000,
  VERSION: '2.0.0',
};

/* ═══════════════════════════════════════════════════════════
   AUTH HELPERS
═══════════════════════════════════════════════════════════ */
const Auth = {
  getToken()       { return localStorage.getItem('auth_token') || ''; },
  getUser()        { try { return JSON.parse(localStorage.getItem('user_data') || 'null'); } catch { return null; } },
  setToken(t)      { localStorage.setItem('auth_token', t); },
  setUser(u)       { localStorage.setItem('user_data', JSON.stringify(u)); },
  clear()          { localStorage.removeItem('auth_token'); localStorage.removeItem('user_data'); },
  isLoggedIn()     { return !!this.getToken(); },

  /** Tokenni backend bilan tekshiradi. ok bo'lsa true qaytaradi */
  async verify() {
    const token = this.getToken();
    if (!token) return false;
    try {
      const res = await apiFetch('/verify', { method: 'GET' });
      return !!res;
    } catch {
      this.clear();
      return false;
    }
  },

  /** Login sahifasiga yo'naltiradi (agar allaqachon login sahifasida bo'lmasa) */
  redirectToLogin() {
    const current = window.location.pathname;
    if (!current.includes('login')) {
      window.location.href = '/login?next=' + encodeURIComponent(current);
    }
  },
};

/* ═══════════════════════════════════════════════════════════
   API FETCH WRAPPER
═══════════════════════════════════════════════════════════ */
/**
 * apiFetch('/problems?limit=20')
 * apiFetch('/login', { method:'POST', body: { otp_code:'123456' } })
 */
async function apiFetch(path, opts = {}) {
  const url = RC.API_BASE + path;
  const token = Auth.getToken();

  const headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(opts.headers || {}),
  };

  const init = {
    method: opts.method || 'GET',
    headers,
    ...(opts.body ? { body: JSON.stringify(opts.body) } : {}),
  };

  const res = await fetch(url, init);

  /* 401 → token eskirgan, login sahifasiga o'tkazish */
  if (res.status === 401) {
    Auth.clear();
    Auth.redirectToLogin();
    throw new Error('Sessiya tugagan. Iltimos, qayta kiring.');
  }

  /* 429 → rate limit */
  if (res.status === 429) {
    throw new Error('Juda ko\'p so\'rov. Biroz kuting.');
  }

  let data;
  try { data = await res.json(); } catch { data = null; }

  if (!res.ok) {
    const msg = data?.error || data?.detail || data?.message || `HTTP ${res.status}`;
    throw new Error(msg);
  }

  return data;
}

/* ═══════════════════════════════════════════════════════════
   TOAST NOTIFICATIONS
   showToast('Xabar matni', 'success' | 'error' | 'warning' | 'info')
═══════════════════════════════════════════════════════════ */
(function initToast() {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }
})();

function showToast(message, type = 'info', duration = RC.TOAST_DURATION) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const icons = {
    success: `<svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>`,
    error:   `<svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
    warning: `<svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
    info:    `<svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
  };

  const toast = document.createElement('div');
  toast.className = `toast-item ${type}`;
  toast.innerHTML = `
    <span class="toast-dot"></span>
    <span style="flex:1;min-width:0">${escHtml(message)}</span>
    <button onclick="this.parentElement.remove()" style="background:none;border:none;cursor:pointer;opacity:0.5;padding:0;display:flex;align-items:center;color:inherit;margin-left:4px">
      <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
    </button>`;

  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('out');
    setTimeout(() => toast.remove(), 320);
  }, duration);

  return toast;
}

/* Alias: Turli nom bilan chaqirishlar uchun */
window.showToast = showToast;
window.notify    = showToast;

/* ═══════════════════════════════════════════════════════════
   MODAL HELPERS
═══════════════════════════════════════════════════════════ */
const Modal = {
  open(id)  {
    const el = document.getElementById(id);
    if (el) { el.classList.add('show'); document.body.style.overflow = 'hidden'; }
  },
  close(id) {
    const el = document.getElementById(id);
    if (el) { el.classList.remove('show'); document.body.style.overflow = ''; }
  },
  toggle(id) {
    const el = document.getElementById(id);
    if (el) el.classList.contains('show') ? this.close(id) : this.open(id);
  },
};

/* Overlay-ga click → modal yopilsin */
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('show');
    document.body.style.overflow = '';
  }
});

/* ESC → barcha ochiq modalni yop */
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.show').forEach(m => {
      m.classList.remove('show');
      document.body.style.overflow = '';
    });
  }
});

/* ═══════════════════════════════════════════════════════════
   TOPBAR: foydalanuvchi ma'lumotlarini ko'rsatish
═══════════════════════════════════════════════════════════ */
function renderTopbarUser() {
  const user = Auth.getUser();
  const avatarEl = document.querySelector('.user-avatar');
  const loginBtn = document.querySelector('.btn-login');
  const signupBtn = document.querySelector('.btn-signup');

  if (!avatarEl) return;

  if (user && Auth.isLoggedIn()) {
    /* Initials */
    const name = user.full_name || user.username || '?';
    const initials = name.split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase();
    avatarEl.textContent = initials;
    avatarEl.title = name;
    avatarEl.style.display = 'flex';

    if (loginBtn)  loginBtn.style.display  = 'none';
    if (signupBtn) signupBtn.style.display = 'none';
  } else {
    avatarEl.style.display = 'none';
    if (loginBtn)  loginBtn.style.display  = '';
    if (signupBtn) signupBtn.style.display = '';
  }
}

/* Logout */
function logout() {
  Auth.clear();
  showToast('Tizimdan chiqdingiz', 'info');
  setTimeout(() => window.location.href = '/login.html', 800);
}
window.logout = logout;

/* ═══════════════════════════════════════════════════════════
   NAV: active link highlight
═══════════════════════════════════════════════════════════ */
function highlightNav() {
  const path = window.location.pathname;
  document.querySelectorAll('.nav-link').forEach(link => {
    const href = link.getAttribute('href') || '';
    const active =
      (href !== '/' && path.includes(href)) ||
      (href === '/' && (path === '/' || path === '/index.html'));
    link.classList.toggle('active', active);
  });
}

/* ═══════════════════════════════════════════════════════════
   HINT TOGGLES (problem description)
═══════════════════════════════════════════════════════════ */
function initHintToggles() {
  document.querySelectorAll('.hint-toggle').forEach(btn => {
    btn.addEventListener('click', function () {
      const body = this.nextElementSibling;
      if (!body || !body.classList.contains('hint-body')) return;
      const open = body.style.display === 'block';
      body.style.display = open ? 'none' : 'block';
      this.classList.toggle('open', !open);
    });
  });
}

/* ═══════════════════════════════════════════════════════════
   DRAG RESIZE (split layout — horizontal)
═══════════════════════════════════════════════════════════ */
function initSplitDrag(opts = {}) {
  const bar     = opts.bar     || document.getElementById('splitDrag');
  const left    = opts.left    || document.getElementById('splitLeft');
  const onResize = opts.onResize || null;
  if (!bar || !left) return;

  let dragging = false;

  bar.addEventListener('mousedown', e => {
    dragging = true;
    e.preventDefault();
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  });

  document.addEventListener('mousemove', e => {
    if (!dragging) return;
    const ws = (opts.container || document.getElementById('workspace') || document.body).getBoundingClientRect();
    const w  = Math.max(280, Math.min(e.clientX - ws.left, ws.width - 360));
    left.style.width    = w + 'px';
    left.style.minWidth = w + 'px';
    if (onResize) onResize(w);
  });

  document.addEventListener('mouseup', () => {
    if (!dragging) return;
    dragging = false;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  });
}

/* ═══════════════════════════════════════════════════════════
   BOTTOM PANEL RESIZE (vertical)
═══════════════════════════════════════════════════════════ */
function initBottomResize(opts = {}) {
  const handle   = opts.handle   || document.getElementById('bottomResize');
  const zone     = opts.zone     || document.getElementById('bottomZone');
  const onResize = opts.onResize || null;
  if (!handle || !zone) return;

  let dragging = false, startY = 0, startH = 0;

  handle.addEventListener('mousedown', e => {
    dragging = true;
    startY = e.clientY;
    startH = zone.offsetHeight;
    e.preventDefault();
    document.body.style.cursor = 'row-resize';
    document.body.style.userSelect = 'none';
  });

  document.addEventListener('mousemove', e => {
    if (!dragging) return;
    const h = Math.max(80, Math.min(startH - (e.clientY - startY), 560));
    zone.style.height = h + 'px';
    if (onResize) onResize(h);
  });

  document.addEventListener('mouseup', () => {
    if (!dragging) return;
    dragging = false;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  });
}

/* ═══════════════════════════════════════════════════════════
   ACCEPTANCE RATE BARS — animatsiya
═══════════════════════════════════════════════════════════ */
function animateRateBars() {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const fill = entry.target;
        const target = fill.dataset.width || '0';
        fill.style.width = target + '%';
        observer.unobserve(fill);
      }
    });
  }, { threshold: 0.2 });

  document.querySelectorAll('.rate-fill[data-width]').forEach(el => {
    el.style.width = '0%';
    observer.observe(el);
  });
}

/* ═══════════════════════════════════════════════════════════
   COPY TO CLIPBOARD
═══════════════════════════════════════════════════════════ */
async function copyText(text, msg = 'Nusxalandi!') {
  try {
    await navigator.clipboard.writeText(text);
    showToast(msg, 'success', 1800);
  } catch {
    /* Fallback */
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;opacity:0';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    ta.remove();
    showToast(msg, 'success', 1800);
  }
}
window.copyText = copyText;

/* ═══════════════════════════════════════════════════════════
   FORMAT HELPERS
═══════════════════════════════════════════════════════════ */

/** XSS-dan himoya */
function escHtml(str) {
  const d = document.createElement('div');
  d.textContent = str || '';
  return d.innerHTML;
}

/** Sonni formatlash: 1234567 → 1.2M */
function fmtNum(n) {
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return String(n);
}

/** Vaqtni formatlashtirish */
function fmtTime(ms) {
  if (ms < 1000) return ms + 'ms';
  return (ms / 1000).toFixed(2) + 's';
}

/** Bayt → KB/MB */
function fmtBytes(b) {
  if (b >= 1048576) return (b / 1048576).toFixed(1) + ' MB';
  if (b >= 1024)    return (b / 1024).toFixed(1) + ' KB';
  return b + ' B';
}

/** Nisbiy vaqt: "2 daqiqa oldin" */
function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60)   return 'Hozirgina';
  const m = Math.floor(s / 60);
  if (m < 60)   return `${m} daqiqa oldin`;
  const h = Math.floor(m / 60);
  if (h < 24)   return `${h} soat oldin`;
  const d = Math.floor(h / 24);
  if (d < 30)   return `${d} kun oldin`;
  const mo = Math.floor(d / 30);
  if (mo < 12)  return `${mo} oy oldin`;
  return `${Math.floor(mo / 12)} yil oldin`;
}

/** Qiyinlik belgisi HTML */
function diffBadgeHtml(diff) {
  const map = {
    easy:   ['badge-easy',   'Easy'],
    medium: ['badge-medium', 'Medium'],
    hard:   ['badge-hard',   'Hard'],
  };
  const [cls, label] = map[(diff || '').toLowerCase()] || map.easy;
  return `<span class="badge ${cls}">${label}</span>`;
}

/** Qabul % uchun rang sinfi */
function rateClass(rate) {
  const r = Math.round(rate || 0);
  if (r >= 60) return 'high';
  if (r >= 35) return 'medium';
  return 'low';
}

/* Global export */
window.RC_Utils = { escHtml, fmtNum, fmtTime, fmtBytes, timeAgo, diffBadgeHtml, rateClass };

/* ═══════════════════════════════════════════════════════════
   COUNTDOWN TIMER
   const timer = new CountdownTimer(300, el, onEnd)
   timer.start() / timer.stop() / timer.reset(secs)
═══════════════════════════════════════════════════════════ */
class CountdownTimer {
  constructor(seconds, el, onEnd) {
    this.secs  = seconds;
    this.left  = seconds;
    this.el    = typeof el === 'string' ? document.getElementById(el) : el;
    this.onEnd = onEnd || null;
    this._iv   = null;
  }

  start() {
    this._tick();
    this._iv = setInterval(() => this._tick(), 1000);
  }

  stop()  { clearInterval(this._iv); }

  reset(secs) {
    this.stop();
    this.left = secs !== undefined ? secs : this.secs;
    this._render();
  }

  _tick() {
    this._render();
    if (this.left <= 0) {
      this.stop();
      if (this.onEnd) this.onEnd();
      return;
    }
    this.left--;
  }

  _render() {
    if (!this.el) return;
    const m   = String(Math.floor(this.left / 60)).padStart(2, '0');
    const s   = String(this.left % 60).padStart(2, '0');
    this.el.textContent = `${m}:${s}`;
    if (this.left <= 30) this.el.style.color = 'var(--hard)';
    else if (this.left <= 60) this.el.style.color = 'var(--medium)';
    else this.el.style.color = '';
  }
}
window.CountdownTimer = CountdownTimer;

/* ═══════════════════════════════════════════════════════════
   DEBOUNCE / THROTTLE
═══════════════════════════════════════════════════════════ */
function debounce(fn, delay = 300) {
  let t;
  return function (...args) {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(this, args), delay);
  };
}

function throttle(fn, limit = 100) {
  let last = 0;
  return function (...args) {
    const now = Date.now();
    if (now - last < limit) return;
    last = now;
    return fn.apply(this, args);
  };
}

window.debounce  = debounce;
window.throttle  = throttle;

/* ═══════════════════════════════════════════════════════════
   LOCAL STORAGE HELPERS (JSON-safe)
═══════════════════════════════════════════════════════════ */
const Store = {
  get(key, fallback = null) {
    try { return JSON.parse(localStorage.getItem(key)); } catch { return fallback; }
  },
  set(key, val) {
    try { localStorage.setItem(key, JSON.stringify(val)); } catch {}
  },
  remove(key) { localStorage.removeItem(key); },
};
window.Store = Store;

/* ═══════════════════════════════════════════════════════════
   BOOKMARKS (local)
═══════════════════════════════════════════════════════════ */
const Bookmarks = {
  _key: 'rc_bookmarks',
  all()        { return Store.get(this._key, []); },
  has(id)      { return this.all().includes(id); },
  toggle(id)   {
    const list = this.all();
    const idx  = list.indexOf(id);
    if (idx === -1) { list.push(id); showToast('Saqlandi 🔖', 'success', 1800); }
    else            { list.splice(idx, 1); showToast('Saqlashdan olib tashlandi', 'info', 1800); }
    Store.set(this._key, list);
    return idx === -1; /* true = qo'shildi */
  },
};
window.Bookmarks = Bookmarks;

/* ═══════════════════════════════════════════════════════════
   KEYBOARD SHORTCUTS REGISTRY
═══════════════════════════════════════════════════════════ */
const Shortcuts = {
  _map: {},
  register(combo, fn, description = '') {
    this._map[combo.toLowerCase()] = { fn, description };
  },
  _parse(e) {
    const parts = [];
    if (e.ctrlKey || e.metaKey) parts.push('ctrl');
    if (e.shiftKey) parts.push('shift');
    if (e.altKey)   parts.push('alt');
    parts.push(e.key.toLowerCase());
    return parts.join('+');
  },
};

document.addEventListener('keydown', e => {
  /* Inputda bosish — global shortcut-lar ishlamaydi */
  const tag = document.activeElement?.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || document.activeElement?.isContentEditable) return;

  const combo = Shortcuts._parse(e);
  if (Shortcuts._map[combo]) {
    e.preventDefault();
    Shortcuts._map[combo].fn(e);
  }
});

/* Built-in: / → search inputga fokus */
Shortcuts.register('/', () => {
  const s = document.querySelector('.input[type="search"], #searchInput');
  if (s) { s.focus(); s.select(); }
});

window.Shortcuts = Shortcuts;

/* ═══════════════════════════════════════════════════════════
   FULLSCREEN
═══════════════════════════════════════════════════════════ */
function toggleFullscreen(el) {
  const target = el || document.documentElement;
  if (!document.fullscreenElement) {
    target.requestFullscreen().catch(() => showToast('To\'liq ekran ishlamadi', 'warning'));
  } else {
    document.exitFullscreen().catch(() => {});
  }
}
window.toggleFullscreen = toggleFullscreen;

/* ═══════════════════════════════════════════════════════════
   INIT — DOMContentLoaded
═══════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  /* Toast container yaratish */
  if (!document.getElementById('toast-container')) {
    const c = document.createElement('div');
    c.id = 'toast-container';
    document.body.appendChild(c);
  }

  renderTopbarUser();
  highlightNav();
  initHintToggles();
  animateRateBars();

  /* Barcha .hint-toggle ga bosish ishlovchisi */
  document.body.addEventListener('click', e => {
    const btn = e.target.closest('.hint-toggle');
    if (!btn) return;
    const body = btn.nextElementSibling;
    if (!body || !body.classList.contains('hint-body')) return;
    const open = body.style.display === 'block';
    body.style.display = open ? 'none' : 'block';
    btn.classList.toggle('open', !open);
  });

  /* Bookmarks tugmalarini sync qilish */
  document.querySelectorAll('[data-bookmark]').forEach(btn => {
    const id = btn.dataset.bookmark;
    if (Bookmarks.has(id)) btn.classList.add('active');
    btn.addEventListener('click', () => {
      const added = Bookmarks.toggle(id);
      btn.classList.toggle('active', added);
    });
  });
});

/* ═══════════════════════════════════════════════════════════
   GLOBAL EXPORTS
═══════════════════════════════════════════════════════════ */
window.RC       = RC;
window.Auth     = Auth;
window.apiFetch = apiFetch;
window.Modal    = Modal;