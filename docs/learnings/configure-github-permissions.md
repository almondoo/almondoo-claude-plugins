# Learnings — configure-github-permissions

各セッションで得た知見を新しい順に記録。

## 2026-05-24 (multi-angle audit + meta-verify v0.1.1 → v0.1.2)

### 事実誤認の修正

- **Cat 5 (`gh issue close`) を Tier 3 と呼んでいたのは誤り**。ユーザー global `~/.claude/settings.json` の実エントリは `Bash(gh issue close *)` が `permissions.ask` 配下。global CLAUDE.md のルール「ask 配下は Tier 2」に従えば Tier 2 が正解。default を `deny` → `ask` に変更し、根拠を「reopen で巻き戻し可能なので保守的に ask が均衡」に書き直し。`gh pr close` は global で `permissions.deny` なので Cat 7 の Tier 3 default deny は維持。**教訓: skill が外部規約を引用する箇所は、その規約の現物 (この場合 global settings.json + global CLAUDE.md) を毎回 grep して整合確認すること。誤った権威付けは生成物の信頼性を一発で吹き飛ばす。**

### カテゴリ網羅性の補完

- **新 Cat 11 (delete-class) 追加**: `gh repo delete` / `gh issue delete` は global で deny 済みなのに 10 カテゴリのどこにも入っていなかった。`gh run delete` / `gh cache delete` / `gh secret delete` / `gh variable delete` も同居させて一括 default deny。Cat 8 (release) は既存名前空間が強いので分離せず維持。
- **gh repo create / fork / archive / gh codespace / gh gist / gh extension / gh auth login-logout** などの抜けは現バージョンでは導入見送り。理由: (a) global settings に該当エントリがないので default 判断の根拠が薄い、(b) 11 カテゴリでも質問体験がそろそろ限界、(c) ユーザーが必要なら手で書き足せばよい (`gh api` で間接実行も可)。将来「scripts を導入する判断」をする時に同時に拡張するのが筋。

### Step 7 (書き込み手順) の具体化

- **Edit vs Write 分岐の判定条件**を `data.permissions === undefined` で明示。
- **既存配列の順序保持**を Step 7 本文に明文化 (これまで Why this design に 1 行あるだけだった)。
- **mkdir 絶対パス化**: `mkdir -p .claude` の相対パスは Claude セッション中の cwd を信用できないので、Step 1 で取得した `git rev-parse --show-toplevel` を絶対パスで使う形に変更。
- **pre-write re-read**: Step 1 と Step 7 の間に user が手で settings.local.json を編集する可能性を Edge cases に追加 + 再 read で検出する手順を Step 7 末尾に追加。

### Step 5 / Step 6 の安全強化

- Step 5 「Keep both」の説明で **deny precedence の出典 URL** (`code.claude.com/docs/en/permissions`) を明示。これまでは断定だけで根拠なしだった。
- Step 6 の「skip 条件」を「additions 0 件 AND removals 0 件」に厳密化。conflict-driven removal がある場合は preview prompt を必ず通す。
- Step 6 の preview prompt が **global CLAUDE.md Tier 2 の「shared assets per-write confirmation」要件** をそのまま満たしている旨を本文に明記 (skill scope 承認だけでは skip 不可)。

### description / メタ整合

- **target file の明示** を 3 文書 (SKILL frontmatter / plugin.json / marketplace.json) すべてに展開: 「project-local `.claude/settings.local.json` のみ、`settings.json` と `~/.claude/settings.json` は触らない」。これまでは「project local」と暗黙だったので、ユーザーが「global で gh を allow したい」のつもりで起動するミスマッチを防ぐ。
- **競合スキル disambiguator** を SKILL description に 1 文追加: vs `fewer-permission-prompts` (transcript-driven) / vs `update-config` (汎用 settings)。
- **marketplace.json keywords の sync ズレ** (`fewer-prompts` が plugin.json にのみ存在) を修正。

### スキル仕様の確認結果 (棄却した指摘)

- **「README が `/configure-github-permissions:configure-github-permissions` を usage 提示しているが commands/ がないので動かない」疑い** → claude-code-guide エージェントが公式 docs (`code.claude.com/docs/en/skills.md#where-skills-live`) を引用して **動作確認**。Plugin skill は `/plugin-name:skill-name` 形式の slash command で commands/ ラッパー無しでも起動可能。README の usage 表記は正確。代わりに「slash command でも自然言語でも起動する」両モードを README で明示する形に補強。
- **「日本語キーワード description 追加」** → 棄却。CLAUDE.md は plugins/* 配下を英語 only と要求。SKILL の description は英語キーワード経由で日本語プロンプトも内部で十分マッチする想定で運用。

### pure-prompt 構成の意図 (将来の判断のため)

- 「merge / dedupe / conflict 検出を scripts に外出ししないのか」という指摘あり。今回は SKILL 本文に「pure-prompt の意図」を明示する形で対応 (Why this design 末尾)。trigger となるのは: (a) target が `~/.claude/settings.json` にも広がる、(b) gh 以外の tool (npm/pnpm/aws) も同じ category UX に乗る、(c) 並び順に意味付け (semantic grouping) を持たせる、のいずれか。

### 派生変更 (commit message に出ていない調整)

- Step 3 の batch 分割を **4+4+2 → 4+4+3** に変更 (Cat 11 追加に伴う再配置)。
- README ja/en に **「実行前の推奨 / Before running」** セクションを追加 (backup hint + jq 修復 hint)。
- README ja の typo「スキア」→「スキル」を修正 (再評価エージェントが検出)。

### バージョン経緯

- v0.1.1 → v0.1.2 (Cat 5 Tier 3 誤記訂正 + Cat 11 追加 + Step 5/6/7 安全強化 + meta 整合)。

## 2026-05-24 (self-review meta-loop polish v0.1.2 → v0.1.3)

### 残課題の収束

- **Cat 10 の「literal-glob」表現が過剰断言だった**: 「Bash permission matching is literal-glob, so curly-brace tokens never match real argv」と書いていたが、公式 `code.claude.com/docs/en/permissions` は wildcard `*` の挙動しか定義していない。`{...}` placeholder が literal 扱いになるのは「spec 外なので literal として処理される」という論理に書き直し。**教訓: 引用元 doc に存在する語彙だけで主張を組み立てる。doc 外の挙動を引用文体で書くと信頼性を下げる。**
- **Cat 9 (workflow execution) の Tier 関係性を明示**: Why this design の「Tier-3 categories default to deny」リストに Cat 9 を含めなかった一方、Cat 9 本文では Tier 関係性に言及がなく、なぜ deny default かが Tier フレームワーク上で不明瞭だった。「Tier 3 ではないが副作用大なのでこの skill では deny default、project 単位で `ask` 上書き可」と 1 文追加。

### バージョン経緯

- v0.1.2 → v0.1.3 (Cat 10 spec 引用厳密化 + Cat 9 Tier 注記)。

## 2026-05-21 (audit-driven cleanup v0.1.0 → v0.1.1)

### 気付き / gotcha

- **パターン文字列の space typo に注意**: L137 example が `Bash(gh api repos/{owner}/{repo}/pulls/* /comments)` で `*` と `/comments` の間に余分な space。実環境で match 不能 → copy-paste 利用者にハマる defect。example も settings.local.json と同じ厳密性で書く。
- **個人 namespace の漏洩を避ける**: 元 SKILL.md に `almondoo/review-agent` のような具体的 repo 名が残っていた。OSS 配布物では generic example に置換 (例: "an internal-only task tracker repo")。
- **動詞選択 "fix the behavior" は誤読を招く**: "不具合修正" と読まれる。意図は "lock in / force" → "would also force the same setting" 等の wording に置換。
- **フラグメント文に注意**: "Falls under global CLAUDE.md Tier 3." のような主語抜き文は読みづらい。"These commands fall under..." と補完。

### 設計判断 (確立済み pattern)

- **AskUserQuestion max 4 questions/call の harness 制約**: 10 categories を 3 batches (4+4+2) に分割が確定 pattern。一気に投げない。
- **Destructive categories は default `deny`**: merge / release / workflow exec / `gh api` は user CLAUDE.md Tier 3 (destructive external write) に整合させ、recommended option として `deny` を first に配置 + `(Recommended)` 表示。
- **`gh api` は `ask` default**: `-X DELETE` 等の method 切り替えが Bash arg-pattern で確実に isolate できないため、blanket `allow` も `deny` も適切でない。視覚確認前提の `ask` がバランス。

### バージョン経緯

- v0.1.0 (initial) → v0.1.1 (上記 4 件の wording / typo / namespace clean up)。
