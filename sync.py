#!/usr/bin/env python3
"""
最新の楽曲一覧を取得し直し、未ダウンロードの曲だけをダウンロードし、
プレイヤー(player.html)を再生成する。

新曲が増えたときは、このスクリプトを再実行するだけでよい:
    python3 sync.py

内部で fetch_list.py → download_m4a.py → generate_player.py を順に呼び出す。
いずれも「既存はスキップ／上書きのみ」の作りなので、何度実行しても安全。
fetch_list.py はデフォルトで差分取得（前回取得済みの曲に出会った時点で打ち切り）。
全件取り直したい場合は `python3 sync.py --full` のように渡すと fetch_list.py に
そのまま引き継がれる。
"""

import subprocess
import sys


def main():
    fetch_args = sys.argv[1:]
    steps = [
        ["python3", "fetch_list.py", *fetch_args],
        ["python3", "download_m4a.py"],
        ["python3", "generate_player.py"],
    ]
    for cmd in steps:
        print(f"\n===== 実行: {' '.join(cmd)} =====")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"エラーで中断しました: {' '.join(cmd)}")
            sys.exit(result.returncode)


if __name__ == "__main__":
    main()
