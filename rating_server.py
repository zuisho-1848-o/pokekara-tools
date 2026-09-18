#!/usr/bin/env python3
"""
ローカルで player.html を配信しつつ、個人評価(★1-5)と伸びしろフラグを
ratings.json に保存するための簡易サーバー。

使い方:
    python3 rating_server.py
    → http://localhost:8765/player.html をブラウザで開く

API:
    GET  /api/ratings  → ratings.json の内容を返す
                          （{mv_id: {"rating": 1-5, "ceiling": "quick_fix"|"fundamental"|"ceiling"}}、
                          各キーは値がある時だけ含まれる）
    POST /api/rate     → {"mv_id": "...", "rating": 1-5 または null} を受け取り
                          星評価を更新する（null は評価解除）
    POST /api/ceiling  → {"mv_id": "...", "ceiling": "quick_fix"|"fundamental"|"ceiling"|null}
                          を受け取り伸びしろ状態を更新する（null は未選択に戻す）

それ以外のパスは通常の静的ファイル配信（player.html, downloads/ 等）。
player.html は毎回ディスクから読むので、generate_player.py で再生成しても
サーバーを再起動せずブラウザを更新するだけで反映される。

static配信は HTTP Range リクエスト(部分取得)に対応している。
Pythonの http.server は標準では Range を無視して常に全体を200で返すため、
<audio>要素が曲の未バッファ部分にシーク（曲を変えた直後など）すると
ブラウザがRangeリクエストの失敗とみなして再生位置を0に戻してしまう
不具合があった。206 Partial Content を正しく返すことで解消している。
"""

import http.server
import json
import os
import re
import socketserver
import threading

PORT = 8765
RATINGS_FILE = "ratings.json"
CEILING_VALUES = {"quick_fix", "fundamental", "ceiling"}
RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)$")
_lock = threading.Lock()


def load_ratings():
    if not os.path.exists(RATINGS_FILE):
        return {}
    with open(RATINGS_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_ratings(data):
    tmp = RATINGS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, RATINGS_FILE)


def update_field(data, mv_id, key, value):
    entry = dict(data.get(mv_id) or {})
    if value is None:
        entry.pop(key, None)
    else:
        entry[key] = value
    if entry:
        data[mv_id] = entry
    else:
        data.pop(mv_id, None)


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/ratings":
            with _lock:
                data = load_ratings()
            self._send_json(200, data)
            return
        range_header = self.headers.get("Range")
        if range_header and self._serve_range(range_header):
            return
        super().do_GET()

    def _serve_range(self, range_header):
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            return False
        m = RANGE_RE.match(range_header)
        if not m:
            return False

        file_size = os.path.getsize(path)
        start_str, end_str = m.groups()
        if start_str == "":
            if end_str == "":
                return False
            suffix_length = int(end_str)
            start = max(file_size - suffix_length, 0)
            end = file_size - 1
        else:
            start = int(start_str)
            end = int(end_str) if end_str else file_size - 1
        end = min(end, file_size - 1)

        if start > end or start >= file_size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{file_size}")
            self.end_headers()
            return True

        length = end - start + 1
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(65536, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)
        return True

    def do_POST(self):
        if self.path == "/api/rate":
            self._handle_update("rating", self._parse_rating)
            return
        if self.path == "/api/ceiling":
            self._handle_update("ceiling", self._parse_ceiling)
            return
        self.send_response(404)
        self.end_headers()

    def _handle_update(self, key, parse_value):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw)
            mv_id = str(payload["mv_id"])
            value = parse_value(payload.get(key))
        except Exception as e:
            self._send_json(400, {"error": str(e)})
            return

        with _lock:
            data = load_ratings()
            update_field(data, mv_id, key, value)
            save_ratings(data)

        self._send_json(200, {"ok": True})

    @staticmethod
    def _parse_rating(rating):
        if rating is None:
            return None
        rating = int(rating)
        if not (1 <= rating <= 5):
            raise ValueError("rating must be 1-5")
        return rating

    @staticmethod
    def _parse_ceiling(ceiling):
        if ceiling is None:
            return None
        if ceiling not in CEILING_VALUES:
            raise ValueError(f"ceiling must be one of {sorted(CEILING_VALUES)}")
        return ceiling

    def _send_json(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


def main():
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"http://localhost:{PORT}/player.html を開いてください（Ctrl+Cで終了）")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
