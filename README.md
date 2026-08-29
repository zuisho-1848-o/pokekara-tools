# ポケカラ 楽曲一覧取得 手順

自分がポケカラに投稿した楽曲の「タイトル + m4aダウンロードURL」一覧を
CSV/JSONで取得する手順。

## 1. 前提: 自分の共有情報を確認する

自分のマイページ、もしくは投稿した楽曲のシェアURLを開くと、以下のような形式になっている。

```
https://u.pokekara.com/mv/<mv_id>?u_share=<自分のuser_share_id>&is_share_reward=0
```

この `u_share=uXXXXXXXXXXXX` が自分のユーザーIDにあたる（`t_uid` にも同じ値を使う）。

## 2. 一覧取得APIの仕様

エンドポイント:

```
https://api.pokekara.com/x/moment/list_feed
```

主なクエリパラメータ:

| パラメータ | 内容 |
|---|---|
| `u_share` / `t_uid` | 自分のユーザーID（`uXXXXXXXXXXXX`） |
| `appid` | `com.pokekara.web` 固定 |
| `phonetype` | `web` 固定 |
| `request_refer` | `h5` 固定 |
| `unique_device_id` | 適当なUUIDでOK（ブラウザから叩いた際に払い出された値をそのまま流用） |
| `cursor` | ページング用（2ページ目以降に付与） |

レスポンス構造（抜粋）:

```
data.moments[].data.title       # 曲タイトル
data.moments[].data.video_url   # m4aのダウンロードURL
data.moments[].data.mv_id_str   # 投稿ID
data.moments[].data.duration    # 秒数
data.has_more                   # 次ページの有無
data.pagination.next_cursor     # 次ページ取得用カーソル
```

`has_more` が `true` の間、`pagination.next_cursor` の値を次のリクエストの
`cursor` パラメータに入れて呼び出すことで全件取得できる（1回あたり10件）。

## 3. 取得スクリプトの実行

同ディレクトリの [`fetch_list.py`](fetch_list.py) を使う。

```bash
python3 fetch_list.py
```

- スクリプト内 `BASE_PARAMS` の `u_share` / `t_uid` / `unique_device_id` を
  自分の値に書き換えてから実行する（現状は memo.md に記載の値が入っている）。
- 実行すると `has_more` が `false` になるまで自動でページングし、
  取得件数を逐次表示する。
- 出力ファイル:
  - `songs.json` — 全件の配列（mv_id, title, m4a_url, page_url, score, posted_at, duration_sec, song_id）
  - `songs.csv` — 同内容のCSV（Excel等でそのまま開ける文字コード）
- `page_url` は曲ごとの共有ページのフルURL（`mv_id` と `u_share` から組み立て）。
- `score` は0〜100の数値スコア。アプリ上のSSS/SS等の文字ランクはクライアント側の
  音程解析ロジックで計算されており、APIからは取得できないため未対応。

## 4. 実行結果（参考）

2026-08-11時点で **376曲** を取得済み（`songs.json` / `songs.csv`）。

## 5. 次のステップ（m4a本体のダウンロード）

`songs.csv` の `m4a_url` 列を使えば、以下のようなコマンドで一括ダウンロードできる。

```bash
python3 - <<'PY'
import csv, os, urllib.request

os.makedirs("downloads", exist_ok=True)
with open("songs.csv", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        title = row["title"].replace("/", "_")
        dest = f"downloads/{row['mv_id']}_{title}.m4a"
        if os.path.exists(dest):
            continue
        print("downloading:", title)
        urllib.request.urlretrieve(row["m4a_url"], dest)
PY
```

## 6. まとめてダウンロード（実運用）

同ディレクトリの [`download_m4a.py`](download_m4a.py) が実際のダウンロード処理。

```bash
python3 download_m4a.py
```

- サーバー負荷対策として、1件ずつ順番にダウンロードし、1件ごとに1.5〜3秒のランダム待機を挟む。
- 失敗した曲は数回リトライしてから諦める（他の曲の処理は継続）。
- **保存先ファイルが既に存在する場合は自動でスキップ**するため、
  途中で止めても再実行すれば続きからダウンロードされる。

## 7. 新曲が増えたときの再同期

[`sync.py`](sync.py) を実行すると「最新一覧の再取得 → 未ダウンロード分だけダウンロード」を
まとめて行える。

```bash
python3 sync.py
```

`fetch_list.py` は毎回全件を取得し直す（軽量なメタデータAPI呼び出しのみ）が、
`download_m4a.py` 側が既存ファイルをスキップするため、実質的に差分ダウンロードになる。
最後に `generate_player.py` が実行され、`player.html` も最新の内容に更新される。
定期的にこれを叩けば、新しく投稿した曲だけが自動でダウンロードされる。

## 8. ブラウザで再生する（player.html）

[`generate_player.py`](generate_player.py) を実行すると、`songs.json` と
`downloads/` の中身から自己完結型の `player.html` が生成される。

```bash
python3 generate_player.py
```

生成された `player.html` をブラウザで直接開けば使える（サーバー不要、外部通信なし）。

機能:
- タイトル検索（部分一致・リアルタイム）
- 列ヘッダークリックでソート（タイトル / 評価 / 投稿日 / 長さ、昇順⇄降順トグル）
- 評価・投稿日の範囲指定での絞り込み
- 行クリックで再生、下部プレイヤーで再生/一時停止・前へ/次へ
- 音量スライダー（`localStorage` に保存され次回も引き継ぐ）
- 「1曲リピート」「全曲リピート（表示中の絞り込み・並び順のリストを順送り）」

ダウンロード済みの曲はローカルファイルを再生する。未ダウンロードの曲は
一覧に「未DL」バッジが付き、再生ボタンを押した瞬間だけ配信元URLから
ストリーミング再生する（単曲再生なので通常のアプリ利用と同等の負荷）。

`sync.py` 実行時に自動で再生成されるため、通常は個別に実行する必要はない。

## 9. 個人評価（★1〜5）をつけて保存する

player.htmlに「マイ評価」列があり、★をクリックすると1〜5段階で評価できる
（同じ★をもう一度クリックすると解除）。

**サーバー経由での保存（推奨）**

```bash
python3 rating_server.py
```

を実行し、表示される `http://localhost:8765/player.html` をブラウザで開くと、
評価がクリックのたびに同ディレクトリの `ratings.json` に保存される
（`mv_id` → 評価点のJSON）。`player.html` を直接file://で開いた場合と違い、
ブラウザのキャッシュ削除や別ブラウザ利用で消える心配がない。

`generate_player.py`（`sync.py`経由も含む）で`player.html`を再生成しても、
サーバーはディスクから毎回読み直すのでブラウザをリロードするだけで反映される
（サーバー再起動は不要）。

**file://で直接開いた場合のフォールバック**

サーバーを起動せずに`player.html`を直接ダブルクリックで開いても評価機能は動くが、
その場合はブラウザの`localStorage`に保存される。`localStorage`は`file://`という
ローカルファイル共通のオリジンに紐づくため、ブラウザの閲覧データ削除や別ブラウザ・
別PCの利用で消えてしまう可能性がある。保存を確実にしたい場合は上記のサーバー経由を使うこと。
