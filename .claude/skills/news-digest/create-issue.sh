#!/usr/bin/env bash
# news-digest の手順7：その日のダイジェストを issue にし、HTML を artifact として添付する。
# 使い方: bash .claude/skills/news-digest/create-issue.sh YYYY-MM-DD
#   本文は .tmp/digest-issue-body.md（Markdown）から読む。終了時に削除する。
# gh api を直接呼ぶと環境によって承認待ちで止まるため、この1本にまとめて .claude/settings.json で実行を許可している。
# 終了コード: 0 成功（issue URL を出力） / 1 issue 作成失敗 / 2 issue は作成済みで artifact 失敗（issue URL を出力）
set -euo pipefail

DATE="${1:-}"
if [[ ! "$DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  echo "usage: bash $0 YYYY-MM-DD" >&2
  exit 1
fi

cd "$(git rev-parse --show-toplevel)"

BODY_FILE=".tmp/digest-issue-body.md"
HTML_FILE="digests/${DATE:0:4}/${DATE:5:2}/$DATE.html"
trap 'rm -f "$BODY_FILE"' EXIT

for f in "$BODY_FILE" "$HTML_FILE"; do
  if [ ! -f "$f" ]; then
    echo "error: $f がありません" >&2
    exit 1
  fi
done

R=$(git remote get-url origin | sed -E 's#\.git$##; s#.*[/:]([^/]+/[^/]+)$#\1#')

# 既にあれば 422 になるので無視する
gh api "repos/$R/labels" -f name=digest -f color=b45309 >/dev/null 2>&1 || true

if ! N=$(gh api "repos/$R/issues" -f title="digest: $DATE" -F body=@"$BODY_FILE" -f 'labels[]=digest' --jq .number); then
  echo "error: issue を作成できませんでした" >&2
  exit 1
fi
URL="https://github.com/$R/issues/$N"

if ! gh api -H "X-GitHub-Api-Version: 2026-03-10" "repos/$R/issues/$N/artifacts" \
  -f name="ダイジェスト $DATE" -F body=@"$HTML_FILE" -f type=embedded_html >/dev/null; then
  echo "$URL"
  echo "error: artifact を作成できませんでした（issue は作成済み）" >&2
  exit 2
fi

echo "$URL"
