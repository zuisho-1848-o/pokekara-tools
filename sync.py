#!/usr/bin/env python3
"""
最新の楽曲一覧を取得し直し、未ダウンロードの曲だけをダウンロードし、
プレイヤー(player.html)を再生成する。

新曲が増えたときは、このスクリプトを再実行するだけでよい:
    python3 sync.py

内部で fetch_list.py → download_m4a.py → generate_player.py を順に呼び出す。
いずれも「既存はスキップ／上書きのみ」の作りなので、何度実行しても安全。
"""

import subprocess
import sys

STEPS = [
    ["python3", "fetch_list.py"],
    ["python3", "download_m4a.py"],
    ["python3", "generate_player.py"],
]


def main():
    for cmd in STEPS:
        print(f"\n===== 実行: {' '.join(cmd)} =====")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"エラーで中断しました: {' '.join(cmd)}")
            sys.exit(result.returncode)


if __name__ == "__main__":
    main()
