#!/usr/bin/env bash
#
# VPS 上に GitHub Actions セルフホストランナーを設置するスクリプト。
#
# 【事前準備】
#   GitHub リポジトリ → Settings → Actions → Runners → New self-hosted runner
#   の画面に表示される「登録トークン」（A で始まる長い文字列）をコピーしておく。
#   ※トークンの有効期限は約1時間です。
#
# 【実行】VPS に root でログインして:
#   curl -fsSL https://raw.githubusercontent.com/woodstockv999/-/main/scripts/setup-runner.sh -o setup-runner.sh
#   sudo bash setup-runner.sh <登録トークン>
#
#   ※リポジトリを clone 済みなら: sudo bash scripts/setup-runner.sh <登録トークン>
#
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/woodstockv999/-}"
RUNNER_USER="${RUNNER_USER:-runner}"
RUNNER_NAME="${RUNNER_NAME:-$(hostname)-xserver-vps}"
TOKEN="${1:-${RUNNER_TOKEN:-}}"

if [[ -z "$TOKEN" ]]; then
  echo "エラー: 登録トークンが必要です。" >&2
  echo "  sudo bash setup-runner.sh <登録トークン>" >&2
  echo "  トークンは GitHub の Settings → Actions → Runners → New self-hosted runner に表示されます。" >&2
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "エラー: root で実行してください（sudo bash setup-runner.sh ...）。" >&2
  exit 1
fi

echo "==> 依存パッケージをインストール"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
# python3-venv/git は監視ジョブ本体に、jq は最新版取得に使用
apt-get install -y curl tar git jq python3 python3-venv python3-pip

echo "==> ランナー実行用ユーザー '$RUNNER_USER' を準備"
if ! id "$RUNNER_USER" &>/dev/null; then
  adduser --disabled-password --gecos "" "$RUNNER_USER"
fi

RUNNER_HOME="/home/$RUNNER_USER/actions-runner"
install -d -o "$RUNNER_USER" -g "$RUNNER_USER" "$RUNNER_HOME"

echo "==> 最新のランナーバージョンを取得"
VER="$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest | jq -r .tag_name)"
VER="${VER#v}"
if [[ -z "$VER" || "$VER" == "null" ]]; then
  echo "エラー: 最新バージョンの取得に失敗しました。" >&2
  exit 1
fi
TARBALL="actions-runner-linux-x64-${VER}.tar.gz"
URL="https://github.com/actions/runner/releases/download/v${VER}/${TARBALL}"

echo "==> ダウンロード & 展開 (v${VER})"
sudo -u "$RUNNER_USER" bash -c "cd '$RUNNER_HOME' && curl -fsSL -o '$TARBALL' '$URL' && tar xzf '$TARBALL' && rm -f '$TARBALL'"

echo "==> ランナーを設定（config.sh は root 不可のため $RUNNER_USER で実行）"
sudo -u "$RUNNER_USER" bash -c "cd '$RUNNER_HOME' && ./config.sh \
  --unattended \
  --url '$REPO_URL' \
  --token '$TOKEN' \
  --name '$RUNNER_NAME' \
  --labels self-hosted,vps,linux \
  --replace"

echo "==> サービスとして登録・起動（再起動後も自動起動）"
cd "$RUNNER_HOME"
./svc.sh install "$RUNNER_USER"
./svc.sh start
sleep 2
./svc.sh status || true

echo ""
echo "==> 完了しました。"
echo "    GitHub の Settings → Actions → Runners に '$RUNNER_NAME' が"
echo "    緑色の Idle で表示されれば成功です。"
echo "    続けて Actions タブ → company-news-monitor → Run workflow で動作確認できます。"
