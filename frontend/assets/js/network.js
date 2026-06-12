// ==================== LINKED LIST NODE ====================
class Node {
    constructor(data) {
        this.data = data;
        this.next = null;
        this.prev = null;
    }
}

// ==================== DEQUE (O(1) hamma amallar) ====================
class Deque {
    constructor() {
        this.head = null;
        this.tail = null;
        this.size = 0;
    }

    pushRight(data) {
        const node = new Node(data);
        if (!this.head) {
            this.head = this.tail = node;
        } else {
            node.prev = this.tail;
            this.tail.next = node;
            this.tail = node;
        }
        this.size++;
    }

    pushLeft(data) {
        const node = new Node(data);
        if (!this.head) {
            this.head = this.tail = node;
        } else {
            node.next = this.head;
            this.head.prev = node;
            this.head = node;
        }
        this.size++;
    }

    popLeft() {
        if (!this.head) return null;
        const data = this.head.data;
        if (this.size === 1) {
            this.head = this.tail = null;
        } else {
            this.head = this.head.next;
            this.head.prev = null;
        }
        this.size--;
        return data;
    }

    popRight() {
        if (!this.tail) return null;
        const data = this.tail.data;
        if (this.size === 1) {
            this.head = this.tail = null;
        } else {
            this.tail = this.tail.prev;
            this.tail.next = null;
        }
        this.size--;
        return data;
    }

    peekLeft() { return this.head?.data ?? null; }
    peekRight() { return this.tail?.data ?? null; }
    isEmpty() { return this.size === 0; }
    
    clear() {
        this.head = this.tail = null;
        this.size = 0;
    }

    *[Symbol.iterator]() {
        let current = this.head;
        while (current) {
            yield current.data;
            current = current.next;
        }
    }
}

const Event = {
    Sabmit: "s",
    Run: "r",
    Commint: "c"
}
// ==================== WEB SOCKET (AVTOMATIK QAYTA ULANISH + NAVBAT) ====================
class WS {
    constructor(userId, url = "wss://api.42.uz/track") {
        this.userId = userId;
        this.url = url;
        this.ws = null;
        this.queue = new Deque();
        this.reconnectDelay = 1000;
        this.maxDelay = 16000;
        this.attempts = 0;
        this.heartbeatInterval = null;
        this.isConnecting = false;
    }

    connect() {
        if (this.isConnecting || this.ws?.readyState === WebSocket.OPEN) return;
        this.isConnecting = true;
        
        try {
            this.ws = new WebSocket(`${this.url}?userId=${this.userId}`);
            this.ws.onopen = () => {
                console.log("✅ WS ulandi");
                this.attempts = 0;
                this.reconnectDelay = 1000;
                this.isConnecting = false;
                this._startHeartbeat();
                this._flush();
                this.send("status", { status: "online" });
            };
            
            this.ws.onmessage = (e) => {
                const msg = JSON.parse(e.data);
                if (msg.type === "pong") return;
                console.log("📨", msg);
            };
            
            this.ws.onclose = () => {
                console.log("⚠️ WS uzildi");
                this._cleanup();
                this._reconnect();
            };
            
            this.ws.onerror = (err) => {
                console.error("❌ WS xato:", err);
                this.ws?.close();
            };
        } catch (err) {
            this.isConnecting = false;
            this._reconnect();
        }
    }

    send(type, payload, priority = "normal") {
        const packet = { type, userId: this.userId, payload, priority, ts: Date.now() };
        
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(packet));
        } else {
            // Navbat to'lib ketganda past prioritylilarni o'chirish
            if (this.queue.size >= 50) {
                if (priority === "normal") return;
                this.queue.popLeft(); // Eng eskisini o'chir
            }
            this.queue.pushRight(packet);
        }
    }

    _flush() {
        while (!this.queue.isEmpty() && this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(this.queue.popLeft()));
        }
    }

    _startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            if (this.ws?.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: "ping", ts: Date.now() }));
            }
        }, 15000);
    }

    _reconnect() {
        const delay = Math.min(this.maxDelay, this.reconnectDelay * Math.pow(2, this.attempts++));
        setTimeout(() => this.connect(), delay + (Math.random() * 200));
        this.reconnectDelay = delay;
    }

    _cleanup() {
        if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);
    }

    disconnect() {
        this._cleanup();
        this.ws?.close();
        this.ws = null;
    }
}

// ==================== CACHE (IndexedDB) ====================
class Cache {
    constructor(ttl = 300000) {
        this.ttl = ttl;
        this.db = null;
        this._init();
    }

    async _init() {
        this.db = new Dexie("AppCache");
        this.db.version(1).stores({ cache: "key, expireAt" });
    }

    async get(key) {
        if (!this.db) await this._init();
        const entry = await this.db.cache.get(key);
        if (!entry) return null;
        if (Date.now() > entry.expireAt) {
            await this.db.cache.delete(key);
            return null;
        }
        return entry.data;
    }

    async set(key, data) {
        if (!this.db) await this._init();
        await this.db.cache.put({
            key,
            data,
            expireAt: Date.now() + this.ttl
        });
    }

    async clear() {
        if (this.db) await this.db.cache.clear();
    }
}

// ==================== REST API (GET + KESH) ====================
class API {
    constructor(baseURL, cache = null) {
        this.baseURL = baseURL;
        this.cache = cache;
    }

    async get(endpoint, options = {}) {
        const url = this.baseURL + endpoint;
        const key = options.params ? `${url}?${new URLSearchParams(options.params)}` : url;
        
        // Keshdan o'qish
        if (this.cache && options.cache !== false) {
            const cached = await this.cache.get(key);
            if (cached) return cached;
        }
        
        // So'rov yuborish
        const query = options.params ? `?${new URLSearchParams(options.params)}` : "";
        const res = await fetch(`${url}${query}`, {
            headers: { 'Content-Type': 'application/json', ...options.headers }
        });
        
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        
        // Keshga yozish
        if (this.cache && options.cache !== false) {
            await this.cache.set(key, data);
        }
        
        return data;
    }
}
