function switchTab(name, btn) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  if(btn) btn.classList.add('active');
  ['overview','submissions','contests','settings'].forEach(p => {
    document.getElementById('pane-'+p).style.display = p===name ? '' : 'none';
  });
}

/* Heatmap */
(function(){
  const g = document.getElementById('heatmap');
  if (!g) return;
  const lv = [0,0,1,2,3,4,2,1,0,0,1,3,4,2,1,0,2,3,1,2,0,1,3,4,2,1,0,0,2,3,
              1,2,3,4,2,1,0,1,2,3,0,1,2,3,4,2,1,0,0,1,3,2,1,0,0,1,2,3,4,2,
              1,0,2,3,1,0,0,2,3,4,1,2,0,1,3,2,1,0,1,2,3,4,0,1,2,3,0,1,2,1,
              0,1,0,0,1,2,3,4,2,1,0,0,1,2,3,2,1,0,1,2,3,4,0,1,2,0,1,2,3,0,
              0,1,2,3,4,2,1,0,0,2,1,3,0,1,2,0,1,3,2,4,1,0,0,1,2,0,1,2,3,0,
              1,2,3,4,2,1,0,2,3,1,0,0,1,2,3,4,2,0,1,3,2,1,0,0,2,3,4,1,2,0,
              1,0,2,3,1,2,3,4,2,1,0,0,1,2,3,2,1,0,1,2,3,4,0,1,2,3,0,1,2,1,
              0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
              0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
              0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
              0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];
  const map = ['','hm-1','hm-2','hm-3','hm-4'];
  lv.slice(0,364).forEach(v => {
    const c = document.createElement('div');
    c.className = 'hm-cell '+(map[v]||'');
    g.appendChild(c);
  });
})();

/* Tag cloud */
(function(){
  const tags = [
    {name:'Array',n:28},{name:'Hash Table',n:21},{name:'DP',n:12},
    {name:'Graph',n:9},{name:'Greedy',n:14},{name:'Binary Search',n:18},
    {name:'Stack',n:11},{name:'Tree',n:8},{name:'BFS/DFS',n:7},
    {name:'Two Pointers',n:15},{name:'Sorting',n:20},{name:'Math',n:10},
    {name:'String',n:16},{name:'Simulation',n:6},{name:'Recursion',n:13},
  ];
  const el = document.getElementById('tagCloud');
  if (el) el.innerHTML = tags.map(t =>
    `<div class="tc-tag">${t.name}<span class="tc-count">${t.n}</span></div>`
  ).join('');
})();

/* Recent submissions */
const SUBS = [
  {status:'ac',  title:'Two Sum',           lang:'C++ 17',   time:'124ms', mem:'9.2MB', ago:'2 soat oldin'},
  {status:'wa',  title:'Longest Substring', lang:'C++ 17',   time:'—',     mem:'—',     ago:'3 soat oldin'},
  {status:'ac',  title:'Binary Tree BFS',   lang:'Python 3', time:'210ms', mem:'14MB',  ago:'1 kun oldin'},
  {status:'tle', title:'Graph Shortest',    lang:'C++ 17',   time:'>2s',   mem:'—',     ago:'2 kun oldin'},
  {status:'ac',  title:'Kadane Algorithm',  lang:'Java 17',  time:'188ms', mem:'11MB',  ago:'3 kun oldin'},
];

function subRowHtml(s, compact) {
  const cls   = {ac:'var(--easy-dark)',wa:'var(--hard-dark)',tle:'var(--medium-dark)',mle:'#7c3aed'};
  const label = {ac:'Accepted',wa:'Wrong Answer',tle:'Time Limit',mle:'Memory Limit'};
  return `<div class="sub-item" onclick="location.href='problem-detail.html'">
    <div class="sub-status-dot ${s.status}"></div>
    <div style="flex:1;min-width:0">
      <div style="font-size:13px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${s.title}</div>
      <div style="font-size:11px;color:var(--text-4);margin-top:1px">${s.lang}</div>
    </div>
    <div style="text-align:right;flex-shrink:0">
      <div style="font-size:12px;font-weight:600;color:${cls[s.status]||'var(--text-3)'}}">${label[s.status]||s.status}</div>
      <div style="font-size:11px;color:var(--text-4);font-family:var(--font-mono)">${s.time} · ${s.mem}</div>
      <div style="font-size:10.5px;color:var(--text-5)">${s.ago}</div>
    </div>
  </div>`;
}

const rsEl = document.getElementById('recentSubs');
const asEl = document.getElementById('allSubsList');
if (rsEl) rsEl.innerHTML = SUBS.slice(0,4).map(s => subRowHtml(s)).join('');
if (asEl) asEl.innerHTML = SUBS.map(s => subRowHtml(s)).join('');

/* Contest history */
const HISTORY = [
  {title:'RobaContest #47', rank:'#23',  pts:'+120', date:'Bugun'},
  {title:'CFM Cup #7',      rank:'#41',  pts:'+85',  date:'1 hafta oldin'},
  {title:'Weekly #11',      rank:'#15',  pts:'+200', date:'2 hafta oldin'},
  {title:'RobaContest #46', rank:'#31',  pts:'+95',  date:'3 hafta oldin'},
  {title:'CFM Cup #6',      rank:'#52',  pts:'+60',  date:'1 oy oldin'},
];
const chEl = document.getElementById('contestHistory');
if (chEl) chEl.innerHTML = HISTORY.map(h => `
  <div class="ch-row" onclick="location.href='contest-detail.html'">
    <div style="font-size:13px;font-weight:600;color:var(--text)">${h.title}</div>
    <div style="text-align:center;font-family:var(--font-mono);font-size:13px;font-weight:700;color:var(--accent-dark)">${h.rank}</div>
    <div style="text-align:center;font-family:var(--font-mono);font-size:13px;font-weight:700;color:var(--easy-dark)">${h.pts}</div>
    <div style="text-align:right;font-size:11.5px;color:var(--text-4)">${h.date}</div>
  </div>`).join('');

/* Load user from localStorage */
document.addEventListener('DOMContentLoaded', () => {
  const user = typeof Auth !== 'undefined' ? Auth.getUser() : null;
  if (user) {
    const n = user.full_name || user.username || 'Foydalanuvchi';
    const av = n.split(' ').slice(0,2).map(w=>w[0]).join('').toUpperCase();
    const nameEl = document.getElementById('profileName');
    const handleEl = document.getElementById('profileHandle');
    const avatarEl = document.getElementById('profileAvatar');
    if (nameEl) nameEl.textContent = n;
    if (handleEl) handleEl.textContent = '@' + (user.username || 'user');
    if (avatarEl) avatarEl.textContent = av;
  }
});