# CodeForge — Next.js Platform Design Specification
> LeetCode + Boot.dev + 42.uz inspired platform
> **AI Agent: Bu hujjat yagona haqiqat manbai. Har bir bo'limni so'zsiz bajaring.**

---

## Tech Stack

```
Framework:     Next.js 14+ (App Router)
Language:      TypeScript
Styling:       Tailwind CSS + CSS Variables
State:         Zustand
Data fetching: TanStack Query (React Query)
Auth:          JWT (httpOnly cookie) — faqat OTP, register yo'q
Editor:        Monaco Editor (@monaco-editor/react) — lazy load
WS:            native WebSocket + reconnect hook
DB:            PostgreSQL via Django ORM (schema quyida)
Isolate:       ioi/isolate sandbox (kod bajarish uchun)
```

---

## Design Tokens

```css
:root {
  --bg-base:       #0b0f1a;
  --bg-surface:    #111827;
  --bg-raised:     #1a2234;
  --bg-overlay:    #1e2d40;
  --bg-hover:      #243044;

  --brand:         #00d4aa;
  --brand-dim:     #00d4aa22;
  --brand-border:  #00d4aa44;

  --accent:        #6366f1;
  --accent-dim:    #6366f122;

  --easy:          #22c55e;
  --medium:        #f59e0b;
  --hard:          #ef4444;

  --text-1:        #f1f5f9;
  --text-2:        #94a3b8;
  --text-3:        #475569;

  --border:        #1e293b;
  --border-2:      #334155;

  --success:       #22c55e;
  --error:         #ef4444;
  --warning:       #f59e0b;

  --font-ui:   'Sora', sans-serif;
  --font-code: 'JetBrains Mono', monospace;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
}
```

---

## App Router Struktura

```
app/
├── (auth)/
│   ├── login/page.tsx              OTP login
│   └── verify/page.tsx             6-digit OTP confirm
│
├── (platform)/
│   ├── layout.tsx                  Navbar + sidebar
│   ├── page.tsx                    Dashboard / Home
│   │
│   ├── problems/
│   │   ├── page.tsx                Problem list
│   │   └── [slug]/page.tsx         Problem detail (adaptive)
│   │
│   ├── contests/
│   │   ├── page.tsx                Contest list
│   │   └── [id]/page.tsx           Contest detail (adaptive)
│   │
│   ├── courses/
│   │   ├── page.tsx                Course catalog
│   │   └── [slug]/
│   │       ├── page.tsx            Course detail
│   │       └── [lesson]/page.tsx   Lesson page (adaptive)
│   │
│   ├── leaderboard/page.tsx
│   └── profile/[username]/page.tsx
│
└── api/
    ├── auth/send-otp/route.ts
    ├── auth/verify-otp/route.ts
    └── [...proxy]/route.ts         Django API proxy
```

---

## Auth — OTP Only (Register yo'q)

### DB Model (Django BaseUser)
```python
class BaseUser(AbstractBaseUser):
    phone        = models.CharField(max_length=20, unique=True, null=True, blank=True)
    telegram_id  = models.BigIntegerField(unique=True, null=True, blank=True)
    username     = models.CharField(max_length=50, unique=True)
    full_name    = models.CharField(max_length=200, blank=True)
    is_active    = models.BooleanField(default=True)
    date_joined  = models.DateTimeField(auto_now_add=True)
    # OTP: Redis da saqlanadi, DB ga tushmaydi
    # OTP format: 6 raqam, masalan "131414"
```

### API Contracts

```typescript
// POST /api/auth/send-otp/
// Request:
{ phone: string }                  // "+998901234567"
// Response (success):
{ message: "OTP yuborildi", expires_in: 120 }
// Response (error — register yo'q, faqat mavjud user):
{ error: "Foydalanuvchi topilmadi" }

// POST /api/auth/verify-otp/
// Request:
{ phone: string, otp: string }     // otp: "131414"
// Response (success):
{ access: string, refresh: string, user: UserDTO }
// Response (error):
{ error: "Kod noto'g'ri yoki muddati o'tgan" }

// POST /api/auth/refresh/
{ refresh: string }
// Response:
{ access: string }
```

### `/login` Page Layout

```
Layout: Centered card 380px, dark, dot-grid background

┌────────────────────────────────────┐
│         🔥 CodeForge               │
│                                    │
│   Platformaga kirish               │
│                                    │
│  ┌──────────────────────────────┐  │
│  │ +998 │ 90 123 45 67         │  │
│  └──────────────────────────────┘  │
│                                    │
│  [ Kodni yuborish → ]  (CTA)       │
│                                    │
│  ─────────── yoki ───────────      │
│                                    │
│  [ Telegram orqali kirish ]        │
│                                    │
│  ⚠️ Ro'yxatdan o'tish mavjud emas  │
│     Faqat mavjud foydalanuvchilar  │
└────────────────────────────────────┘

States:
  - idle: default
  - loading: spinner in button
  - error "Raqam topilmadi": red border + shake animation
  - success: navigate to /verify?phone=...
```

### `/verify` — 6-Digit OTP

```
┌────────────────────────────────────┐
│  ← Orqaga                          │
│                                    │
│   Kodni kiriting                   │
│   +998 90 *** ** 67 ga yuborildi   │
│                                    │
│  ┌──┐ ┌──┐ ┌──┐  ┌──┐ ┌──┐ ┌──┐  │
│  │1 │ │3 │ │1 │  │4 │ │1 │ │4 │  │
│  └──┘ └──┘ └──┘  └──┘ └──┘ └──┘  │
│         (3 + 3 guruhlangan)        │
│                                    │
│   ⏱ Qayta yuborish: 01:48         │
└────────────────────────────────────┘

OTP Input rules:
  - 6 alohida <input maxLength={1} inputMode="numeric" />
  - Har kirishdan keyin focus keyingiga
  - Backspace → oldingiga
  - Paste → hammasi to'ladi
  - Noto'g'ri → shake + red border
  - To'g'ri → loading → redirect /
```

```typescript
// components/auth/OtpInput.tsx
'use client';
import { useRef, KeyboardEvent, ClipboardEvent } from 'react';

export function OtpInput({ length = 6, onChange }: {
  length?: number;
  onChange: (value: string) => void;
}) {
  const inputs = useRef<(HTMLInputElement | null)[]>([]);

  const handleKey = (i: number, e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !e.currentTarget.value && i > 0)
      inputs.current[i - 1]?.focus();
  };
  const handleInput = (i: number, val: string) => {
    if (!/^\d?$/.test(val)) return;
    if (val && i < length - 1) inputs.current[i + 1]?.focus();
    onChange(inputs.current.map(el => el?.value ?? '').join(''));
  };
  const handlePaste = (e: ClipboardEvent) => {
    e.preventDefault();
    const digits = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, length);
    digits.split('').forEach((d, i) => { if (inputs.current[i]) inputs.current[i]!.value = d; });
    inputs.current[Math.min(digits.length, length - 1)]?.focus();
    onChange(digits.padEnd(length, '').slice(0, length));
  };

  return (
    <div style={{ display: 'flex', gap: 8 }} onPaste={handlePaste}>
      {Array.from({ length }).map((_, i) => (
        <>
          {i === 3 && <span style={{ width: 12 }} />}  {/* 3+3 gap */}
          <input key={i} ref={el => { inputs.current[i] = el; }}
            maxLength={1} inputMode="numeric" autoFocus={i === 0}
            onChange={e => handleInput(i, e.target.value)}
            onKeyDown={e => handleKey(i, e)}
            style={{
              width: 52, height: 64, textAlign: 'center',
              fontSize: 24, fontFamily: 'var(--font-code)',
              background: 'var(--bg-raised)', border: '1.5px solid var(--border-2)',
              borderRadius: 'var(--radius-md)', color: 'var(--text-1)',
              outline: 'none', transition: 'border-color 150ms',
            }}
          />
        </>
      ))}
    </div>
  );
}
```

---

## Adaptive Content System

```
Platform uchta asosiy content turini qo'llab-quvvatlaydi.
UI avtomatik moslashadi — alohida page yo'q.

┌────────────────────────────────────────────────────┐
│  Content Types                                     │
│                                                    │
│  💻 Problem  — Monaco editor + ioi/isolate sandbox │
│  📝 Test     — MCQ variantlar + timer              │
│  🎬 Video    — HLS stream + transcript             │
│                                                    │
│  Bu uchala QAYERDA bo'lishi mumkin:                │
│  • Mustaqil /problems/:slug                        │
│  • Course lesson ichida                            │
│  • Contest ichida                                  │
└────────────────────────────────────────────────────┘
```

```typescript
// lib/content-detector.ts
export type ContentType = 'problem' | 'test' | 'video' | 'mixed';

export function detectContentType(item: {
  problems?: unknown[];
  tests?: unknown[];
  video_url?: string | null;
}): ContentType {
  const has = {
    problems: (item.problems?.length ?? 0) > 0,
    tests:    (item.tests?.length ?? 0) > 0,
    video:    !!item.video_url,
  };
  const count = Object.values(has).filter(Boolean).length;
  if (count > 1) return 'mixed';
  if (has.problems) return 'problem';
  if (has.tests)    return 'test';
  if (has.video)    return 'video';
  return 'mixed';
}
```

---

## Problems Page — `/problems`

### Mock Data
```json
[
  {
    "id": 1, "title": "Ikki son yig'indisi", "slug": "two-sum",
    "difficulty": "easy", "category": "Array", "xp": 100,
    "acceptance_rate": 72.4, "tags": ["Array", "Hash Table"],
    "is_solved": true, "submission_count": 12840, "has_video": true
  },
  {
    "id": 2, "title": "Bog'liq ro'yxatni qaytarish", "slug": "reverse-linked-list",
    "difficulty": "easy", "category": "Linked List", "xp": 100,
    "acceptance_rate": 68.1, "tags": ["Linked List", "Recursion"],
    "is_solved": false, "submission_count": 9234, "has_video": false
  },
  {
    "id": 3, "title": "Eng uzun substroq", "slug": "longest-substring",
    "difficulty": "medium", "category": "String", "xp": 250,
    "acceptance_rate": 33.8, "tags": ["Sliding Window"],
    "is_solved": false, "submission_count": 6712, "has_video": true
  },
  {
    "id": 4, "title": "Median ikkita massivdan", "slug": "median-two-arrays",
    "difficulty": "hard", "category": "Binary Search", "xp": 500,
    "acceptance_rate": 14.2, "tags": ["Binary Search", "Divide & Conquer"],
    "is_solved": false, "submission_count": 2341, "has_video": false
  },
  {
    "id": 5, "title": "LRU Cache", "slug": "lru-cache",
    "difficulty": "medium", "category": "Design", "xp": 300,
    "acceptance_rate": 41.6, "tags": ["Hash Table", "Linked List"],
    "is_solved": true, "submission_count": 7890, "has_video": true
  }
]
```

### Layout (Desktop)

```
┌─[Sticky filters]───────────────────────────────────────────────┐
│  [🔍 Masala qidirish...]  [🟢 Oson▼]  [Array▼]  [Tags▼]      │
│  Active chips: [🟢 Oson ×]  [Array ×]                          │
├─────────────────────────────────────────────────────┬───────────┤
│  # │ Sarlavha            │ Qiyinlik │   %  │   XP   │  PANEL   │
│ ───┼─────────────────────┼──────────┼──────┼────────│          │
│  1 │ ✅ Ikki son...      │  🟢 Oson │ 72%  │ ⚡100  │ Yechildi │
│    │    📹 Array         │          │      │        │  2 / 5   │
│ ───┼─────────────────────┼──────────┼──────┼────────│          │
│  2 │ — Bog'liq ro'yxat.. │  🟢 Oson │ 68%  │ ⚡100  │ 🟢 2/2  │
│    │    Linked List       │          │      │        │ 🟡 0/2  │
│ ───┼─────────────────────┼──────────┼──────┼────────│ 🔴 0/1  │
│  3 │ — Eng uzun substroq │ 🟡 O'rta │ 34%  │ ⚡250  │          │
│    │    📹 String         │          │      │        │ Streak   │
│ ───┼─────────────────────┼──────────┼──────┼────────│ 🔥 7 kun │
│  4 │ — Median ikki mass. │  🔴 Qiyn │ 14%  │ ⚡500  │          │
│    │    Binary Search     │          │      │        │ XP: 4750 │
└────┴─────────────────────┴──────────┴──────┴────────┴───────────┘

📹 = has_video (video yechim mavjud)
✅ = is_solved
Hover: left border 3px brand-color, bg slight lift
```

---

## Problem Detail — `/problems/[slug]`

### Mock Data (Full)
```json
{
  "id": 1, "title": "Ikki son yig'indisi", "slug": "two-sum",
  "difficulty": "easy", "xp": 100, "category": "Array",
  "tags": ["Array", "Hash Table"],
  "description": "Berilgan `nums` ro'yxati va `target` son uchun indekslarni toping. Ikkita son yig'indisi `target` ga teng bo'lishi kerak.",
  "time_limit": 2000, "memory_limit": 256,
  "acceptance_rate": 72.4, "submission_count": 12840,
  "examples": [
    { "input": "nums = [2, 7, 11, 15]\ntarget = 9", "output": "[0, 1]", "explanation": "nums[0] + nums[1] = 2 + 7 = 9" },
    { "input": "nums = [3, 2, 4]\ntarget = 6",      "output": "[1, 2]", "explanation": "nums[1] + nums[2] = 2 + 4 = 6" }
  ],
  "hints": ["Hash map ishlatishni o'ylab ko'ring", "target - nums[i] ni map dan qidiring"],
  "challenges": ["O(n) vaqt murakkabligida yeching", "Extra xotira ishlatmasdan yeching"],
  "constraints": ["2 ≤ nums.length ≤ 10⁴", "-10⁹ ≤ nums[i] ≤ 10⁹"],
  "functions": {
    "python":     "def twoSum(nums: List[int], target: int) -> List[int]:\n    pass",
    "javascript": "function twoSum(nums, target) {\n    \n}",
    "cpp":        "class Solution {\npublic:\n    vector<int> twoSum(vector<int>& nums, int target) {\n        \n    }\n};",
    "go":         "func twoSum(nums []int, target int) []int {\n    \n}",
    "rust":       "impl Solution {\n    pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {\n        \n    }\n}"
  },
  "has_video": true,
  "video": {
    "title": "Two Sum — Hash Map yondashuvi", "duration": "08:34",
    "hls_url": "https://cdn.example.com/videos/two-sum.m3u8",
    "mp4_url": "https://cdn.example.com/videos/two-sum.mp4",
    "thumbnail": "https://cdn.example.com/thumbs/two-sum.jpg"
  }
}
```

### Split Panel Layout

```
┌──[Left 42%]────────────────────┬──[Right 58%]──────────────────┐
│ Tab: [Masala] [Yechimlar] [📹] │ [Python▼]  [▶ Run] [⬆ Submit]│
│                                │                               │
│  Two Sum                       │ ┌─Monaco Editor─────────────┐ │
│  🟢 Oson   ⚡ 100 XP           │ │                           │ │
│  ⏱ 2000ms  💾 256MB           │ │  def twoSum(              │ │
│                                │ │      nums: List[int],     │ │
│  Tavsif (Markdown rendered)    │ │      target: int          │ │
│  ...                           │ │  ) -> List[int]:          │ │
│                                │ │      pass                 │ │
│  Misol 1:                      │ └───────────────────────────┘ │
│  ┌──────────────────────────┐  │                               │
│  │ Input:  nums=[2,7,11,15] │  │ ─── Console Output ───────── │
│  │         target=9         │  │ ┌─────────────────────────┐  │
│  │ Output: [0, 1]           │  │ │                         │  │
│  │ Izoh:   2+7=9            │  │ │  Hali bajarilmadi...    │  │
│  └──────────────────────────┘  │ │                         │  │
│                                │ └─────────────────────────┘  │
│  ▶ Hint 1 (accordion)         │                               │
│  ▶ Hint 2 (accordion)         │ [+ O'z testingni qo'sh]       │
│                                │ ┌─────────────────────────┐  │
│  Challenges:                   │ │ Input:    [2,7,11]  9   │  │
│  ○ O(n) da yeching             │ │ Expected: [0,1]         │  │
│  ○ Extra xotirasiz             │ └─────────────────────────┘  │
│                                │                               │
│  Constraints: ...              │                               │
└────────────────────────────────┴───────────────────────────────┘

Video tab (has_video=true bo'lsa ko'rinadi):
  [Masala] [Yechimlar] [📹 Video]
  Video tab ochilganda:
  ┌────────────────────────────────────────┐
  │ [HLS Player — hls.js]                 │
  │ ▶ Two Sum — Hash Map  08:34           │
  │ [████████████░░░░░░░] 4:12 / 8:34    │
  └────────────────────────────────────────┘
```

### WebSocket — Code Execution (ioi/isolate API)

```typescript
// ws://api/ws/execute/
type ExecSend = {
  type: 'run' | 'submit';
  problem_id: number;
  language: 'python' | 'javascript' | 'cpp' | 'go' | 'rust';
  code: string;
  custom_input?: string;   // faqat 'run' uchun
  token: string;
};

type ExecMessage =
  | { type: 'queued';        data: { job_id: string; position: number } }
  | { type: 'running';       data: { job_id: string; test_id: number } }
  | { type: 'test_result';   data: {
      test_id: number;
      status: 'passed' | 'failed' | 'tle' | 'mle' | 'runtime_error';
      time_ms: number;
      memory_mb: number;
      expected?: string;
      got?: string;
    }}
  | { type: 'compile_error'; data: { message: string; line?: number } }
  | { type: 'done';          data: {
      passed: number;
      total: number;
      xp_earned?: number;    // faqat submit + hammasi o'tsa
      new_level?: number;    // level up bo'lsa
    }};

// UI:
//  queued      → "Navbatda (#3)..."
//  running     → "Test 1 tekshirilmoqda..."
//  test_result → row qo'shiladi, 150ms delay bilan animated
//  done+pass   → konfetti + "+100 XP" toast + XP animation
//  done+fail   → qizil banner, xato ko'rsatiladi
//  compile_err → Monaco editor da squiggly line
```

---

## Contests Page — `/contests`

### Mock Data
```json
[
  {
    "id": 1, "title": "Weekly Contest #47",
    "type": "open", "status": "ongoing", "difficulty": "medium",
    "content_types": ["problem"],
    "start_time": "2026-05-11T14:00:00Z",
    "end_time": "2026-05-11T16:30:00Z",
    "duration": "2 soat 30 daqiqa",
    "participants_count": 342, "max_participants": 1000,
    "problems_count": 4, "tests_count": 0,
    "prizes": ["1-o'rin: 5000 XP", "2-o'rin: 3000 XP", "3-o'rin: 1500 XP"],
    "is_featured": true, "is_registered": true, "requires_key": false
  },
  {
    "id": 2, "title": "Algorithm Masters Cup",
    "type": "open", "status": "upcoming", "difficulty": "hard",
    "content_types": ["problem"],
    "start_time": "2026-05-15T10:00:00Z",
    "end_time": "2026-05-15T14:00:00Z",
    "duration": "4 soat",
    "participants_count": 89, "max_participants": 500,
    "problems_count": 5, "tests_count": 0,
    "prizes": ["1-o'rin: $100", "2-o'rin: $50"],
    "is_featured": true, "is_registered": false, "requires_key": false
  },
  {
    "id": 3, "title": "Aralash Tanlov — Kod & Test",
    "type": "open", "status": "upcoming", "difficulty": "medium",
    "content_types": ["problem", "test"],
    "start_time": "2026-05-18T18:00:00Z",
    "end_time": "2026-05-18T20:30:00Z",
    "duration": "2 soat 30 daqiqa",
    "participants_count": 201, "max_participants": 1000,
    "problems_count": 3, "tests_count": 10,
    "prizes": ["1-o'rin: 3000 XP"],
    "is_featured": false, "is_registered": false, "requires_key": false
  },
  {
    "id": 4, "title": "TechCorp Yopiq Tanlov",
    "type": "private", "status": "upcoming", "difficulty": "hard",
    "content_types": ["problem", "test"],
    "start_time": "2026-05-20T09:00:00Z",
    "end_time": "2026-05-20T12:00:00Z",
    "duration": "3 soat",
    "participants_count": 12, "max_participants": 50,
    "problems_count": 4, "tests_count": 5,
    "prizes": ["Ish taklifi", "500,000 so'm"],
    "is_featured": false, "is_registered": false,
    "requires_key": true
  }
]
```

### Contest Card UI

```
OCHIQ — LIVE:
┌──────────────────────────────────────────┐
│ 🔴 LIVE                 ⏱ 1:23:45 qoldi │
│ Weekly Contest #47                        │
│ ──────────────────────────────────────── │
│ 342/1000 👤   🟡 O'rtacha   2s 30d      │
│ [💻 Masala ×4]                           │
│ 🏆 5000XP  3000XP  1500XP               │
│ [Davom etish →]                          │
└──────────────────────────────────────────┘

YOPIQ — UPCOMING:
┌──────────────────────────────────────────┐
│ 🔒 YOPIQ               20-may 09:00      │
│ TechCorp Yopiq Tanlov                    │
│ ──────────────────────────────────────── │
│ 12/50 👤     🔴 Qiyin     3 soat        │
│ [💻 Masala ×4]  [📝 Test ×5]            │
│ 🏆 Ish taklifi   500,000 so'm           │
│                                          │
│ ┌────────────────────────────────────┐   │
│ │ 🔑 Kirish kodini kiriting...       │   │
│ └────────────────────────────────────┘   │
│ [Tasdiqlash]                             │
└──────────────────────────────────────────┘

ARALASH (problem + test):
  [💻 Masala ×3]  [📝 Test ×10]  (ikkalasi ko'rinadi)

Filter tabs: [Hammasi] [Davom etmoqda] [Kutilmoqda] [Yakunlangan]
             [Ochiq] [Yopiq]
```

### WebSocket — Contest Live Updates

```typescript
// ws://api/ws/contest/{id}/
type ContestMessage =
  | { type: 'time_update';      data: { seconds_left: number } }
  | { type: 'status_change';    data: { status: 'ongoing' | 'ended' } }
  | { type: 'participant_join'; data: { count: number } };

// ws://api/ws/contest/{id}/leaderboard/
type LeaderboardMessage =
  | { type: 'score_update'; data: {
      username: string;
      rank: number;
      old_rank: number;
      total_score: number;
      problem_index?: number;
      test_score?: number;
    }};
```

---

## Contest Detail — `/contests/[id]`

### Adaptive Layouts

```typescript
// Adaptive render — content_types ga qarab
function ContestDetailPage({ contest }) {
  const type = detectContestType(contest);

  if (type === 'problem') return <ContestProblemLayout />;
  if (type === 'test')    return <ContestTestLayout />;
  return <ContestMixedLayout />;   // problem + test
}

// Mixed layout sidebar:
// [Masalalar] bo'lim → [problem1, problem2, ...]
// [Testlar]   bo'lim → [test1, test2, ...]
// O'ng: Monaco yoki MCQ (tanlanganga qarab)
```

### Leaderboard Mock Data
```json
{
  "leaderboard": [
    {
      "rank": 1, "username": "sardor_dev",
      "total_score": 1400, "problems_solved": 4, "tests_score": 0,
      "finish_time": "01:12:34", "problem_scores": [300, 300, 400, 400], "penalty": 2
    },
    {
      "rank": 2, "username": "malika_codes",
      "total_score": 1100, "problems_solved": 3, "tests_score": 0,
      "finish_time": "01:45:22", "problem_scores": [300, 400, 400, 0], "penalty": 1
    },
    {
      "rank": 3, "username": "jasur_algo",
      "total_score": 950, "problems_solved": 2, "tests_score": 350,
      "finish_time": null, "problem_scores": [300, 300, 0, 0], "penalty": 0
    }
  ]
}
```

```
Leaderboard (mixed contest):
Rank │ User        │ Total  │ 💻 Kod │ 📝 Test │ Vaqt
─────┼─────────────┼────────┼────────┼─────────┼──────
  1  │ sardor_dev  │  1400  │  4/4   │   —     │ 1:12
  2  │ malika      │  1100  │  3/4   │   —     │ 1:45
  3  │ jasur_algo  │   950  │  2/4   │ 350/500 │ —
```

---

## Courses Page — `/courses`

### Mock Data
```json
[
  {
    "id": 1, "title": "Python asoslari", "slug": "python-basics",
    "description": "Noldan Python o'rganing.",
    "price": 0, "discount_price": null,
    "total_lessons": 42, "completed_lessons": 18,
    "modules_count": 6, "estimated_hours": 24,
    "difficulty": "Boshlang'ich", "rating": 4.8, "students_count": 1240,
    "is_enrolled": true,
    "content_breakdown": { "video": 28, "problem": 10, "test": 4 }
  },
  {
    "id": 2, "title": "Ma'lumotlar tuzilmasi", "slug": "data-structures",
    "description": "Array, LinkedList, Stack, Queue, Tree, Graph.",
    "price": 299000, "discount_price": 199000,
    "total_lessons": 68, "completed_lessons": 0,
    "modules_count": 8, "estimated_hours": 40,
    "difficulty": "O'rta", "rating": 4.9, "students_count": 890,
    "is_enrolled": false,
    "content_breakdown": { "video": 30, "problem": 35, "test": 3 }
  },
  {
    "id": 3, "title": "Django Backend", "slug": "django-backend",
    "description": "REST API, JWT, PostgreSQL, Docker.",
    "price": 499000, "discount_price": null,
    "total_lessons": 85, "completed_lessons": 0,
    "modules_count": 10, "estimated_hours": 60,
    "difficulty": "Yuqori", "rating": 4.7, "students_count": 432,
    "is_enrolled": false,
    "content_breakdown": { "video": 50, "problem": 30, "test": 5 }
  }
]
```

### Course Card

```
┌──────────────────────────────────┐
│ [Python badge top-right]         │
│ [Course icon / illustration]     │
│ Python asoslari                  │
│ ⭐4.8  •  1,240 talaba          │
│ Boshlang'ich  •  24 soat        │
│                                  │
│ Kontent: 🎬28  💻10  📝4        │
│                                  │
│ [████████░░░░░░] 18/42  43%     │
│                                  │
│ BEPUL         [Davom etish →]   │
└──────────────────────────────────┘

(Pullik + chegirma):
│ ~~299,000~~  199,000 so'm       │
│               [Sotib olish →]   │
```

---

## Lesson Page — `/courses/[slug]/[lesson]`

### Mock Data
```json
{
  "id": 10, "title": "Hash Map bilan Two Sum", "slug": "hash-map-two-sum",
  "order": 5,
  "modul": { "id": 2, "title": "Massivlar" },
  "course": { "slug": "python-basics", "title": "Python asoslari" },
  "video_url": "https://cdn.example.com/lessons/hash-map.m3u8",
  "video_duration": "12:34",
  "content_md": "# Hash Map\n\nHash map — kalit-qiymat juftliklarini saqlaydi...\n\n## O'rnatish\n```python\nhashmap = {}\n```",
  "problems": [
    { "id": 1, "title": "Two Sum", "slug": "two-sum", "difficulty": "easy", "xp": 100, "is_solved": false }
  ],
  "tests": [
    { "id": 5, "title": "Hash Map bilimini tekshirish", "question_count": 5, "duration_minutes": 10, "is_completed": false, "passing_score": 70 }
  ],
  "next_lesson": { "slug": "binary-search-intro", "title": "Binary Search" },
  "prev_lesson":  { "slug": "arrays-basics", "title": "Array asoslari" },
  "is_completed": false
}
```

### Adaptive Lesson Layout

```typescript
// Render order: Video → Markdown → Problems → Tests → Plagiarism notice → Nav
function LessonPage({ lesson }) {
  return (
    <div className="lesson-container">
      {/* 1. Video (agar mavjud) */}
      {lesson.video_url && (
        <section>
          <VideoPlayer src={lesson.video_url} duration={lesson.video_duration} />
        </section>
      )}

      {/* 2. Matn kontent */}
      {lesson.content_md && (
        <section className="prose">
          <MarkdownContent content={lesson.content_md} />
        </section>
      )}

      {/* 3. Masalalar (agar mavjud) */}
      {lesson.problems?.length > 0 && (
        <section>
          <h2>💻 Amaliy masalalar</h2>
          {lesson.problems.map(p => (
            <EmbeddedProblemCard key={p.id} problem={p} />
          ))}
          {/* Plagiarism ogohlantirish */}
          <PlagiarismNotice />
        </section>
      )}

      {/* 4. Testlar (agar mavjud) */}
      {lesson.tests?.length > 0 && (
        <section>
          <h2>📝 Bilimni tekshirish</h2>
          {lesson.tests.map(t => (
            <TestCard key={t.id} test={t} />
          ))}
        </section>
      )}

      {/* 5. Navigatsiya */}
      <LessonNavigation
        prev={lesson.prev_lesson}
        next={lesson.next_lesson}
        isCompleted={lesson.is_completed}
      />
    </div>
  );
}
```

### Plagiarism Notice

```
⚠️ Komponent — har doim coding masalalar pastida ko'rinadi, dismiss yo'q:

┌──────────────────────────────────────────────────────┐
│ ⚠️  Plagiarism (nusxa ko'chirish) haqida             │
│                                                      │
│ Bu masalaning yechimi Internetda mavjud bo'lishi     │
│ mumkin. Lekin:                                       │
│                                                      │
│ • Boshqa koddan nusxa ko'chirish qat'iyan taqiqlandi │
│ • Barcha yechimlar avtomatik plagiarism tekshiruvidan│
│   o'tkaziladi (moss, jplag algoritmlari)             │
│ • Aniqlansa — XP 0, hisobingiz vaqtincha bloklanadi  │
│                                                      │
│ O'zingiz o'ylang, o'zingiz yozing. 💪                │
└──────────────────────────────────────────────────────┘
```

---

## Test (MCQ) Interface

### Test Mock Data
```json
{
  "session_id": "uuid-abc123",
  "test": { "id": 5, "title": "Hash Map bilimini tekshirish", "question_count": 5, "duration_minutes": 10 },
  "questions": [
    {
      "id": 1, "text": "Hash map ning o'rtacha vaqt murakkabligi nima?",
      "image": null, "order": 1,
      "choices": [
        { "id": 1, "text": "O(1)", "order": 1 },
        { "id": 2, "text": "O(n)", "order": 2 },
        { "id": 3, "text": "O(log n)", "order": 3 },
        { "id": 4, "text": "O(n²)", "order": 4 }
      ]
    },
    {
      "id": 2, "text": "Python da dict dan qanday element olish mumkin?",
      "image": null, "order": 2,
      "choices": [
        { "id": 5, "text": "d['key']", "order": 1 },
        { "id": 6, "text": "d.get('key')", "order": 2 },
        { "id": 7, "text": "Ikkalasi ham to'g'ri", "order": 3 },
        { "id": 8, "text": "d.fetch('key')", "order": 4 }
      ]
    }
  ],
  "time_left_seconds": 598
}
```

### Test UI Layout

```
┌──────────────────────────────────────────────────────┐
│ Hash Map bilimini tekshirish          ⏱ 09:58        │
│ [████████████░░░░░░░░░░░░] 2 / 5 savol               │
├──────────────────────────────────────────────────────┤
│                                                      │
│  2-savol                                             │
│                                                      │
│  Hash map ning o'rtacha vaqt murakkabligi nima?      │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │ ○  A)  O(1)                                    │  │
│  └────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────┐  │
│  │ ●  B)  O(n)              ← TANLANGAN           │  │
│  └────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────┐  │
│  │ ○  C)  O(log n)                                │  │
│  └────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────┐  │
│  │ ○  D)  O(n²)                                   │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  [1✓] [2●] [3○] [4○] [5○]    dot navigation         │
│                                                      │
│  [← Oldingi]                  [Keyingi →]            │
│                                                      │
│                             [Testni yakunlash]       │
└──────────────────────────────────────────────────────┘

Auto-save: har javob tanlanganda POST /api/tests/answer/
Deadline yetganda: avtomatik submit + redirect result
```

### Test Result Screen

```
┌──────────────────────────────────────────────────────┐
│            Test yakunlandi!                          │
│                                                      │
│              3 / 5                                   │
│             60%                                      │
│                                                      │
│  ──────────────────────────────────────────────────  │
│  1-savol ✅  To'g'ri                                  │
│  2-savol ❌  Xato — To'g'ri javob: A) O(1)           │
│  3-savol ✅  To'g'ri                                  │
│  4-savol ❌  Xato — To'g'ri javob: C) O(log n)       │
│  5-savol ✅  To'g'ri                                  │
│  ──────────────────────────────────────────────────  │
│                                                      │
│  ⚡ +30 XP olindi                                    │
│  (passing_score: 70% — O'tgansiz ✅)                 │
│                                                      │
│  [Qayta urinish]        [Darsga qaytish]             │
└──────────────────────────────────────────────────────┘
```

### WebSocket — Test Timer
```typescript
// ws://api/ws/test-session/{session_id}/
type TestWsMessage =
  | { type: 'time_update'; data: { seconds_left: number } }
  | { type: 'auto_submit'; data: { reason: 'deadline' | 'time_up' } };
```

---

## Profile Page — `/profile/[username]`

### Mock Data
```json
{
  "username": "sardor_dev", "full_name": "Sardor Yusupov",
  "joined_at": "2025-08-15",
  "stats": {
    "xp": 4750, "level": 12,
    "current_streak": 7, "longest_streak": 23,
    "total_solved": 87,
    "easy_count": 45, "medium_count": 32, "hard_count": 10,
    "test_count": 24,
    "contest_rating": 1642, "contests_participated": 11, "rank_global": 234
  },
  "activity_heatmap": {
    "2026-04-01": 2, "2026-04-02": 0, "2026-04-03": 4,
    "2026-04-04": 1, "2026-05-08": 6, "2026-05-11": 2
  },
  "recent_submissions": [
    { "problem": "Two Sum",    "slug": "two-sum",    "status": true,  "language": "python", "submitted_at": "2026-05-11T10:23:00Z" },
    { "problem": "Reverse LL", "slug": "reverse-ll", "status": true,  "language": "python", "submitted_at": "2026-05-10T19:45:00Z" },
    { "problem": "LRU Cache",  "slug": "lru-cache",  "status": false, "language": "python", "submitted_at": "2026-05-10T18:12:00Z" }
  ],
  "badges": [
    { "name": "Streak Master",  "icon": "fire",      "description": "7 kun ketma-ket" },
    { "name": "First Blood",    "icon": "sword",      "description": "Birinchi masala" },
    { "name": "Speed Demon",    "icon": "lightning",  "description": "1 daqiqada yechim" },
    { "name": "Test Champion",  "icon": "trophy",     "description": "10 test 100%" }
  ]
}
```

---

## Leaderboard — `/leaderboard`

### Mock Data
```json
{
  "period": "global", "my_rank": 42,
  "users": [
    { "rank": 1,  "username": "sardor_dev",   "xp": 12400, "solved": 234, "streak": 45, "level": 28 },
    { "rank": 2,  "username": "malika_codes", "xp": 11800, "solved": 218, "streak": 32, "level": 26 },
    { "rank": 3,  "username": "jasur_algo",   "xp": 10950, "solved": 201, "streak": 28, "level": 25 },
    { "rank": 4,  "username": "nodira_dev",   "xp":  9870, "solved": 187, "streak": 19, "level": 23 },
    { "rank": 5,  "username": "bekzod_99",    "xp":  9100, "solved": 174, "streak": 14, "level": 22 },
    { "rank": 42, "username": "current_user", "xp":  4750, "solved": 87,  "streak": 7,  "level": 12 }
  ]
}
```

### Layout

```
TOP 3 PODIUM (animated on mount):
        [2nd malika]     [1st sardor]     [3rd jasur]
          ⭐11800          ⭐12400          ⭐10950
          [  🥈  ]        [  🥇  ]        [  🥉  ]
          [██████]       [████████]       [█████]

Tabs: [Global] [Haftalik] [Oylik]

TABLE:
Rank │ User         │ Level │ XP      │ Solved │ Streak
─────┼──────────────┼───────┼─────────┼────────┼────────
 4   │ nodira_dev   │  23   │  9,870  │  187   │ 🔥 19
 5   │ bekzod_99    │  22   │  9,100  │  174   │ 🔥 14
...
[42] │ ⭐ Siz        │  12   │  4,750  │   87   │ 🔥  7
     (brand-primary highlight row)
```

---

## Shared Components

### useWebSocket Hook
```typescript
// hooks/useWebSocket.ts
export function useWebSocket<T>(url: string, onMessage: (msg: T) => void) {
  const wsRef   = useRef<WebSocket | null>(null);
  const retries = useRef(0);

  const connect = useCallback(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;
    ws.onopen    = () => { retries.current = 0; };
    ws.onmessage = e  => onMessage(JSON.parse(e.data) as T);
    ws.onclose   = () => {
      const delay = Math.min(1000 * 2 ** retries.current, 30000);
      retries.current++;
      setTimeout(connect, delay);
    };
  }, [url, onMessage]);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);
}
```

### DifficultyBadge
```tsx
const map = {
  easy:   { label: 'Oson',     color: '#22c55e' },
  medium: { label: "O'rtacha", color: '#f59e0b' },
  hard:   { label: 'Qiyin',    color: '#ef4444' },
};
<span style={{ background: `${map[d].color}22`, color: map[d].color,
  padding: '2px 10px', borderRadius: 9999, fontSize: 12 }}>
  {map[d].label}
</span>
```

### ContentTypeBadges (contest / lesson uchun)
```tsx
{hasProblems && <Badge icon="💻">Masala ×{n}</Badge>}
{hasTests    && <Badge icon="📝">Test ×{n}</Badge>}
{hasVideo    && <Badge icon="🎬">Video</Badge>}
```

---

## API Endpoints

```typescript
// Auth
POST /api/auth/send-otp/              { phone }
POST /api/auth/verify-otp/            { phone, otp }     // otp: "131414"
POST /api/auth/refresh/               { refresh }
POST /api/auth/logout/

// Problems
GET  /api/problems/                   ?difficulty=&category=&search=&solved=&page=
GET  /api/problems/:slug/
POST /api/problems/:slug/run/         { code, language, custom_input? }
POST /api/problems/:slug/submit/      { code, language }
GET  /api/problems/:slug/submissions/

// Contests
GET  /api/contests/                   ?status=&type=
GET  /api/contests/:id/
POST /api/contests/:id/register/      { access_key? }    // yopiq uchun
GET  /api/contests/:id/leaderboard/
GET  /api/contests/:id/problems/
GET  /api/contests/:id/tests/

// Courses
GET  /api/courses/                    ?enrolled=&price=
GET  /api/courses/:slug/
POST /api/courses/:id/enroll/
GET  /api/courses/:slug/:lesson/
POST /api/lessons/:id/complete/

// Tests (MCQ)
POST /api/tests/:id/start/            → { session_id, questions, time_left }
POST /api/tests/answer/               { session_id, question_id, choice_id }
POST /api/tests/submit/               { session_id }
GET  /api/tests/result/:session_id/

// Profile
GET  /api/profile/:username/
GET  /api/profile/me/

// Leaderboard
GET  /api/leaderboard/                ?period=global|weekly|monthly
```

---

## WebSocket Endpoints

```
ws://api/ws/execute/                  Kod ishlatish (ioi/isolate)
ws://api/ws/contest/{id}/             Contest timer + status
ws://api/ws/contest/{id}/leaderboard/ Live leaderboard
ws://api/ws/test-session/{id}/        Test timer + auto-submit
ws://api/ws/notifications/            Real-time bildirishnomalar
```

---

## Next.js Performance

```typescript
// Dynamic imports
const MonacoEditor  = dynamic(() => import('@monaco-editor/react'), { ssr: false });
const VideoPlayer   = dynamic(() => import('@/components/VideoPlayer'), { ssr: false });
const Hls           = dynamic(() => import('hls.js'), { ssr: false });

// Problem list: @tanstack/virtual (virtualize)
// Images: next/image, WebP format
// Fonts: next/font/google (Sora + JetBrains Mono)
// Monaco: load only on /problems/[slug]
```

---

## AI Agent — Yakuniy Ko'rsatmalar

```
1. AUTH
   - Faqat OTP (6 raqam, masalan "131414")
   - Register sahifasi YO'Q — mavjud userni tekshiradi
   - Yopiq contest: access_key inline modal

2. ADAPTIVE CONTENT
   - Problem:  Monaco + WebSocket execution + plagiarism notice
   - Test:     MCQ + countdown + auto-save + auto-submit
   - Video:    hls.js player + mp4 fallback
   - Mixed:    hammasi birga, yuqoridan pastga tartibda

3. CONTEST TYPES
   - "open":    barcha ko'radi, ro'yxat erkin
   - "private": access_key modal inline, faqat shundan keyin ro'yxat

4. WEBSOCKET — reconnect MAJBURIY
   - useWebSocket hook exponential backoff: 1s → 2s → 4s → max 30s
   - Har sahifada kerakli WS ni connect qiling

5. MOCK DATA
   - Yuqoridagi JSON'larni MSW yoki /api/mock/ dan serving qiling

6. PLAGIARISM NOTICE
   - Dismiss bo'lmaydi
   - Har bir coding lesson va standalone problem pastida

7. LEADERBOARD — mixed contest uchun
   - Kod va Test ustunlari alohida ko'rsatiladi

8. ISOLATE API (ioi/isolate)
   - Barcha kod submission WebSocket orqali
   - TLE / MLE / Runtime Error / Compile Error farqlash
```




test user
```json
{"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZXNzaW9uX2lkIjoxLCJ0ZWxlZ3JhbV9pZCI6NzE0MjkwODMzNCwicGhvbmVfbnVtYmVyIjoiOTk4OTc5NDM3Njc0IiwidXNlcm5hbWUiOiJDb2RpbmdfZm9yX01hY2hpbmVzIiwiZnVsbF9uYW1lIjoiQXNhZGJlayBcdWQ4M2RcdWRjM2UgXHUyNzI4Iiwic2VjcmV0X2tleSI6IklUTUM0N1FOTkNHQVJHUVdFNUs1RTdHMllOMlRHSUtJIiwiZXhwIjoxODA5MzM1NzkwLCJpYXQiOjE3Nzg1NzczOTB9.DlqXiFLnwvK7DRGdP6ijY7x1NRzCCpDVRTGr52Kv4k8", "user": {"user_id": 7142908334, "username": "Coding_for_Machines", "phone": "998979437674", "full_name": "Asadbek \ud83d\udc3e \u2728", "last_login": "2026-05-12 09:16:30.527350+00:00"}}%  ```