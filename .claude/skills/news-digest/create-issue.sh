#!/usr/bin/env bash
# news-digest の手順8：その日のダイジェストを issue にし、HTML を artifact として添付する。
# 使い方: bash .claude/skills/news-digest/create-issue.sh YYYY-MM-DD
#   本文は .tmp/digest-issue-body.md（Markdown）から読む。終了時に削除する。
#   タイトルは profile.md の `## issue` 節の `- タイトル: ...` から作る（無ければ既定の書式）。
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

# issue のタイトル。profile.md の `## issue` 節の `- タイトル:` 行を書式とし、日付の置き換え文字を展開する。
# 置き換え文字: {yyyy} 年4桁 / {mm} 月2桁 / {dd} 日2桁 / {m} 月 / {d} 日。行が無い・空なら既定の書式。
DEFAULT_TITLE_FORMAT='今日のニュース：{yyyy}年{mm}月{dd}日'
TITLE_FORMAT=""
if [ -f profile.md ]; then
  TITLE_FORMAT=$(awk '
    /<!--/ { c = 1 }
    c { if (/-->/) c = 0; next }
    /^## / { s = ($0 ~ /^## issue[ \t]*$/); next }
    s && /^- タイトル(:|：)/ { sub(/^- タイトル(:|：)[ \t]*/, ""); sub(/[ \t\r]+$/, ""); print; exit }
  ' profile.md)
fi
[ -n "$TITLE_FORMAT" ] || TITLE_FORMAT="$DEFAULT_TITLE_FORMAT"
YYYY=${DATE:0:4}; MM=${DATE:5:2}; DD=${DATE:8:2}
TITLE=$TITLE_FORMAT
TITLE=${TITLE//\{yyyy\}/$YYYY}
TITLE=${TITLE//\{mm\}/$MM}
TITLE=${TITLE//\{dd\}/$DD}
TITLE=${TITLE//\{m\}/$((10#$MM))}
TITLE=${TITLE//\{d\}/$((10#$DD))}

R=$(git remote get-url origin | sed -E 's#\.git$##; s#.*[/:]([^/]+/[^/]+)$#\1#')

# 既にあれば 422 になるので無視する
gh api "repos/$R/labels" -f name=digest -f color=b45309 >/dev/null 2>&1 || true

if ! N=$(gh api "repos/$R/issues" -f title="$TITLE" -F body=@"$BODY_FILE" -f 'labels[]=digest' --jq .number); then
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
