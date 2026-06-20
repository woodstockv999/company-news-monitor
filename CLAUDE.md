# プロジェクト概要（Claude 向けメモ）

特定企業のニュースリリースを日次で監視し、新着があればメール通知するツール。
GitHub Actions の cron で VPS 上のセルフホストランナーを起動し、`monitor.py` を実行する。

## 企業の追加・削除は「チャットベース」で行う

ユーザーはチャットで「○○を監視に追加して」「△△を外して」と指示する。
Claude は次の手順で対応すること:

1. `companies.yml` を編集する（`manage.py` を使ってもよい）。
   - RSS があれば `type: rss` を優先（安定）。
   - RSS が無ければ `type: html` + `item_selector`（記事リンクの CSS セレクタ）。
   - URL が不明なときは、企業名から公式ニュース/IR ページの RSS を調べて提案する。
2. 変更を**コミットして push** する（コミットしないと Actions に反映されない）。
3. 追加時は、次回実行で「ベースライン化（その時点の記事を既読登録するだけ）」され、
   **通知は次回以降の新着から**始まることをユーザーに伝える。

```bash
# 追加例
python manage.py add --id sony --name "ソニーグループ" --rss "https://example.com/feed.xml"
# 削除例
python manage.py remove --id sony
# 一覧
python manage.py list
```

`companies.yml` を直接編集しても同じ（`manage.py` は入力補助）。

## 触ってはいけない/自動管理されるもの

- `state.json` … 既読履歴。`monitor.py` が自動更新し、Actions が自動コミットする。手動編集しない。
- 企業を `companies.yml` から削除すると、`state.json` の該当履歴は次回実行時に自動で除去される。

## メール送信

Gmail SMTP。認証情報は GitHub Secrets（`SMTP_USER` / `SMTP_PASS` / `MAIL_TO` / 任意で `MAIL_FROM`）。
コードやリポジトリに認証情報を書かないこと。

## 動作確認

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/python monitor.py --dry-run   # メールを送らず検知結果を表示
```
