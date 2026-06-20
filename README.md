# 企業ニュース監視ツール

特定企業のニュースリリースを**日次で監視**し、新着があった場合のみ**メール通知**する仕組みです。

- スケジューリング: **GitHub Actions**（cron）
- 実行環境: **Xserver VPS 上のセルフホストランナー**（`runs-on: self-hosted`）
- 通知: **Gmail SMTP**
- 企業の登録・削除: `companies.yml` の編集、または `manage.py` のコマンド一発

---

## 仕組み

```
GitHub Actions (毎日 09:00 JST にcron起動)
        │  workflow をディスパッチ
        ▼
VPS のセルフホストランナー  ──►  monitor.py 実行
        │                          ├─ companies.yml の各企業の RSS/HTML を取得
        │                          ├─ state.json の既読履歴と差分を比較
        │                          ├─ 新着があれば Gmail SMTP でメール送信
        │                          └─ state.json を更新
        ▼
更新された state.json を git commit & push（次回の比較基準になる）
```

- **既読履歴**は `state.json` に企業ごとに保存され、毎回リポジトリへコミットされます。
- 企業を**新規登録した直後**は、その時点の記事を「ベースライン」として記録するだけで通知しません（過去記事の大量通知を防ぐため）。**次回以降の新着から通知**されます。
- 1社の取得に失敗しても他社の処理は止まりません（エラーはログに記録）。

---

## ファイル構成

| ファイル | 役割 |
|---|---|
| `companies.yml` | 監視対象企業の一覧（ここを編集すれば登録/削除完了） |
| `manage.py` | 企業の追加・削除・一覧表示の補助CLI |
| `monitor.py` | 監視本体。GitHub Actions から実行される |
| `state.json` | 既読履歴（自動更新・自動コミット） |
| `app/` | 取得・通知・設定のコアモジュール |
| `.github/workflows/monitor.yml` | スケジュール定義 |

---

## 企業の登録・削除

### 方法1: CLI（おすすめ）

```bash
# 一覧
python manage.py list

# RSSフィードで登録
python manage.py add --id sony --name "ソニーグループ" \
  --rss "https://www.example.com/news/feed.xml"

# ニュース一覧ページ（HTML）で登録（記事リンクのCSSセレクタを指定）
python manage.py add --id foo --name "Foo社" \
  --html "https://www.example.com/news/" --selector "a.news-list__link"

# 削除
python manage.py remove --id sony
```

### 方法2: `companies.yml` を直接編集

```yaml
companies:
  - id: sony                         # 一意なID（半角英数）
    name: ソニーグループ              # 通知に表示される名前
    sources:
      - type: rss                    # RSS/Atom フィード（最も安定・推奨）
        url: https://www.example.com/news/feed.xml

  - id: foo
    name: Foo社
    sources:
      - type: html                   # ニュース一覧ページをスクレイピング
        url: https://www.example.com/news/
        item_selector: "a.news-list__link"   # 記事リンクを選ぶCSSセレクタ
```

> **RSS が使える場合は RSS を強く推奨**します（安定して正確）。RSS が無い企業のみ `html` を使い、ブラウザの開発者ツールで記事リンクの CSS セレクタを調べて `item_selector` に指定してください。

変更後はコミットしてください（GitHub Actions が読むのはリポジトリ上のファイルです）:

```bash
git add companies.yml && git commit -m "監視企業を更新" && git push
```

---

## ローカルでの動作確認

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt

# メールを送らず、検知結果だけ表示（state.json は更新されます）
./.venv/bin/python monitor.py --dry-run
```

---

## セットアップ

### 1. Gmail アプリパスワードを取得

通常の Gmail パスワードでは SMTP ログインできません。**アプリパスワード**が必要です。

1. Google アカウントで**2段階認証を有効化**（必須）
2. https://myaccount.google.com/apppasswords にアクセス
3. アプリ名（例: `news-monitor`）を入力して生成 → **16桁のパスワード**をコピー

### 2. GitHub Secrets を登録

リポジトリの **Settings → Secrets and variables → Actions → New repository secret** で以下を登録:

| Secret 名 | 値 |
|---|---|
| `SMTP_USER` | 送信元 Gmail アドレス（例: `jsbseven170@gmail.com`） |
| `SMTP_PASS` | 上で取得した16桁アプリパスワード（空白は詰める） |
| `MAIL_TO` | 通知先アドレス。カンマ区切りで複数可（例: `jsbseven170@gmail.com`） |
| `MAIL_FROM` | （任意）送信元表示。未設定なら `SMTP_USER` を使用 |

### 3. VPS にセルフホストランナーを設置（Xserver VPS / Ubuntu 24.04）

```bash
ssh root@210.131.212.62

# 必要パッケージ
apt update && apt install -y python3 python3-venv python3-pip git

# 専用ユーザーで動かす（root 直は非推奨）
adduser --disabled-password --gecos "" runner
su - runner
```

リポジトリの **Settings → Actions → Runners → New self-hosted runner** を開き、
表示される **Download / Configure コマンドをそのまま `runner` ユーザーで実行**します（トークン入りのコマンドが画面に出ます）。概ね以下の流れです:

```bash
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-x64.tar.gz -L <画面に表示されるURL>
tar xzf actions-runner-linux-x64.tar.gz
./config.sh --url https://github.com/woodstockv999/- --token <画面に表示されるトークン>
```

常駐サービス化（再起動後も自動起動）:

```bash
sudo ./svc.sh install runner
sudo ./svc.sh start
sudo ./svc.sh status   # Active (running) を確認
```

### 4. 動作確認

GitHub の **Actions タブ → company-news-monitor → Run workflow** で手動実行できます。
ログでベースライン設定が走り、`state.json` がコミットされれば成功です。
翌日以降、新着があればメールが届きます。

---

## スケジュールと運用上の注意

- **実行時刻**: `.github/workflows/monitor.yml` の cron は `0 0 * * *`（00:00 UTC = **09:00 JST**）。
  時刻変更はこの行を編集します（cron は UTC 基準）。
- **schedule は default ブランチ（`main`）でのみ発火**します。開発ブランチにあるだけでは日次実行されません。
  運用を開始するには **`main` にマージ**してください。`workflow_dispatch`（手動実行）はどのブランチでも可能です。
- **ランナーが起動している必要があります**。VPS やサービスが止まると、その間のスケジュールは実行されません（`svc.sh status` で常時稼働を確認）。
- セルフホストランナーは信頼できるリポジトリ専用にしてください（private リポジトリ推奨）。

---

## カスタマイズの勘所

- 監視頻度を上げる: cron を `0 */6 * * *`（6時間ごと）などに変更。
- 履歴の保持件数: `monitor.py` の `MAX_SEEN`（既定1000件／社）。
- 通知文面: `app/notifier.py` の `render_text` / `render_html`。
