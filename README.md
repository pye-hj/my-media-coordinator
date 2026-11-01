# my-media-coordinator

関心プロフィール（`profile.md`）に沿ってメディアを収集・整理する Claude Code のスキル集の**雛形**。

このリポジトリはスキルとテンプレートだけを持つ。実際の収集は、このリポジトリを複製した各自の private リポジトリで行い、関心や生成物もそちらで管理する。

| 種別 | パス | 雛形（このリポジトリ） | 複製リポジトリ |
|---|---|---|---|
| スキル・テンプレート | `.claude/skills/**`, `profile_template.md`, `README.md`, `.gitignore`, `.github/**`, `digests/.gitkeep` | 管理・編集する | 編集しない（雛形から取り込む） |
| 利用者データ | `profile.md`, `digests/YYYY/**`, `state/**` | 持たない | コミットする |

## 収録スキル

- `/news-digest` — `profile.md` の関心に沿ってニュースを集め、HTML の日次ダイジェストを `digests/` に書き出してコミットし、issue で知らせる。

## 複製リポジトリを作る

```bash
git clone https://github.com/pye-hj/my-media-coordinator.git <name>
cd <name>
git remote rename origin template
git remote set-url --push template DISABLED   # 雛形への誤 push を防ぐ
gh repo create <name> --private --source . --remote origin --push
```

続けて初期設定を行う。

1. `.gitignore` の「利用者データ」ブロックを削除する（複製側では利用者データをコミットするため）。
2. `profile_template.md` を `profile.md` にコピーし、関心を書く。
3. コミットしてプッシュする。

```bash
cp profile_template.md profile.md
git add .gitignore profile.md
git commit -m "初期設定"
git push -u origin main
```

`.github/workflows/template-guard.yml` は雛形専用のチェックで、複製リポジトリでは実行されない。削除する必要はない（削除すると、雛形の更新を取り込むときに衝突することがある）。逆に `.github/workflows/digest-notify.yml` は複製リポジトリでだけ動く（「使う」を参照）。

## 使う

- Claude Code で `/news-digest` を実行する。ダイジェストと既読記録（`state/`）はコミットされ、`origin` の `main` にプッシュされる。
- あわせて `digest` ラベル付きの issue「digest: YYYY-MM-DD」が立つ。本文に今日の要点があり、HTML 版は issue の Artifacts から Preview で読める。読んだら issue を close すれば、Issues 一覧が未読リストになる。
  - issue の artifact は GitHub の public preview の機能。使えない場合でも、git 上のファイルと issue の本文は残る。
- issue が立つと `digest-notify` ワークフローが作成者をメンションし、要点をコメントする。issue は本人の名義で立つので GitHub は本人に通知しないが、このコメントの通知は届く。
  - 受け取り方（メール / GitHub Mobile）は GitHub の Settings → Notifications の「Participating, @mentions and custom」で選ぶ。
  - 複製リポジトリで Actions を無効にしていると届かない。
- 毎日自動で実行するには、`/schedule` で複製リポジトリを対象にしたルーティンを作る。
- `profile.md` を書き換えたらコミットしてプッシュする。翌日以降のダイジェストに反映される。

## 雛形の更新を取り込む

```bash
git pull --no-rebase template main
git push
```

複製側には利用者データのコミットがあるため、雛形とは履歴が分かれている。`--no-rebase`（マージで統合）を付けないと、git は「Need to specify how to reconcile divergent branches」で止まる。rebase は使わない（プッシュ済みのコミットを書き換えることになり、force push が必要になる）。毎回付けるのが手間なら、複製リポジトリで一度 `git config pull.rebase false` を実行しておく。

複製側でスキルやテンプレートを編集していなければ衝突しない。

## 雛形の開発に参加する人へ

- 変更は PR 経由で入れる。`main` への直接 push はできない。
- 利用者データ（`profile.md`, `digests/YYYY/**`, `state/**`）をコミットしない。`.gitignore` で無視されており、PR では `template-guard` が検査する。
- スキルを手元で試すときは、上の手順で複製リポジトリを作ってそちらで実行する。
