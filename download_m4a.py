#!/usr/bin/env python3
"""
songs.csv の m4a_url を1件ずつダウンロードする。

サーバー負荷対策:
    - 並列実行はせず1件ずつ順番にダウンロード
    - リクエスト間に待機時間(SLEEP_SEC)を挟む
    - 既にダウンロード済みのファイルはスキップ（中断・再実行が安全）
    - 失敗時は待機を延ばしつつ数回だけリトライ

配信元に存在しない曲（404など、コラボ相手側の都合で削除された等）は
failed_downloads.json に記録し、以後の実行では自動でスキップする。
再挑戦したい場合は failed_downloads.json から該当行を削除すればよい。

使い方:
    python3 download_m4a.py
"""

import csv
import json
import os
import random
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

CSV_PATH = "songs.csv"
OUT_DIR = "downloads"
FAILED_LIST_PATH = "failed_downloads.json"
SLEEP_RANGE = (1.5, 3.0)  # 1件ごとの待機秒数（ランダムに散らす）
MAX_RETRIES = 3
RETRY_BACKOFF_SEC = 5

HEADERS = {"User-Agent": "Mozilla/5.0 (personal-archive-script)"}


def load_failed_list() -> dict:
    if os.path.exists(FAILED_LIST_PATH):
        with open(FAILED_LIST_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_failed_list(failed_map: dict) -> None:
    with open(FAILED_LIST_PATH, "w", encoding="utf-8") as f:
        json.dump(failed_map, f, ensure_ascii=False, indent=2)


def sanitize(name: str) -> str:
    for ch in '/\\:*?"<>|':
        name = name.replace(ch, "_")
    return name.strip()


def download_one(url: str, dest: str):
    """成功なら (True, None) を、失敗なら (False, 理由文字列) を返す。"""
    tmp = dest + ".part"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as res, open(tmp, "wb") as f:
                f.write(res.read())
            os.replace(tmp, dest)
            return True, None
        except urllib.error.HTTPError as e:
            if os.path.exists(tmp):
                os.remove(tmp)
            if e.code == 404:
                # 配信元に音源が存在しない（削除済み等）。リトライしても無駄なので即断念。
                print(f"  404 Not Found（配信元に存在しません）")
                return False, "404 Not Found"
            print(f"  失敗 (試行{attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SEC * attempt)
            last_err = str(e)
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"  失敗 (試行{attempt}/{MAX_RETRIES}): {e}")
            if os.path.exists(tmp):
                os.remove(tmp)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SEC * attempt)
            last_err = str(e)
    return False, last_err


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    with open(CSV_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    failed_map = load_failed_list()

    total = len(rows)
    skipped = 0
    skipped_known_bad = 0
    done = 0
    newly_failed = []

    for i, row in enumerate(rows, 1):
        mv_id = row["mv_id"]
        title = sanitize(row["title"] or mv_id)
        dest = os.path.join(OUT_DIR, f"{mv_id}_{title}.m4a")

        if os.path.exists(dest):
            skipped += 1
            continue

        if mv_id in failed_map:
            skipped_known_bad += 1
            continue

        print(f"[{i}/{total}] ダウンロード中: {title}")
        ok, reason = download_one(row["m4a_url"], dest)
        if ok:
            done += 1
        else:
            newly_failed.append(mv_id)
            failed_map[mv_id] = {
                "title": row["title"],
                "url": row["m4a_url"],
                "reason": reason,
                "failed_at": datetime.now(timezone.utc).astimezone().isoformat(),
            }
            save_failed_list(failed_map)
            print(f"  → 断念（failed_downloads.jsonに記録・以後スキップ）: {title}")

        time.sleep(random.uniform(*SLEEP_RANGE))

    print("\n===== 完了 =====")
    print(f"新規ダウンロード: {done}")
    print(f"スキップ（既存ファイル）: {skipped}")
    print(f"スキップ（既知の失敗曲）: {skipped_known_bad}")
    print(f"新規失敗: {len(newly_failed)}")
    if newly_failed:
        print("新規に失敗したmv_id:", ", ".join(newly_failed))
    if failed_map:
        print(
            f"\n累計 {len(failed_map)}曲が failed_downloads.json に登録されています。"
            "再挑戦したい場合は該当エントリを削除してください。"
        )


if __name__ == "__main__":
    main()
