#!/usr/bin/env python3
"""
ローカルで player.html を配信しつつ、個人評価(★1-5)を
ratings.json に保存するための簡易サーバー。

使い方:
    python3 rating_server.py
    → http://localhost:8765/player.html をブラウザで開く

API:
    GET  /api/ratings  → ratings.json の内容を返す（{mv_id: rating}）
    POST /api/rate     → {"mv_id": "...", "rating": 1-5 または null} を受け取り
                          ratings.json を更新する（null は評価解除）

それ以外のパスは通常の静的ファイル配信（player.html, downloads/ 等）。
player.html は毎回ディスクから読むので、generate_player.py で再生成しても
サーバーを再起動せずブラウザを更新するだけで反映される。
"""

import http.server
import json
import os
import socketserver
import threading

PORT = 8765
RATINGS_FILE = "ratings.json"
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


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/ratings":
            with _lock:
                data = load_ratings()
            self._send_json(200, data)
            return
        super().do_GET()

    def do_POST(self):
        if self.path != "/api/rate":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw)
            mv_id = str(payload["mv_id"])
            rating = payload.get("rating")
            if rating is not None:
                rating = int(rating)
                if not (1 <= rating <= 5):
                    raise ValueError("rating must be 1-5")
        except Exception as e:
            self._send_json(400, {"error": str(e)})
            return

        with _lock:
            data = load_ratings()
            if rating is None:
                data.pop(mv_id, None)
            else:
                data[mv_id] = rating
            save_ratings(data)

        self._send_json(200, {"ok": True})

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
