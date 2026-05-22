# Learnings — configure-github-permissions

各セッションで得た知見を新しい順に記録。

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
