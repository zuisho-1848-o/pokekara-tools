#!/usr/bin/env python3
"""
songs.json + downloads/ の内容から、ブラウザで開くだけで使える
自己完結型プレイヤー (player.html) を生成する。

使い方:
    python3 generate_player.py

生成後、player.html をブラウザで直接開けば使える（サーバー不要）。
ダウンロード済みの曲はローカルファイルを再生し、未ダウンロードの曲は
再生ボタンを押した時だけ配信元URLからストリーミング再生する。
"""

import html
import json
import os

SONGS_JSON = "songs.json"
DOWNLOAD_DIR = "downloads"
OUT_HTML = "player.html"


def sanitize(name: str) -> str:
    for ch in '/\\:*?"<>|':
        name = name.replace(ch, "_")
    return name.strip()


def main():
    with open(SONGS_JSON, encoding="utf-8") as f:
        songs = json.load(f)

    items = []
    local_count = 0
    for s in songs:
        title = s.get("title") or s["mv_id"]
        fname = f"{s['mv_id']}_{sanitize(title)}.m4a"
        local_path = os.path.join(DOWNLOAD_DIR, fname)
        has_local = os.path.exists(local_path)
        if has_local:
            local_count += 1
        items.append(
            {
                "id": s["mv_id"],
                "title": title,
                "score": s.get("score"),
                "posted_at": s.get("posted_at") or "",
                "duration": s.get("duration_sec") or 0,
                "page_url": s.get("page_url") or "",
                "src": (
                    f"{DOWNLOAD_DIR}/{fname}" if has_local else s.get("m4a_url")
                ),
                "local": has_local,
                "collab": bool(s.get("is_collab")),
            }
        )

    data_json = json.dumps(items, ensure_ascii=False)

    html_out = TEMPLATE.replace("__SONGS_JSON__", data_json)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"{OUT_HTML} を生成しました（曲数: {len(items)}, ローカル再生可: {local_count}）")


TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>My Pokekara Player</title>
<style>
  :root {
    color-scheme: light dark;
    --bg: #f5f5f7;
    --fg: #1c1c1e;
    --card: #ffffff;
    --border: #d9d9dd;
    --accent: #4a6cf7;
    --muted: #8a8a8e;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #16161a;
      --fg: #f2f2f4;
      --card: #212126;
      --border: #35353b;
      --muted: #9a9aa0;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, "Hiragino Sans", "Yu Gothic", sans-serif;
    background: var(--bg);
    color: var(--fg);
    padding-bottom: 110px;
  }
  header {
    padding: 16px 20px 8px;
  }
  h1 { font-size: 18px; margin: 0 0 12px; }
  .controls {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: center;
    padding: 0 20px 12px;
  }
  .controls input[type="text"] {
    flex: 1;
    min-width: 160px;
    padding: 8px 10px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: var(--card);
    color: var(--fg);
  }
  .controls label {
    font-size: 12px;
    color: var(--muted);
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .controls input[type="number"],
  .controls input[type="date"],
  .controls select {
    padding: 6px 8px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--card);
    color: var(--fg);
    width: 110px;
  }
  .status {
    padding: 0 20px 8px;
    font-size: 12px;
    color: var(--muted);
  }
  table { width: 100%; border-collapse: collapse; }
  thead th {
    position: sticky;
    top: 0;
    background: var(--bg);
    text-align: left;
    padding: 8px 12px;
    font-size: 12px;
    color: var(--muted);
    cursor: pointer;
    user-select: none;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  thead th.active { color: var(--accent); }
  tbody td {
    padding: 8px 12px;
    border-bottom: 1px solid var(--border);
    font-size: 14px;
  }
  tbody tr { cursor: pointer; }
  tbody tr:hover { background: color-mix(in srgb, var(--accent) 8%, transparent); }
  tbody tr.playing { background: color-mix(in srgb, var(--accent) 18%, transparent); }
  tbody tr.nolocal td.title { color: var(--muted); }
  td.rating { white-space: nowrap; }
  td.rating .star { cursor: pointer; font-size: 15px; color: var(--muted); }
  td.rating .star.filled { color: #f5b301; }
  .badge {
    font-size: 10px;
    padding: 1px 6px;
    border-radius: 999px;
    border: 1px solid var(--border);
    margin-left: 6px;
    color: var(--muted);
  }
  .badge.collab {
    color: var(--accent);
    border-color: var(--accent);
  }
  .info-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 1px solid var(--muted);
    color: var(--muted);
    font-size: 10px;
    font-weight: bold;
    font-style: normal;
    text-transform: none;
    cursor: pointer;
    margin-left: 4px;
    vertical-align: middle;
  }
  .info-btn:hover { border-color: var(--accent); color: var(--accent); }
  .info-popover {
    display: none;
    position: absolute;
    top: 100%;
    left: 0;
    z-index: 10;
    margin-top: 6px;
    width: 260px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.2);
    padding: 10px 12px;
    font-size: 12px;
    font-weight: normal;
    color: var(--fg);
    cursor: default;
    white-space: normal;
  }
  .info-popover.open { display: block; }
  .info-popover dl { margin: 0; }
  .info-popover dt { font-weight: bold; margin-top: 6px; }
  .info-popover dt:first-child { margin-top: 0; }
  .info-popover dd { margin: 0 0 0 0; color: var(--muted); }
  .player {
    position: fixed;
    left: 0; right: 0; bottom: 0;
    background: var(--card);
    border-top: 1px solid var(--border);
    padding: 10px 16px 14px;
  }
  .player .now {
    font-size: 13px;
    margin-bottom: 6px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .player .row {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }
  .player button {
    border: 1px solid var(--border);
    background: var(--card);
    color: var(--fg);
    border-radius: 8px;
    padding: 6px 12px;
    cursor: pointer;
    font-size: 13px;
  }
  .player button.on { background: var(--accent); color: white; border-color: var(--accent); }
  .player input[type="range"] { vertical-align: middle; }
  .time { font-size: 12px; color: var(--muted); width: 90px; text-align: center; }
  .seek { flex: 1; min-width: 120px; }
  .vol { width: 100px; }
</style>
</head>
<body>

<header>
  <h1>My Pokekara Player</h1>
</header>

<div class="controls">
  <input id="q" type="text" placeholder="タイトル検索...">
  <label>評価 min <input id="scoreMin" type="number" min="0" max="100" step="1"></label>
  <label>評価 max <input id="scoreMax" type="number" min="0" max="100" step="1"></label>
  <label>投稿日 from <input id="dateMin" type="date"></label>
  <label>投稿日 to <input id="dateMax" type="date"></label>
  <label>コラボ
    <select id="collabFilter">
      <option value="all">すべて</option>
      <option value="solo">ソロのみ</option>
      <option value="collab">コラボのみ</option>
    </select>
  </label>
  <label>マイ評価
    <select id="myRatingFilter">
      <option value="all">すべて</option>
      <option value="none">未評価のみ</option>
      <option value="1">★1以上</option>
      <option value="2">★2以上</option>
      <option value="3">★3以上</option>
      <option value="4">★4以上</option>
      <option value="5">★5</option>
    </select>
  </label>
  <button id="clearFilters">絞り込み解除</button>
</div>
<div class="status" id="status"></div>

<table>
  <thead>
    <tr>
      <th data-key="title">タイトル</th>
      <th data-key="score">評価</th>
      <th data-key="myRating" class="myrating-th">マイ評価<span class="info-btn" id="myRatingInfoBtn">i</span>
        <div class="info-popover" id="myRatingInfoPopover">
          <dl>
            <dt>★5</dt><dd>人に薦めたい・一番聞いてほしい</dd>
            <dt>★4</dt><dd>及第点以上、欠点なし（自信作だが5ほどの目玉ではない）</dd>
            <dt>★3</dt><dd>聞かせられるが、自分でわかる小さな粗がある</dd>
            <dt>★2</dt><dd>高音の聞き苦しいところがあるかミスが多い</dd>
            <dt>★1</dt><dd>撮り直したいし聞かれたくない</dd>
          </dl>
        </div>
      </th>
      <th data-key="posted_at">投稿日</th>
      <th data-key="duration">長さ</th>
    </tr>
  </thead>
  <tbody id="rows"></tbody>
</table>

<div class="player">
  <div class="now" id="nowPlaying">再生中の曲はありません</div>
  <div class="row">
    <button id="prevBtn">⏮ 前へ</button>
    <button id="playBtn">▶ 再生</button>
    <button id="nextBtn">次へ ⏭</button>
    <button id="loopOneBtn" title="この曲をリピート">🔂 1曲リピート</button>
    <button id="loopAllBtn" title="表示中の曲をリピート" class="on">🔁 全曲リピート</button>
    <button id="jumpToPlayingBtn" title="再生中の曲までリストをスクロール">🎯 現在の曲へ</button>
    <span class="time" id="curTime">0:00</span>
    <input class="seek" id="seek" type="range" min="0" max="100" value="0">
    <span class="time" id="durTime">0:00</span>
    <span>🔊</span>
    <input class="vol" id="vol" type="range" min="0" max="100" value="80">
  </div>
</div>

<audio id="audio"></audio>

<script>
const SONGS = __SONGS_JSON__;

const audio = document.getElementById('audio');
const rowsEl = document.getElementById('rows');
const statusEl = document.getElementById('status');

let sortKey = localStorage.getItem('pokekara_sort_key') || 'posted_at';
let sortDir = localStorage.getItem('pokekara_sort_dir') || 'desc';
let currentList = [];
let currentIndex = -1;
let loopOne = false;
let loopAll = true;

const qEl = document.getElementById('q');
const scoreMinEl = document.getElementById('scoreMin');
const scoreMaxEl = document.getElementById('scoreMax');
const dateMinEl = document.getElementById('dateMin');
const dateMaxEl = document.getElementById('dateMax');
const collabFilterEl = document.getElementById('collabFilter');
const myRatingFilterEl = document.getElementById('myRatingFilter');

let ratingsBackend = 'server';

async function loadRatings() {
  try {
    const res = await fetch('/api/ratings');
    if (!res.ok) throw new Error('bad response');
    return await res.json();
  } catch {
    ratingsBackend = 'local';
    try {
      return JSON.parse(localStorage.getItem('pokekara_ratings') || '{}');
    } catch {
      return {};
    }
  }
}

async function saveRating(mvId, rating) {
  if (ratingsBackend === 'server') {
    try {
      const res = await fetch('/api/rate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mv_id: mvId, rating }),
      });
      if (!res.ok) throw new Error('bad response');
      return;
    } catch {
      ratingsBackend = 'local';
    }
  }
  const data = JSON.parse(localStorage.getItem('pokekara_ratings') || '{}');
  if (rating == null) delete data[mvId];
  else data[mvId] = rating;
  localStorage.setItem('pokekara_ratings', JSON.stringify(data));
}

function fmtTime(sec) {
  if (!isFinite(sec) || sec < 0) sec = 0;
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

function applyFilters() {
  const q = qEl.value.trim().toLowerCase();
  const sMin = scoreMinEl.value !== '' ? parseFloat(scoreMinEl.value) : -Infinity;
  const sMax = scoreMaxEl.value !== '' ? parseFloat(scoreMaxEl.value) : Infinity;
  const dMin = dateMinEl.value || '';
  const dMax = dateMaxEl.value || '';
  const collabMode = collabFilterEl.value;
  const myRatingMode = myRatingFilterEl.value;

  let list = SONGS.filter(s => {
    if (q && !s.title.toLowerCase().includes(q)) return false;
    const score = s.score ?? -1;
    if (score < sMin || score > sMax) return false;
    const d = (s.posted_at || '').slice(0, 10);
    if (dMin && d && d < dMin) return false;
    if (dMax && d && d > dMax) return false;
    if (collabMode === 'solo' && s.collab) return false;
    if (collabMode === 'collab' && !s.collab) return false;
    if (myRatingMode === 'none' && s.myRating) return false;
    if (myRatingMode !== 'all' && myRatingMode !== 'none' && (s.myRating || 0) < parseInt(myRatingMode, 10)) return false;
    return true;
  });

  list.sort((a, b) => {
    let av = a[sortKey], bv = b[sortKey];
    if (sortKey === 'title') { av = av || ''; bv = bv || ''; }
    if (av == null) av = sortDir === 'asc' ? Infinity : -Infinity;
    if (bv == null) bv = sortDir === 'asc' ? Infinity : -Infinity;
    if (av < bv) return sortDir === 'asc' ? -1 : 1;
    if (av > bv) return sortDir === 'asc' ? 1 : -1;
    return 0;
  });

  currentList = list;
  render();
}

function starsHtml(rating) {
  let out = '';
  for (let r = 1; r <= 5; r++) {
    out += `<span class="star${rating >= r ? ' filled' : ''}" data-r="${r}">★</span>`;
  }
  return out;
}

function render() {
  rowsEl.innerHTML = '';
  const playingId = currentIndex >= 0 ? currentList[currentIndex]?.id : null;

  for (const s of currentList) {
    const tr = document.createElement('tr');
    if (!s.local) tr.classList.add('nolocal');
    if (s.id === playingId) tr.classList.add('playing');
    tr.innerHTML = `
      <td class="title">${escapeHtml(s.title)}${s.local ? '' : '<span class="badge">未DL</span>'}${s.collab ? '<span class="badge collab">コラボ</span>' : ''}</td>
      <td>${s.score != null ? Number(s.score).toFixed(1) : '-'}</td>
      <td class="rating">${starsHtml(s.myRating || 0)}</td>
      <td>${escapeHtml((s.posted_at || '').slice(0, 16))}</td>
      <td>${fmtTime(s.duration)}</td>
    `;
    tr.addEventListener('click', () => playById(s.id));
    const ratingTd = tr.querySelector('td.rating');
    ratingTd.addEventListener('click', (e) => {
      const starEl = e.target.closest('.star');
      if (!starEl) return;
      e.stopPropagation();
      const r = parseInt(starEl.dataset.r, 10);
      const newRating = s.myRating === r ? null : r;
      s.myRating = newRating;
      saveRating(s.id, newRating);
      if (myRatingFilterEl.value !== 'all') {
        applyFilters();
      } else {
        ratingTd.innerHTML = starsHtml(newRating || 0);
      }
    });
    rowsEl.appendChild(tr);
  }

  statusEl.textContent = `${currentList.length} / ${SONGS.length} 曲を表示`;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function playById(id) {
  const idx = currentList.findIndex(s => s.id === id);
  if (idx === -1) return;
  currentIndex = idx;
  const s = currentList[idx];
  audio.src = s.src;
  audio.play();
  document.getElementById('nowPlaying').textContent =
    `${s.title} ${s.score != null ? '(評価 ' + Number(s.score).toFixed(1) + ')' : ''}`;
  render();
}

function playNext() {
  if (currentList.length === 0) return;
  if (currentIndex + 1 < currentList.length) {
    playById(currentList[currentIndex + 1].id);
  } else if (loopAll) {
    playById(currentList[0].id);
  }
}

function playPrev() {
  if (currentList.length === 0) return;
  if (currentIndex > 0) {
    playById(currentList[currentIndex - 1].id);
  } else if (loopAll) {
    playById(currentList[currentList.length - 1].id);
  }
}

audio.addEventListener('ended', () => {
  if (loopOne) {
    audio.currentTime = 0;
    audio.play();
  } else {
    playNext();
  }
});

function savePlaybackState() {
  if (currentIndex < 0) return;
  const s = currentList[currentIndex];
  if (!s) return;
  try {
    localStorage.setItem('pokekara_last_playback', JSON.stringify({ id: s.id, time: audio.currentTime || 0 }));
  } catch {}
}

let lastSavedAt = 0;
audio.addEventListener('timeupdate', () => {
  document.getElementById('curTime').textContent = fmtTime(audio.currentTime);
  document.getElementById('durTime').textContent = fmtTime(audio.duration);
  if (audio.duration) {
    document.getElementById('seek').value = (audio.currentTime / audio.duration) * 100;
  }
  const now = Date.now();
  if (now - lastSavedAt > 3000) {
    lastSavedAt = now;
    savePlaybackState();
  }
});
audio.addEventListener('pause', savePlaybackState);
window.addEventListener('beforeunload', savePlaybackState);

document.getElementById('seek').addEventListener('input', (e) => {
  if (audio.duration) {
    audio.currentTime = (e.target.value / 100) * audio.duration;
  }
});

document.getElementById('playBtn').addEventListener('click', () => {
  if (audio.paused) { audio.play(); } else { audio.pause(); }
});
audio.addEventListener('play', () => { document.getElementById('playBtn').textContent = '⏸ 一時停止'; });
audio.addEventListener('pause', () => { document.getElementById('playBtn').textContent = '▶ 再生'; });

document.getElementById('nextBtn').addEventListener('click', playNext);
document.getElementById('prevBtn').addEventListener('click', playPrev);

document.getElementById('loopOneBtn').addEventListener('click', (e) => {
  loopOne = !loopOne;
  e.target.classList.toggle('on', loopOne);
});
document.getElementById('loopAllBtn').addEventListener('click', (e) => {
  loopAll = !loopAll;
  e.target.classList.toggle('on', loopAll);
});
document.getElementById('jumpToPlayingBtn').addEventListener('click', () => {
  const playingRow = rowsEl.querySelector('tr.playing');
  if (playingRow) {
    playingRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
});

const volEl = document.getElementById('vol');
const savedVol = localStorage.getItem('pokekara_vol');
if (savedVol !== null) {
  volEl.value = savedVol;
  audio.volume = savedVol / 100;
} else {
  audio.volume = 0.8;
}
volEl.addEventListener('input', (e) => {
  audio.volume = e.target.value / 100;
  localStorage.setItem('pokekara_vol', e.target.value);
});

const myRatingInfoBtn = document.getElementById('myRatingInfoBtn');
const myRatingInfoPopover = document.getElementById('myRatingInfoPopover');
myRatingInfoBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  myRatingInfoPopover.classList.toggle('open');
});
myRatingInfoPopover.addEventListener('click', (e) => e.stopPropagation());
document.addEventListener('click', () => myRatingInfoPopover.classList.remove('open'));

document.querySelectorAll('thead th').forEach(th => {
  th.addEventListener('click', (e) => {
    if (e.target.closest('.info-btn') || e.target.closest('.info-popover')) return;
    const key = th.dataset.key;
    if (sortKey === key) {
      sortDir = sortDir === 'asc' ? 'desc' : 'asc';
    } else {
      sortKey = key;
      sortDir = key === 'title' ? 'asc' : 'desc';
    }
    document.querySelectorAll('thead th').forEach(t => t.classList.remove('active'));
    th.classList.add('active');
    localStorage.setItem('pokekara_sort_key', sortKey);
    localStorage.setItem('pokekara_sort_dir', sortDir);
    applyFilters();
  });
});
document.querySelector(`thead th[data-key="${sortKey}"]`)?.classList.add('active');

[qEl, scoreMinEl, scoreMaxEl, dateMinEl, dateMaxEl].forEach(el => {
  el.addEventListener('input', applyFilters);
});
collabFilterEl.addEventListener('change', applyFilters);
myRatingFilterEl.addEventListener('change', applyFilters);
document.getElementById('clearFilters').addEventListener('click', () => {
  qEl.value = ''; scoreMinEl.value = ''; scoreMaxEl.value = '';
  dateMinEl.value = ''; dateMaxEl.value = ''; collabFilterEl.value = 'all';
  myRatingFilterEl.value = 'all';
  applyFilters();
});

function restoreLastPlayback() {
  let saved = null;
  try {
    saved = JSON.parse(localStorage.getItem('pokekara_last_playback') || 'null');
  } catch {}
  if (!saved || !saved.id) return;
  const idx = currentList.findIndex(s => s.id === saved.id);
  if (idx === -1) return;
  currentIndex = idx;
  const s = currentList[idx];
  audio.src = s.src;
  audio.addEventListener('loadedmetadata', () => {
    audio.currentTime = saved.time || 0;
  }, { once: true });
  document.getElementById('nowPlaying').textContent =
    `${s.title} ${s.score != null ? '(評価 ' + Number(s.score).toFixed(1) + ')' : ''}`;
  render();
  requestAnimationFrame(() => {
    rowsEl.querySelector('tr.playing')?.scrollIntoView({ block: 'center' });
  });
}

async function init() {
  const ratings = await loadRatings();
  for (const s of SONGS) s.myRating = ratings[s.id] ?? null;
  applyFilters();
  restoreLastPlayback();
}
init();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
