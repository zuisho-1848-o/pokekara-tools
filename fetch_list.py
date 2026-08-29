#!/usr/bin/env python3
"""
ポケカラ (Pokekara) の自分の投稿曲一覧を list_feed API から取得し、
タイトル + m4aダウンロードURLをCSV/JSONに出力する。

使い方:
    python3 fetch_list.py

事前準備:
    - BASE_PARAMS の u_share / unique_device_id / t_uid を
      自分の共有ページURLから取得した値に差し替える
      (例: https://u.pokekara.com/mv/xxxx?u_share=uXXXX&is_share_reward=0 )
"""

import datetime
import json
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


def main():
    songs = []
    seen_ids = set()
    cursor = None

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
            seen_ids.add(mv_id)
            songs.append(
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

        print(f"取得済み: {len(songs)}件")

        pagination = data.get("pagination") or {}
        has_more = data.get("has_more")
        next_cursor = pagination.get("next_cursor")
        if not has_more or next_cursor is None:
            break
        cursor = next_cursor
        time.sleep(SLEEP_SEC)

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
