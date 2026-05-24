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

## 2026-05-24 (README + rationale compression v0.1.4 → v0.1.5)

イテレーション5。0.1.4 で繰越にした項目のうち、README 改修と Cat 弁明文圧縮の 5 件を実装。

### README 改修

- **README ja/en に "いつ project-local で override したくなるか" 節を新設** (敵対 P0a 緩和版): OSS repo / CI monorepo / 個人 sandbox の 3 シナリオを明示。敵対的レビューが「skill ごと存在意義なし」と主張した最強の批判への部分的回答。「global と完全に同じ」なら no-op で終わる + override の現実例が示せた以上、skill の価値命題は守れた判断。
- **README ja/en に "パターン記法 (colon vs space)" 注記を追加** (敵対 P1b): skill の colon 形式と global の space 形式が等価であることを公式仕様引用付きで明示。混在しても動作差なし、grep 用に手で揃えてよい、という運用上の指針。
- **README ja/en の "Layout" 節に scripts なし構成の意図を 1 行追記** (構造 #5): SKILL.md の "Why this design" 節への参照リンクを README からも貼り、parallel-audit 比で「軽量に見える」誤認を防止。

### SKILL.md 圧縮

- **Cat 5 弁明文を 4 文→2 文に圧縮** (敵対 P2b): 「Tier 2 の説明 + reversible なので default ask + OSS で deny に締める override 例 + reopen を pair」を 2 文で言い切る形に。why は残しつつ冗長な敬語的補足を削除。
- **Cat 10 弁明文を 4 段落→2 段落に圧縮** (敵対 P2b): flag combo 列挙 + 公式 warning 引用 + GET-only ユースケース + path-scoped allow rule の 4 セクションを、それぞれ 1 文ずつにまとめて 2 段落に圧縮。`{owner}/{repo}` 警告も保持。

### 見送り判断 (今回適用しなかった項目)

- **"11 categories" literal 集約** (構造 #4): SKILL.md 内に 7 箇所あるが、frontmatter / Overview / "When NOT to Use" は数字が読み手の検索性・直感に寄与しており「the categories above」型の指示語に置換すると逆に読みにくくなる。cat 追加時の touch ファイル数を減らす利得 (せいぜい 3-4 箇所減) に対して読みやすさの劣化コストが見合わない。Cat 追加が現実に近づいた時点で再評価する。
- **preset shortcut (Conservative/Balanced/Aggressive)**: 構造インパクトが大きく単独 patch にすべき。Step 2.5 と統合する形で 0.1.6 以降で検討。
- **global diff mode** (~/.claude/settings.json を読んで effective に同じ entry を skip): merge semantics 再現は実装複雑。0.1.6 以降で検討。
- **evals/evals.json 追加** (構造 #3): trigger 競合の eval は skill-creator の専門領域に踏み込むため、別ワークフローで実施。

### バージョン経緯

- v0.1.4 → v0.1.5 (README 3 節改修 + Cat 5/10 圧縮 = 計 5 件)。

## 2026-05-24 (UX/structural deepening v0.1.3 → v0.1.4)

イテレーション4 (UXシミュ + 敵対的レビュー + 構造/スケール の 3 視点) で 8 件の修正項目に絞り込み実施。

### UX 起因の実害修正

- **HIGH: pattern 正規化規則を Step 4 に追加**. `Bash(gh pr view *)` (global の space 形式) と `Bash(gh pr view:*)` (skill の colon 形式) は公式仕様上 equivalent だが、string 比較では別物 → 既存ファイルが space 形式だと skill が無自覚に colon 形式で重複追加していた。Step 4 dedupe で「両形式を同パターンと見なす」を明文化。**教訓: skill が出力する記法と既存ファイルの記法が違う場合、normalize 規則を skill 内で明示しないと idempotency が壊れる。**
- **HIGH: Step 2.5 を新設**. 「11 問答えてから "何も変わりませんでした" と告げられる UX」を回避するため、Step 3 の前に「現状サマリー + Continue / Exit」を提示。preset shortcut (Conservative/Balanced/Aggressive) はさらに大きい構造変更を伴うため次イテに繰越。
- **MED: Step 3 option.description にカテゴリ固有の要約を強制**. これまでは `Auto-allow (allow) — execute without a prompt every time` の generic 文しか指示せず、ユーザーが Cat 1 と Cat 7 で同じ allow を選ぶ判断材料が options 側に乗らなかった。Cat 1 の sample + 「destructive category の deny は irreversibility を call out すべし」を明示。
- **MED: Step 5 conflict 質問にプレフィックス**. 「Step 6 preview 後にまとめて適用」の disclaimer をどの conflict 質問にも必須化。「個別 conflict ごとに勝手に書き換わる」誤解を防止。さらに batched 質問の順序を `(array name, then pattern string)` で再現可能化。

### 構造の伸びる余地への対応

- **HIGH: Step 3 batch 分割を `⌈N/4⌉` 式に書き換え**. 4+4+3 の hard-code を残しつつ「将来 cat が増減したら式から再導出」と明文化。これで Cat 12 / 13 を足すたびに Step 3 を手で書き換える必要が消える。
- **MED: Default selection logic 節を Categories 直前に新設**. これまで Cat 5 / Cat 9 / Cat 10 / Cat 11 にそれぞれ別言で書いていた「なぜこの default か」の判定根拠を 4 ルール (pure-read → allow / external reversible → ask / Tier 3 irreversible → deny / arg-pattern fragile → ask) に集約。新 cat 追加時の判断が機械的になる。

### 価値命題の補強

- **When NOT to Use 段落追加**. 敵対的レビューの「skill ごと存在意義なし」批判への部分的応答。「global で既に充実」「prompt が頻発する前」「単発 1 verb 編集」「team 共有 policy」の 4 つを「使わなくていい case」として明示。これで dead config 量産を skill 側で抑制する責任を持たせる。
- **description に trigger phrase 追加**: `too many gh prompts` / `edit settings.local.json for gh` / `organize gh permissions` / `auto-approve gh` を直接含めて、敵対的 P3 の trigger 網羅性ギャップを埋め。

### 次イテに繰越した項目

これらは構造インパクト or 設計判断の重さで分離:

- **preset shortcut** (Conservative/Balanced/Aggressive を Step 2.5 と統合): 構造変更が大きい。Step 2.5 の Continue/Exit が落ち着いてから 0.1.5 で実装予定。
- **global diff mode** (~/.claude/settings.json を読んで effective に同じ entry を skip 提案): merge semantics 再現が必要で実装複雑。0.1.5 以降で検討。
- **README override シナリオ 2-3 個追加** (敵対 P0a 緩和版): 別 patch で README 重点改修。
- **記法統一注記の README 追加** (P1b): 同上で README 改修にまとめる。
- **Cat 5 / Cat 10 弁明文の 50-70% 圧縮** (P2b): 安全に圧縮するには再度評価が必要。
- **"11 categories" literal 集約** (構造 #4): cat 追加時に同時実施したい。
- **README Layout 軽量意図注記** (構造 #5): README 改修にまとめる。
- **evals/evals.json 追加** (構造 #3): trigger 競合 (fewer-permission-prompts / update-config) の評価。skill-creator の専門領域に踏み込むので別タスクで。

### バージョン経緯

- v0.1.3 → v0.1.4 (UX 起因の実害 4 件 + 構造伸びる余地 2 件 + 価値命題 2 件 = 計 8 件)。

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
