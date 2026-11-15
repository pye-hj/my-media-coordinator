# my-media-coordinator

関心プロフィール（`profile.md`）に沿ってメディアを収集・整理する Claude Code のスキル集の**雛形**。

このリポジトリはスキルとテンプレートだけを持つ。実際の収集は、このリポジトリを複製した各自の private リポジトリで行い、関心や生成物もそちらで管理する。

| 種別 | パス | 雛形（このリポジトリ） | 複製リポジトリ |
|---|---|---|---|
| スキル・テンプレート | `.claude/skills/**`, `.claude/settings.json`, `profile_template.md`, `README.md`, `.gitignore`, `.github/**`, `digests/.gitkeep` | 管理・編集する | 編集しない（雛形から取り込む） |
| 利用者データ | `profile.md`, `digests/YYYY/**`, `state/**` | 持たない | コミットする |

## 収録スキル

- `/news-digest` — `profile.md` の関心に沿ってニュースを集め、HTML の日次ダイジェストを `digests/` に書き出してコミットし、issue で知らせる。
- `/profile-settings` — `profile.md` の配信設定（表示機能の on/off と設定、雛形に新しく加わった節）を、選択肢に答えて確認・編集する。

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

4. Claude Code で `/profile-settings` を実行し、表示機能を設定する（「表示機能」を参照）。

`.github/workflows/template-guard.yml` は雛形専用のチェックで、複製リポジトリでは実行されない。削除する必要はない（削除すると、雛形の更新を取り込むときに衝突することがある）。逆に `.github/workflows/digest-notify.yml` は複製リポジトリでだけ動く（「使う」を参照）。

## 使う

- Claude Code で `/news-digest` を実行する。ダイジェストと既読記録（`state/`）はコミットされ、`origin` の `main` にプッシュされる。
- あわせて `digest` ラベル付きの issue「digest: YYYY-MM-DD」が立つ。本文に今日の要点があり、HTML 版は issue の Artifacts から Preview で読める。読んだら issue を close すれば、Issues 一覧が未読リストになる。
  - issue の artifact は GitHub の public preview の機能。使えない場合でも、git 上のファイルと issue の本文は残る。
  - issue の作成は `.claude/skills/news-digest/create-issue.sh` が行い、その実行は（表示機能のスクリプトとともに）`.claude/settings.json` で許可済み（無人実行でも承認待ちで止まらないようにするため）。複製側で許可を足したいときは `settings.json` ではなく `.claude/settings.local.json`（追跡されない）に書く。`settings.json` を編集すると、雛形の更新を取り込むときに衝突することがある。
- issue が立つと `digest-notify` ワークフローが宛先（既定は作成者）をメンションし、要点をコメントする。issue は本人の名義で立つので GitHub は本人に通知しないが、このコメントの通知は届く。
  - 受け取り方（メール / GitHub Mobile）は GitHub の Settings → Notifications の「Participating, @mentions and custom」で選ぶ。
  - 複製リポジトリで Actions を無効にしていると届かない。
  - 宛先を変えるには、複製リポジトリの Settings → Secrets and variables → Actions → Variables に `DIGEST_NOTIFY_TO` を作る。値はユーザー名や `org/team` を空白・カンマ・改行で区切って並べる（先頭の `@` は省略可）。設定すると作成者は自動では入らないので、自分も受け取るなら自分も書く。

    ```bash
    gh variable set DIGEST_NOTIFY_TO --body "alice bob my-org/news-team"
    ```

  - private リポジトリでは、リポジトリの read 権限を持つ人・チームにしか通知されない。チームの指定は組織のリポジトリでだけ有効。
  - メンションの代わりに、各自がリポジトリを Watch（Custom → Issues）しても issue が立った通知は届く（作成者本人には届かない）。
- 毎日自動で実行するには、`/schedule` で複製リポジトリを対象にしたルーティンを作る。
- `profile.md` を書き換えたらコミットしてプッシュする。翌日以降のダイジェストに反映される。
  - `## 曜日ごとの調整` に、曜日（月〜日）や「平日」「休日」（土日・祝日・東証の休場日）ごとの差分を自然文で書ける（例：`- 休日：NPB を「常に追う」扱い。経済は週間まとめを1本だけ。`）。書かなければ毎日同じ。調整はダイジェストの構成に黙って反映され、出力の形は変わらない。
  - `profile.md` にこの節が無ければ、`/profile-settings` で追加する。

### 表示機能

記事とは別の決まった形式の欄を、ダイジェストの冒頭に足せる。既定ではすべて off で、off のままならダイジェストは従来どおり。`/profile-settings` を実行し、on にする機能とその設定を選ぶ。

| 機能名 | 内容 | 設定 |
|---|---|---|
| 天気 | 1地域のその日の予報を、時刻ごとの表（天気のアイコン・気温・降水確率）で表示する。issue の本文にも1行で載る | 地域（必須）、緯度経度、間隔（時間、既定 3） |

- 天気の予報は [Open-Meteo](https://open-meteo.com/) から取る（キー不要）。クラウド環境で実行する場合は、環境のネットワーク設定で `api.open-meteo.com` への接続を許可する。取得できなかった日は、その旨だけが表示される。
- 機能を足すとき（雛形の開発者向け）は、`features/<名前>.md`（設定と手順）と断片を出力するスクリプトを置き、`SKILL.md` の「表示機能」の表に1行加え、断片の CSS を `digest-template.html` に足す。スクリプトの実行は `.claude/settings.json` で許可する。
  - `/profile-settings` は、`SKILL.md` の表を機能の一覧として、仕様ファイルの最初の見出し直後の段落を説明として、`## 設定` の表（`項目`・`必須`・`意味`）を設定項目として読む。とりうる値の一覧と既定値は `意味` 列に書く。`weather.md` と同じ形式を保つ。

## 雛形の更新を取り込む

```bash
git pull --no-rebase template main
git push
```

複製側には利用者データのコミットがあるため、雛形とは履歴が分かれている。`--no-rebase`（マージで統合）を付けないと、git は「Need to specify how to reconcile divergent branches」で止まる。rebase は使わない（プッシュ済みのコミットを書き換えることになり、force push が必要になる）。毎回付けるのが手間なら、複製リポジトリで一度 `git config pull.rebase false` を実行しておく。

複製側でスキルやテンプレートを編集していなければ衝突しない。

取り込んだら `/profile-settings` を実行する。新しく加わった表示機能や節が示され、その場で設定できる。

## 雛形の開発に参加する人へ

- 変更は PR 経由で入れる。`main` への直接 push はできない。
- 利用者データ（`profile.md`, `digests/YYYY/**`, `state/**`）をコミットしない。`.gitignore` で無視されており、PR では `template-guard` が検査する。
- スキルを手元で試すときは、上の手順で複製リポジトリを作ってそちらで実行する。
