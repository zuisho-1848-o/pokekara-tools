#!/usr/bin/env python3
"""
ポケカラ (Pokekara) の自分の投稿曲一覧を list_feed API から取得し、
タイトル + m4aダウンロードURLをCSV/JSONに出力する。

使い方:
    python3 fetch_list.py        # 差分取得（デフォルト）: 前回取得済みの曲が出てきた時点で打ち切り、
                                  # 新しく投稿された曲だけ既存の songs.json に追記する
    python3 fetch_list.py --full # 全件取得: 最初から全ページを取得し直す

事前準備:
    - BASE_PARAMS の u_share / unique_device_id / t_uid を
      自分の共有ページURLから取得した値に差し替える
      (例: https://u.pokekara.com/mv/xxxx?u_share=uXXXX&is_share_reward=0 )

注記:
    list_feed API は投稿日時の新しい順に返ってくる前提。差分取得モードでは
    既存 songs.json に含まれる mv_id に出会った時点でそれ以降は取得済みと
    みなして打ち切る。
"""

import argparse
import datetime
import json
import os
import time
import urllib.parse
import urllib.request

API = "https://api.pokekara.com/x/moment/list_feed"

# memo.md の共有URLから取れる値。必要に応じて書き換える。
BASE_PARAMS = {
    "request_id": "1786434312391168",
    "u_share": "u1522410711094480896",
    "is_share_reward": "0",
    "appid": "com.pokekara.web",
    "phonetype": "web",
    "request_refer": "h5",
    "unique_device_id": "d3ecd4d9-9563-4036-8463-4b5137d22c04",
    "t_uid": "u1522410711094480896",
}

OUT_JSON = "songs.json"
OUT_CSV = "songs.csv"
SLEEP_SEC = 0.5  # API負荷軽減用のウェイト


def fetch_page(cursor=None):
    params = dict(BASE_PARAMS)
    if cursor is not None:
        params["cursor"] = str(cursor)
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.load(res)


def load_existing():
    if not os.path.exists(OUT_JSON):
        return []
    with open(OUT_JSON, encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--full",
        action="store_true",
        help="差分取得ではなく、全ページを取得し直す",
    )
    args = parser.parse_args()

    existing_songs = [] if args.full else load_existing()
    existing_ids = {s["mv_id"] for s in existing_songs}
    incremental = not args.full and bool(existing_ids)

    new_songs = []
    seen_ids = set()
    cursor = None
    stopped_early = False

    while True:
        body = fetch_page(cursor)
        if body.get("err_code") != 0:
            print("APIエラー:", body.get("err_msg"))
            break

        data = body["data"]
        moments = data.get("moments", [])
        if not moments:
            break

        for m in moments:
            d = m.get("data", {})
            mv_id = d.get("mv_id_str") or m.get("id_str")
            if not mv_id or mv_id in seen_ids:
                continue
            if incremental and mv_id in existing_ids:
                stopped_early = True
                break
            seen_ids.add(mv_id)
            new_songs.append(
                {
                    "mv_id": mv_id,
                    "title": d.get("title", ""),
                    "m4a_url": d.get("video_url") or d.get("video_sound_url"),
                    "page_url": (
                        f"https://u.pokekara.com/mv/{mv_id}"
                        f"?u_share={BASE_PARAMS['u_share']}&is_share_reward=0"
                    ),
                    "score": d.get("score"),
                    "is_collab": d.get("vocal_source_head_uid") != d.get("uid"),
                    "posted_at": (
                        datetime.datetime.fromtimestamp(
                            d["ctime"], tz=datetime.timezone.utc
                        )
                        .astimezone()
                        .strftime("%Y-%m-%d %H:%M:%S")
                        if d.get("ctime")
                        else ""
                    ),
                    "duration_sec": d.get("duration"),
                    "song_id": d.get("song_id"),
                }
            )

        if stopped_early:
            break

        print(f"取得済み: {len(new_songs)}件")

        pagination = data.get("pagination") or {}
        has_more = data.get("has_more")
        next_cursor = pagination.get("next_cursor")
        if not has_more or next_cursor is None:
            break
        cursor = next_cursor
        time.sleep(SLEEP_SEC)

    if incremental:
        print(f"新規: {len(new_songs)}件（既存 {len(existing_songs)}件は保持）")
        songs = new_songs + existing_songs
    else:
        songs = new_songs

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(songs, f, ensure_ascii=False, indent=2)

    import csv

    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "mv_id",
                "title",
                "m4a_url",
                "page_url",
                "score",
                "is_collab",
                "posted_at",
                "duration_sec",
                "song_id",
            ],
        )
        writer.writeheader()
        writer.writerows(songs)

    print(f"\n完了: {len(songs)}曲を {OUT_JSON} / {OUT_CSV} に出力しました。")


if __name__ == "__main__":
    main()
