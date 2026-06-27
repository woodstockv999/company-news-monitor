# company-news-monitor

> 指定した企業の最新ニュースを自動収集し、新着があればメールで通知する GitHub Actions ベースの監視ツールです。

## 概要

Google ニュース RSS などの公開フィードを定期巡回し、既読でない新着記事が見つかったときだけメールを送信します。
監視対象の企業は `companies.yml` を編集するだけで追加・削除できます。GitHub Actions のセルフホストランナー上で 6 時間ごとに自動実行されます。

## 機能

- **6 時間ごとの自動実行**: GitHub Actions スケジュールで 00/06/12/18 UTC（09/15/21/03 JST）に実行
- **差分通知**: `state.json` で既読を管理し、新着記事のみを通知（初回実行はベースライン化のみ）
- **複数ソース対応**: RSS / Atom フィードと HTML スクレイピングの両方に対応
- **企業別まとめメール**: 1 通のメールに全社の新着を整理してまとめて送信
- **7 日以上前の記事は除外**: 古い記事を「新着」として誤通知しない
- **手動実行対応**: `workflow_dispatch` で GitHub UI からいつでも即時実行可能

## ディレクトリ構成

```
company-news-monitor/
├── .github/workflows/monitor.yml  # GitHub Actions ワークフロー
├── app/
│   ├── config.py      # 設定読み込み
│   ├── notifier.py    # メール送信
│   ├── sources.py     # RSS/HTML 取得
│   └── state.py       # 既読管理
├── companies.yml      # 監視企業リスト（ここを編集）
├── monitor.py         # エントリポイント
├── state.json         # 既読履歴（自動管理）
└── requirements.txt
```

## セットアップ

### 1. リポジトリをフォーク / クローン

```bash
git clone https://github.com/woodstockv999/company-news-monitor.git
cd company-news-monitor
```

### 2. セルフホストランナーを登録

GitHub リポジトリの `Settings > Actions > Runners` からランナーを追加してください。  
セットアップスクリプトも同梱しています。

```bash
bash scripts/setup-runner.sh
```

### 3. GitHub Secrets を設定

| シークレット名 | 説明 |
|--------------|------|
| `SMTP_USER` | 送信元 Gmail アドレス |
| `SMTP_PASS` | Gmail アプリパスワード（16 桁） |
| `MAIL_FROM` | 送信元表示アドレス |
| `MAIL_TO` | 通知先メールアドレス |

### 4. 監視企業を設定

`companies.yml` を編集して監視したい企業を追加します。

```yaml
companies:
  - id: example_corp
    name: サンプル株式会社
    sources:
      - type: rss
        url: "https://news.google.com/rss/search?q=%22サンプル%22&hl=ja&gl=JP&ceid=JP:ja"
```

変更を `git push` するだけで次回実行から反映されます。

## ローカルでのドライラン

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python monitor.py --dry-run
```

## ライセンス

MIT
