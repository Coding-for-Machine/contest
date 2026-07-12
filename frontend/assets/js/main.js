/* ============================================================
   CfM Contest — Global JavaScript
   ============================================================ */

(function() {
    'use strict';

    // ============================================================
    // 0. GLOBAL NAVBAR — bitta joyda, har sahifada shu ishlatiladi.
    //    HTML tomonda faqat shu kerak:
    //    <header id="navbar" class="topbar" role="banner"></header>
    // ============================================================
    var NAVBAR_HTML = [
        '<div class="navbar-inner">',
        '  <div class="navbar-left">',
        '    <a href="/" class="navbar-brand" aria-label="CfM Contest bosh sahifa">',
        '      <picture>',
        '        <source srcset="/assets/img/cfm_logo.webp" type="image/webp">',
        '        <img src="/assets/img/cfm_logo.png" alt="CfM Contest Logotipi" width="32" height="32" loading="eager">',
        '      </picture>',
        '      <span class="navbar-brand-text">CfM<small> Contest</small></span>',
        '    </a>',
        '    <nav class="navbar-nav" role="navigation" aria-label="Asosiy navigatsiya">',
        '      <a href="/problems" class="nav-link" id="nav-problems"><span class="material-icons" aria-hidden="true">playlist_play</span> Masalalar</a>',
        '      <a href="/tests" class="nav-link" id="nav-tests"><span class="material-icons" aria-hidden="true">quiz</span> Testlar</a>',
        '      <a href="/contests" class="nav-link" id="nav-contests"><span class="material-icons" aria-hidden="true">emoji_events</span> Musobaqalar</a>',
        '      <a href="/courses" class="nav-link" id="nav-courses"><span class="material-icons" aria-hidden="true">school</span> Kurslar</a>',
        '      <a href="/leaderboard" class="nav-link" id="nav-leaderboard"><span class="material-icons" aria-hidden="true">leaderboard</span> Reyting</a>',
        '    </nav>',
        '  </div>',
        '  <div class="navbar-right">',
        '    <div id="authButtonsBlock" class="navbar-auth-buttons">',
        '      <a href="/login" class="btn btn-outline btn-sm" id="btn-login">Kirish</a>',
        '      <a href="/login" class="btn btn-primary btn-sm" id="btn-signup">Boshlash</a>',
        '    </div>',
        '    <div id="userMenuBlock" class="user-dropdown hidden">',
        '      <button id="userAvatarBtn" class="user-avatar" aria-label="Foydalanuvchi menyusi">AZ</button>',
        '      <div id="userMenu" class="user-dropdown-menu" role="menu">',
        '        <div class="user-menu-header">',
        '          <div id="userMenuName" class="user-menu-name">—</div>',
        '          <div id="userMenuPhone" class="user-menu-phone">—</div>',
        '        </div>',
        '        <a href="#" id="menuProfileLink" role="menuitem"><span class="material-icons" style="font-size:16px;">person</span> Profil</a>',
        '        <a href="/leaderboard" role="menuitem"><span class="material-icons" style="font-size:16px;">emoji_events</span> Mening reytingim</a>',
        '        <a href="/settings" role="menuitem"><span class="material-icons" style="font-size:16px;">settings</span> Sozlamalar</a>',
        '        <div class="user-dropdown-divider"></div>',
        '        <button id="logoutBtn" class="danger" role="menuitem"><span class="material-icons" style="font-size:16px;">logout</span> Chiqish</button>',
        '      </div>',
        '    </div>',
        '    <button class="navbar-mobile-btn" id="navbarMobileBtn" aria-label="Menyu">',
        '      <span class="material-icons" aria-hidden="true">menu</span>',
        '    </button>',
        '  </div>',
        '</div>',
        '<div id="navbarMobileNav" class="navbar-mobile-nav" role="navigation" aria-label="Mobil navigatsiya">',
        '  <div class="navbar-inner">',
        '    <a href="/problems" class="nav-link"><span class="material-icons" aria-hidden="true">playlist_play</span> Masalalar</a>',
        '    <a href="/tests" class="nav-link"><span class="material-icons" aria-hidden="true">quiz</span> Testlar</a>',
        '    <a href="/contests" class="nav-link"><span class="material-icons" aria-hidden="true">emoji_events</span> Musobaqalar</a>',
        '    <a href="/courses" class="nav-link"><span class="material-icons" aria-hidden="true">school</span> Kurslar</a>',
        '    <a href="/leaderboard" class="nav-link"><span class="material-icons" aria-hidden="true">leaderboard</span> Reyting</a>',
        '  </div>',
        '</div>'
    ].join('');

    function injectNavbar() {
        var mount = document.getElementById('navbar');
        if (!mount) return; // sahifada navbar yo'q bo'lsa (mas. login), jim o'tkazamiz

        mount.innerHTML = NAVBAR_HTML;

        // Foydalanuvchi dropdown
        var avatarBtn = document.getElementById('userAvatarBtn');
        var menu = document.getElementById('userMenu');
        if (avatarBtn && menu) {
            avatarBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                menu.classList.toggle('show');
            });
        }
        document.addEventListener('click', function(e) {
            if (menu && menu.classList.contains('show') && !e.target.closest('#userMenuBlock')) {
                menu.classList.remove('show');
            }
        });

        // Mobil menyu
        var mobileBtn = document.getElementById('navbarMobileBtn');
        var mobileNav = document.getElementById('navbarMobileNav');
        if (mobileBtn && mobileNav) {
            mobileBtn.addEventListener('click', function() {
                mobileNav.classList.toggle('show');
            });
        }
    }
    window.injectNavbar = injectNavbar;

    // ============================================================
    // 1. TOAST
    // ============================================================
    function showToast(message, type, duration) {
        type = type || 'info';
        duration = duration || 3000;
        var container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            document.body.appendChild(container);
        }

        var toast = document.createElement('div');
        toast.className = 'toast-item ' + type;
        toast.innerHTML =
            '<span class="toast-dot"></span>' +
            '<span style="flex:1;min-width:0;">' + escapeHtml(message) + '</span>' +
            '<button onclick="this.parentElement.remove()" style="background:none;border:none;cursor:pointer;opacity:0.5;padding:0;display:flex;align-items:center;color:inherit;margin-left:4px;">' +
            '<span class="material-icons" style="font-size:15px;">close</span>' +
            '</button>';

        container.appendChild(toast);
        setTimeout(function() {
            toast.classList.add('out');
            setTimeout(function() { toast.remove(); }, 300);
        }, duration);
    }
    window.showToast = showToast;

    // ============================================================
    // 2. AUTH
    // ============================================================
    var Auth = {
        getToken: function() { return localStorage.getItem('cfm_auth_token') || ''; },
        getUser: function() {
            try { return JSON.parse(localStorage.getItem('cfm_user_data') || 'null'); } catch (e) { return null; }
        },
        setToken: function(t) { localStorage.setItem('cfm_auth_token', t); },
        setUser: function(u) { localStorage.setItem('cfm_user_data', JSON.stringify(u)); },
        clear: function() { localStorage.removeItem('cfm_auth_token'); localStorage.removeItem('cfm_user_data'); },
        isLoggedIn: function() { return !!this.getToken(); },
        logout: function() {
            this.clear();
            showToast('Tizimdan chiqdingiz', 'info');
            setTimeout(function() { window.location.href = '/login'; }, 800);
        },

        // Qat'iy sahifalar uchun — faqat localStorage tekshiradi, API chaqirmaydi
        requireAuth: function(redirectTo) {
            if (!this.isLoggedIn()) {
                var next = encodeURIComponent(window.location.pathname + window.location.search);
                window.location.replace((redirectTo || '/login') + '?next=' + next);
                return false;
            }
            return true;
        },

        // Login sahifasi uchun — token bor bo'lsa ichkariga kiritmaydi
        redirectIfLoggedIn: function(defaultNext) {
            if (this.isLoggedIn()) {
                var params = new URLSearchParams(window.location.search);
                var next = params.get('next') || defaultNext || '/';
                window.location.replace(next);
                return true;
            }
            return false;
        }
    };
    window.Auth = Auth;

    // ============================================================
    // 3. API FETCH
    // ============================================================
    var RC_API_BASE = 'http://localhost:8000/api/v1';

    // Django data API (problems, categories, tags, submissions...) — alohida bazaviy URL.
    // Har bir sahifa shu bittasidan foydalanadi: window.RC_DATA_API_BASE
    window.RC_DATA_API_BASE = window.RC_DATA_API_BASE || 'http://localhost:8000/api/v1';

    async function apiFetch(path, opts) {
        opts = opts || {};
        var url = RC_API_BASE + path;
        var token = Auth.getToken();

        var headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        };
        if (token) headers['Authorization'] = 'Bearer ' + token;
        if (opts.headers) Object.assign(headers, opts.headers);

        var init = {
            method: opts.method || 'GET',
            headers: headers
        };
        if (opts.body) init.body = JSON.stringify(opts.body);

        var res = await fetch(url, init);

        if (res.status === 401) {
            Auth.clear();
            if (!window.location.pathname.includes('login')) {
                window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
            }
            throw new Error('Sessiya tugagan. Iltimos, qayta kiring.');
        }

        if (res.status === 429) {
            throw new Error('Juda ko\'p so\'rov. Biroz kuting.');
        }

        var data;
        try { data = await res.json(); } catch (e) { data = null; }

        if (!res.ok) {
            var msg = data?.error || data?.detail || data?.message || 'HTTP ' + res.status;
            throw new Error(msg);
        }

        return data;
    }
    window.apiFetch = apiFetch;

    // ============================================================
    // 3.1 GLOBAL SSE (Server-Sent Events) — BITTA umumiy ulanish, butun sayt uchun.
    //
    // Oqim: POST /run yoki /submit → backend darhol {task_id, queued:true}
    // qaytaradi (Celery navbatga qo'yadi) → Celery worker Piston orqali
    // bajaradi → natijani Redisga PUBLISH qiladi (kanal: sse:user:{id}) →
    // Django Bolt shu kanalni tinglab turgan async SSE endpoint orqali
    // brauzerga uzatadi → shu yerdagi RCEvents ularni tarqatadi (pub/sub).
    //
    // Bitta ulanishda RUN/SUBMIT natijalaridan tashqari boshqa turdagi
    // eventlar ham kelishi mumkin (bildirishnoma va h.k.) — shuning uchun
    // umumiy (global) pub/sub sifatida yozilgan, faqat run/submit uchun emas.
    //
    // Ishlatilishi:
    //   RCEvents.connect();                                    // bir marta, sahifa boshida
    //   var off = RCEvents.onTask(taskId, function(envelope) {...});  // task_id bo'yicha obuna
    //   off();                                                 // kerak bo'lmasa uziladi
    //   RCEvents.on('notification', function(envelope) {...});  // umumiy turdagi eventga obuna
    //
    // EventSource maxsus header yubora olmagani uchun autentifikatsiya
    // query parametr orqali beriladi (?token=...) — backendda shu parametrni
    // o'qiydigan auth dependency kerak bo'ladi.
    // ============================================================
    var RCEvents = (function() {
        var source = null;
        var connected = false;
        var listeners = {};       // eventType -> [callback, ...]
        var taskListeners = {};   // task_id  -> [callback, ...]

        // Backend hamma narsani STRING holda yuboradi. Ba'zan bu string JSON
        // (masalan {"task_id":...,"type":...,"result":"..."}), ba'zan xom
        // matn bo'lishi mumkin — shuning uchun ikkalasini ham qo'llab-quvvatlaymiz.
        function parseEnvelope(raw) {
            try { return JSON.parse(raw); } catch (e) { return { raw: raw }; }
        }

        function dispatch(eventName, raw) {
            var data = parseEnvelope(raw);
            var envelope = { event: eventName, data: data, raw: raw };

            console.log('◀ [SSE:' + eventName + ']', data);

            (listeners[eventName] || []).slice().forEach(function(cb) { cb(envelope); });

            var taskId = data && (data.task_id || data.taskId);
            if (taskId && taskListeners[taskId]) {
                taskListeners[taskId].slice().forEach(function(cb) { cb(envelope); });
            }
        }

        return {
            connect: function(url) {
                if (connected || !window.EventSource) return;
                url = url || ((window.RC_DATA_API_BASE || 'http://localhost:8000/api/v1') + '/sse/events/stream/');

                var token = Auth.getToken();
                if (token) url += (url.indexOf('?') === -1 ? '?' : '&') + 'token=' + encodeURIComponent(token);

                try {
                    source = new EventSource(url, { withCredentials: true });
                } catch (e) {
                    console.error('[SSE] ulanish ochilmadi:', e);
                    return;
                }

                source.onopen = function() {
                    connected = true;
                    console.log('■ [SSE] global ulanish ochildi');
                };
                source.onerror = function(e) {
                    connected = false;
                    console.warn('[SSE] ulanishda uzilish (brauzer avtomatik qayta ulanadi):', e);
                };

                // Nomlanmagan ("data: ..." faqat) eventlar
                source.onmessage = function(e) { dispatch('message', e.data); };

                // Backend "event: run_result" kabi nomlangan eventlar yuborsa —
                // ro'yxatga moslab qo'shing
                ['run_result', 'submission_result', 'notification', 'task_update', 'done'].forEach(function(name) {
                    source.addEventListener(name, function(e) { dispatch(name, e.data); });
                });
            },

            disconnect: function() {
                if (source) { source.close(); source = null; }
                connected = false;
            },

            // Umumiy turdagi eventlarga obuna (masalan 'notification')
            on: function(eventName, cb) {
                listeners[eventName] = listeners[eventName] || [];
                listeners[eventName].push(cb);
                return function() {
                    listeners[eventName] = (listeners[eventName] || []).filter(function(f) { return f !== cb; });
                };
            },

            // Aynan bitta task_id (bitta Run/Submit) natijalariga obuna
            onTask: function(taskId, cb) {
                taskListeners[taskId] = taskListeners[taskId] || [];
                taskListeners[taskId].push(cb);
                return function() {
                    taskListeners[taskId] = (taskListeners[taskId] || []).filter(function(f) { return f !== cb; });
                };
            },

            isConnected: function() { return connected; }
        };
    })();
    window.RCEvents = RCEvents;

    // ============================================================
    // 3.2 PISTON VERDIKT-STRING PARSERI
    //
    // Backend (PistonStreamService) natijani JSON emas, quyidagi qolipdagi
    // STRING holida qaytaradi:
    //   "IJRO: [AC]\n[Natija]:\n0 1"
    //   "KOMPILYATSIYA: [CE]\n[Xatolik matni]:\n..."
    //   "IJRO: [TO] (Vaqt tugadi)"
    // Bu yerda uni struktura holiga o'tkazamiz.
    // ============================================================
    var VERDICT_LABELS = {
        AC: 'Qabul qilindi', CE: 'Kompilyatsiya xatosi', RE: "Ishga tushirish xatosi",
        TO: 'Vaqt tugadi', SG: 'Signal (crash)', OL: "Chiqish uzunligi oshib ketdi",
        EL: "Xato uzunligi oshib ketdi", XX: 'Tizim xatosi'
    };

    function parseVerdictString(str) {
        str = str || '';
        var m = str.match(/^([^:]+):\s*\[([A-Z]{2})\]\s*(?:\(([^)]*)\))?(?:\n\[[^\]]+\]:\n([\s\S]*))?$/);
        if (!m) return { stage: '—', code: 'XX', label: VERDICT_LABELS.XX, passed: false, note: '', body: str };

        var stage = m[1].trim(), code = m[2], note = m[3] || '', body = m[4] || '';
        return {
            stage: stage,
            code: code,
            label: VERDICT_LABELS[code] || code,
            passed: code === 'AC',
            note: note,
            body: body
        };
    }
    window.parseVerdictString = parseVerdictString;

    // ============================================================
    // 4. TOPBAR USER — login/logout holatiga qarab navbar o'ng
    //    tomonini almashtiradi (Kirish/Boshlash <-> avatar+dropdown)
    // ============================================================
    function truncateText(str, n) {
        str = (str || '').trim();
        if (!str) return '';
        return str.length > n ? str.slice(0, n).trim() + '…' : str;
    }

    function renderTopbarUser() {
        var user = Auth.getUser();
        var authBlock = document.getElementById('authButtonsBlock');
        var userBlock = document.getElementById('userMenuBlock');
        var avatarBtn = document.getElementById('userAvatarBtn');
        var nameEl = document.getElementById('userMenuName');
        var phoneEl = document.getElementById('userMenuPhone');
        var profileLink = document.getElementById('menuProfileLink');
        var footerProfileLink = document.getElementById('footerProfileLink');

        if (Auth.isLoggedIn() && user) {
            var fullName = user.f || user.full_name || '';
            var username = user.u || user.username || '';
            var phone = user.phone || user.p || user.tel || '';
            var displayName = fullName || username || 'Foydalanuvchi';
            var shortName = truncateText(displayName, 20);

            var initials = String(displayName).trim().split(/\s+/).slice(0, 2)
                .map(function(w) { return w[0]; }).join('').toUpperCase();

            if (avatarBtn) { avatarBtn.textContent = initials; avatarBtn.title = displayName; }
            if (nameEl) nameEl.textContent = shortName;
            if (phoneEl) phoneEl.textContent = phone ? phone : (username ? '@' + username : '');

            if (authBlock) authBlock.classList.add('hidden');
            if (userBlock) userBlock.classList.remove('hidden');

            if (username) {
                if (profileLink) profileLink.href = '/u/' + username;
                if (footerProfileLink) footerProfileLink.href = '/u/' + username;
            }
        } else {
            if (authBlock) authBlock.classList.remove('hidden');
            if (userBlock) userBlock.classList.add('hidden');
        }
    }
    window.renderTopbarUser = renderTopbarUser;

    // Logout — dropdown har qanday sahifada chiqsa ham ishlaydi
    document.addEventListener('click', function(e) {
        if (e.target.closest('#logoutBtn')) Auth.logout();
    });

    // ============================================================
    // 5. NAV HIGHLIGHT
    // ============================================================
    function highlightNav() {
        var path = window.location.pathname;
        document.querySelectorAll('.nav-link').forEach(function(link) {
            var href = link.getAttribute('href') || '';
            var active =
                (href !== '/' && path.indexOf(href) === 0) ||
                (href === '/' && path === '/');
            link.classList.toggle('active', active);
        });
    }
    window.highlightNav = highlightNav;

    // ============================================================
    // 6. MODAL
    // ============================================================
    var Modal = {
        open: function(id) {
            var el = document.getElementById(id);
            if (el) { el.classList.add('show'); document.body.style.overflow = 'hidden'; }
        },
        close: function(id) {
            var el = document.getElementById(id);
            if (el) { el.classList.remove('show'); document.body.style.overflow = ''; }
        },
        toggle: function(id) {
            var el = document.getElementById(id);
            if (el) { el.classList.contains('show') ? this.close(id) : this.open(id); }
        }
    };
    window.Modal = Modal;

    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal-overlay')) {
            e.target.classList.remove('show');
            document.body.style.overflow = '';
        }
    });

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-overlay.show').forEach(function(m) {
                m.classList.remove('show');
                document.body.style.overflow = '';
            });
        }
    });

    // ============================================================
    // 7. HINT TOGGLES
    // ============================================================
    function initHintToggles() {
        document.querySelectorAll('.hint-toggle').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var body = this.nextElementSibling;
                if (!body || !body.classList.contains('hint-body')) return;
                var open = body.style.display === 'block';
                body.style.display = open ? 'none' : 'block';
                this.classList.toggle('open', !open);
            });
        });
    }
    window.initHintToggles = initHintToggles;

    // ============================================================
    // 8. SPLIT DRAG
    // ============================================================
    function initSplitDrag(opts) {
        opts = opts || {};
        var bar = opts.bar || document.getElementById('splitDrag');
        var left = opts.left || document.getElementById('splitLeft');
        var onResize = opts.onResize || null;
        if (!bar || !left) return;
        var dragging = false;

        bar.addEventListener('mousedown', function(e) {
            dragging = true;
            e.preventDefault();
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', function(e) {
            if (!dragging) return;
            var ws = (opts.container || document.getElementById('workspace') || document.body)
                .getBoundingClientRect();
            var w = Math.max(280, Math.min(e.clientX - ws.left, ws.width - 360));
            left.style.width = w + 'px';
            left.style.minWidth = w + 'px';
            if (onResize) onResize(w);
        });

        document.addEventListener('mouseup', function() {
            if (!dragging) return;
            dragging = false;
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        });
    }
    window.initSplitDrag = initSplitDrag;

    // ============================================================
    // 9. BOTTOM RESIZE
    // ============================================================
    function initBottomResize(opts) {
        opts = opts || {};
        var handle = opts.handle || document.getElementById('bottomResize');
        var zone = opts.zone || document.getElementById('bottomZone');
        var onResize = opts.onResize || null;
        if (!handle || !zone) return;
        var dragging = false, startY = 0, startH = 0;

        handle.addEventListener('mousedown', function(e) {
            dragging = true;
            startY = e.clientY;
            startH = zone.offsetHeight;
            e.preventDefault();
            document.body.style.cursor = 'row-resize';
            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', function(e) {
            if (!dragging) return;
            var h = Math.max(80, Math.min(startH - (e.clientY - startY), 560));
            zone.style.height = h + 'px';
            if (onResize) onResize(h);
        });

        document.addEventListener('mouseup', function() {
            if (!dragging) return;
            dragging = false;
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        });
    }
    window.initBottomResize = initBottomResize;

    // ============================================================
    // 10. UTILITIES
    // ============================================================
    function escapeHtml(str) {
        var d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    }

    function fmtNum(n) {
        if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
        if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
        return String(n);
    }

    function timeAgo(dateStr) {
        var diff = Date.now() - new Date(dateStr).getTime();
        var s = Math.floor(diff / 1000);
        if (s < 60) return 'Hozirgina';
        var m = Math.floor(s / 60);
        if (m < 60) return m + ' daqiqa oldin';
        var h = Math.floor(m / 60);
        if (h < 24) return h + ' soat oldin';
        var d = Math.floor(h / 24);
        if (d < 30) return d + ' kun oldin';
        var mo = Math.floor(d / 30);
        if (mo < 12) return mo + ' oy oldin';
        return Math.floor(mo / 12) + ' yil oldin';
    }

    function diffBadgeHtml(diff) {
        var map = {
            easy: ['badge-easy', 'Easy'],
            medium: ['badge-medium', 'Medium'],
            hard: ['badge-hard', 'Hard']
        };
        var pair = map[(diff || '').toLowerCase()] || map.easy;
        return '<span class="badge ' + pair[0] + '">' + pair[1] + '</span>';
    }

    window.RC_Utils = {
        escapeHtml: escapeHtml,
        fmtNum: fmtNum,
        timeAgo: timeAgo,
        diffBadgeHtml: diffBadgeHtml
    };

    // ============================================================
    // 11. COUNTDOWN TIMER
    // ============================================================
    function CountdownTimer(seconds, el, onEnd) {
        this.secs = seconds;
        this.left = seconds;
        this.el = typeof el === 'string' ? document.getElementById(el) : el;
        this.onEnd = onEnd || null;
        this._iv = null;
        var self = this;

        this.start = function() {
            self._tick();
            self._iv = setInterval(function() { self._tick(); }, 1000);
        };

        this.stop = function() { clearInterval(self._iv); };

        this.reset = function(secs) {
            self.stop();
            self.left = secs !== undefined ? secs : self.secs;
            self._render();
        };

        this._tick = function() {
            self._render();
            if (self.left <= 0) {
                self.stop();
                if (self.onEnd) self.onEnd();
                return;
            }
            self.left--;
        };

        this._render = function() {
            if (!self.el) return;
            var m = String(Math.floor(self.left / 60)).padStart(2, '0');
            var s = String(self.left % 60).padStart(2, '0');
            self.el.textContent = m + ':' + s;
            if (self.left <= 30) self.el.style.color = 'var(--hard)';
            else if (self.left <= 60) self.el.style.color = 'var(--medium)';
            else self.el.style.color = '';
        };
    }
    window.CountdownTimer = CountdownTimer;

    // ============================================================
    // 12. DEBOUNCE
    // ============================================================
    function debounce(fn, delay) {
        delay = delay || 300;
        var t;
        return function() {
            var args = arguments;
            var ctx = this;
            clearTimeout(t);
            t = setTimeout(function() { fn.apply(ctx, args); }, delay);
        };
    }
    window.debounce = debounce;

    // ============================================================
    // 13. BOOKMARKS
    // ============================================================
    var Bookmarks = {
        _key: 'cfm_bookmarks',
        all: function() {
            try { return JSON.parse(localStorage.getItem(this._key)) || []; } catch (e) { return []; }
        },
        has: function(id) { return this.all().indexOf(id) !== -1; },
        toggle: function(id) {
            var list = this.all();
            var idx = list.indexOf(id);
            if (idx === -1) {
                list.push(id);
                showToast('Saqlandi 🔖', 'success', 1800);
            } else {
                list.splice(idx, 1);
                showToast('Saqlashdan olib tashlandi', 'info', 1800);
            }
            localStorage.setItem(this._key, JSON.stringify(list));
            return idx === -1;
        }
    };
    window.Bookmarks = Bookmarks;

    // ============================================================
    // 14. KEYBOARD SHORTCUTS
    // ============================================================
    var Shortcuts = {
        _map: {},
        register: function(combo, fn) { this._map[combo.toLowerCase()] = fn; },
        _parse: function(e) {
            var parts = [];
            if (e.ctrlKey || e.metaKey) parts.push('ctrl');
            if (e.shiftKey) parts.push('shift');
            if (e.altKey) parts.push('alt');
            parts.push(e.key.toLowerCase());
            return parts.join('+');
        }
    };

    document.addEventListener('keydown', function(e) {
        var tag = document.activeElement ? document.activeElement.tagName : '';
        if (tag === 'INPUT' || tag === 'TEXTAREA' || (document.activeElement && document.activeElement.isContentEditable)) return;
        var combo = Shortcuts._parse(e);
        if (Shortcuts._map[combo]) {
            e.preventDefault();
            Shortcuts._map[combo](e);
        }
    });

    Shortcuts.register('/', function() {
        var s = document.querySelector('.input[type="search"], #searchInput');
        if (s) { s.focus(); s.select(); }
    });
    window.Shortcuts = Shortcuts;

    // ============================================================
    // 15. FULLSCREEN
    // ============================================================
    function toggleFullscreen(el) {
        var target = el || document.documentElement;
        if (!document.fullscreenElement) {
            target.requestFullscreen().catch(function() {
                showToast('To\'liq ekran ishlamadi', 'warning');
            });
        } else {
            document.exitFullscreen().catch(function() {});
        }
    }
    window.toggleFullscreen = toggleFullscreen;

    // ============================================================
    // 16. HERO EDITOR MOCKUP (signature element — rotates subjects)
    //     Python renders as syntax-highlighted code.
    //     Matematika / Fizika render as LaTeX via KaTeX, laid out
    //     like short markdown steps (label + formula per line).
    // ============================================================
    function initEditorMockup() {
        var el = document.getElementById('heroEditor');
        if (!el) return;

        function tex(str) {
            if (window.katex) {
                try { return katex.renderToString(str, { throwOnError: false, displayMode: false }); }
                catch (e) { return str; }
            }
            return str;
        }

        var subjects = [
            {
                type: 'code',
                icon: 'code',
                label: 'Python',
                badgeClass: 'badge-easy',
                filename: 'two_sum.py',
                xp: '+10 XP',
                lines: [
                    '<span class="ln">1</span><span class="tok-kw">def</span> <span class="tok-fn">two_sum</span>(<span class="tok-var">nums</span>, <span class="tok-var">target</span>):',
                    '<span class="ln">2</span>&nbsp;&nbsp;<span class="tok-var">seen</span> = {}',
                    '<span class="ln">3</span>&nbsp;&nbsp;<span class="tok-kw">for</span> <span class="tok-var">i</span>, <span class="tok-var">n</span> <span class="tok-kw">in</span> <span class="tok-fn">enumerate</span>(<span class="tok-var">nums</span>):',
                    '<span class="ln">4</span>&nbsp;&nbsp;&nbsp;&nbsp;<span class="tok-kw">if</span> <span class="tok-var">target</span> - <span class="tok-var">n</span> <span class="tok-kw">in</span> <span class="tok-var">seen</span>:',
                    '<span class="ln">5</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="tok-kw">return</span> [<span class="tok-var">seen</span>[<span class="tok-var">target</span>-<span class="tok-var">n</span>], <span class="tok-var">i</span>]',
                    '<span class="ln">6</span>&nbsp;&nbsp;&nbsp;&nbsp;<span class="tok-var">seen</span>[<span class="tok-var">n</span>] = <span class="tok-var">i</span>'
                ],
                tests: [
                    'test_case_1 — [2,7,11,15], target=9',
                    'test_case_2 — [3,2,4], target=6',
                    'test_case_3 — [3,3], target=6'
                ]
            },
            {
                type: 'latex',
                icon: 'functions',
                label: 'Matematika',
                badgeClass: 'badge-info',
                filename: 'kvadrat_tenglama.md',
                xp: '+12 XP',
                comment: '# kvadrat tenglamani yech',
                steps: [
                    { label: 'Tenglama', formula: 'x^2 - 5x + 6 = 0' },
                    { label: 'Diskriminant', formula: 'D = b^2-4ac = 25-24=1' },
                    { label: 'Ildiz', formula: '\\sqrt{D} = 1' },
                    { label: 'Yechim', formula: 'x_1=\\dfrac{5+1}{2}=3,\\ \\ x_2=\\dfrac{5-1}{2}=2' }
                ],
                tests: [
                    { text: 'tekshiruv', formula: '3^2-5\\cdot3+6=0' },
                    { text: 'tekshiruv', formula: '2^2-5\\cdot2+6=0' },
                    { text: 'natija', formula: 'x_1=3,\\ x_2=2' }
                ]
            },
            {
                type: 'latex',
                icon: 'bolt',
                label: 'Fizika',
                badgeClass: 'badge-brand',
                filename: 'erkin_tushish.md',
                xp: '+15 XP',
                comment: '# erkin tushish: h=45 m, g=10 m/s²',
                steps: [
                    { label: 'Formula', formula: 't=\\sqrt{\\dfrac{2h}{g}}' },
                    { label: "Qo'yamiz", formula: 't=\\sqrt{\\dfrac{2\\cdot45}{10}}' },
                    { label: 'Soddalash', formula: 't=\\sqrt{9}' },
                    { label: 'Natija', formula: 't=3\\ s' }
                ],
                tests: [
                    { text: 'tezlik', formula: 'v=g\\cdot t=30\\ m/s' },
                    { text: 'energiya', formula: 'E=mgh' },
                    { text: 'natija', formula: 't=3\\ s' }
                ]
            }
        ];

        var body = document.getElementById('editorBody');
        var testsWrap = document.getElementById('editorTests');
        var xpPop = document.getElementById('editorXpPop');
        var filenameEl = document.getElementById('editorFilename');
        var badgeEl = document.getElementById('editorBadge');
        var dotsWrap = document.getElementById('editorSubjectDots');
        var idx = 0;

        if (dotsWrap) {
            dotsWrap.innerHTML = subjects.map(function(s, i) {
                return '<span class="subj-dot' + (i === 0 ? ' active' : '') + '" data-i="' + i + '">' +
                    '<span class="material-icons" aria-hidden="true">' + s.icon + '</span>' + s.label + '</span>';
            }).join('');
        }

        function buildCode(subject) {
            body.innerHTML = '';
            subject.lines.forEach(function(line, i) {
                var div = document.createElement('div');
                div.className = 'editor-code-line';
                div.style.animationDelay = (i * 0.22) + 's';
                div.innerHTML = line;
                body.appendChild(div);
            });
            var caret = document.createElement('span');
            caret.className = 'editor-cursor';
            body.appendChild(caret);
            return subject.lines.length;
        }

        function buildLatex(subject) {
            body.innerHTML = '';
            var comment = document.createElement('div');
            comment.className = 'editor-code-line latex-comment';
            comment.style.animationDelay = '0s';
            comment.textContent = subject.comment;
            body.appendChild(comment);

            subject.steps.forEach(function(step, i) {
                var div = document.createElement('div');
                div.className = 'editor-code-line latex-step';
                div.style.animationDelay = ((i + 1) * 0.35) + 's';
                div.innerHTML = '<span class="latex-label">' + step.label + '</span>' +
                    '<span class="latex-formula">' + tex(step.formula) + '</span>';
                body.appendChild(div);
            });
            var caret = document.createElement('span');
            caret.className = 'editor-cursor';
            body.appendChild(caret);
            return subject.steps.length + 1;
        }

        function render(subject) {
            filenameEl.textContent = subject.filename;
            badgeEl.textContent = subject.label;
            badgeEl.className = 'badge ' + subject.badgeClass;
            xpPop.textContent = subject.xp + ' ⚡';
            xpPop.classList.remove('show');

            var stepCount = subject.type === 'code' ? buildCode(subject) : buildLatex(subject);
            var stepDelay = subject.type === 'code' ? 220 : 350;

            testsWrap.innerHTML = subject.tests.map(function(t) {
                var content = typeof t === 'string' ? t : (t.text + ' — <span class="latex-formula">' + tex(t.formula) + '</span>');
                return '<div class="editor-test"><span class="chk"></span> ' + content + '</div>';
            }).join('');
            var tests = testsWrap.querySelectorAll('.editor-test');
            tests.forEach(function(t) { t.style.opacity = 0; });

            if (dotsWrap) {
                dotsWrap.querySelectorAll('.subj-dot').forEach(function(d, i) {
                    d.classList.toggle('active', subjects[i] === subject);
                });
            }

            var lineTime = stepCount * stepDelay + 350;

            tests.forEach(function(t, i) {
                setTimeout(function() {
                    t.style.opacity = '';
                    t.style.animation = 'test-in .3s ease forwards';
                    setTimeout(function() {
                        t.classList.add('pass');
                        var chk = t.querySelector('.chk');
                        if (chk) chk.innerHTML = '<span class="material-icons" style="font-size:11px;">check</span>';
                    }, 250);
                }, lineTime + i * 380);
            });

            setTimeout(function() {
                xpPop.classList.add('show');
            }, lineTime + tests.length * 380 + 250);
        }

        function next() {
            render(subjects[idx]);
            idx = (idx + 1) % subjects.length;
        }

        if (dotsWrap) {
            dotsWrap.addEventListener('click', function(e) {
                var dot = e.target.closest('.subj-dot');
                if (!dot) return;
                clearInterval(cycle);
                idx = parseInt(dot.dataset.i, 10);
                render(subjects[idx]);
                idx = (idx + 1) % subjects.length;
                cycle = setInterval(next, 8000);
            });
        }

        next();
        var cycle = setInterval(next, 8000);
    }
    window.initEditorMockup = initEditorMockup;

    // ============================================================
    // 17. INIT
    // ============================================================
    document.addEventListener('DOMContentLoaded', function() {
        injectNavbar();      // 🆕 avval navbar HTML inject qilinadi
        renderTopbarUser();  // keyin login holatiga qarab to'ldiriladi
        highlightNav();
        initHintToggles();
        initEditorMockup();

        // 🆕 Global SSE — login qilgan bo'lsa, butun sayt uchun bitta ulanish ochamiz
        if (Auth.isLoggedIn()) RCEvents.connect();

        if (!document.getElementById('toast-container')) {
            var c = document.createElement('div');
            c.id = 'toast-container';
            document.body.appendChild(c);
        }

        document.querySelectorAll('[data-bookmark]').forEach(function(btn) {
            var id = btn.dataset.bookmark;
            if (Bookmarks.has(id)) btn.classList.add('active');
            btn.addEventListener('click', function() {
                var added = Bookmarks.toggle(id);
                btn.classList.toggle('active', added);
            });
        });

        var heroTimer = document.getElementById('heroTimer');
        if (heroTimer) {
            var seconds = 18 * 3600 + 42 * 60 + 5;
            setInterval(function() {
                if (seconds <= 0) return;
                seconds--;
                var h = String(Math.floor(seconds / 3600)).padStart(2, '0');
                var m = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
                var s = String(seconds % 60).padStart(2, '0');
                heroTimer.textContent = h + ':' + m + ':' + s;
            }, 1000);
        }

        setTimeout(function() {
            showToast('Xush kelibsiz! 🔥', 'success', 2500);
        }, 800);
    });

})();