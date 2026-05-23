# Frontend design reference — `skill-eval-viewer`

Captured design contract for the HTML report. Owned by `render_html.py`. Read this before editing the renderer or changing the look-and-feel.

---

## 1. Audience assumption

The reader has already read the plugin's README (or has the README open in another tab). The report focuses exclusively on **the findings of this iteration** — verdict, layer numbers, fixes. Plugin overview / glossary / "what is skill-eval?" prose lives in `README.md` (English) and `README-ja.md` (Japanese mirror), not in the report.

Implications for the renderer:

- Open with a banner-level "README pointer" — one sentence above the table of contents telling the reader where to go for terminology.
- Per-eval descriptions (the `description` field in `evals.json`) still live in the report, because they are iteration-specific: which evals were run, what each one tested.
- Do not duplicate glossary terms inline. When the verdict text says `hard_fail`, trust the reader to know it; the README definition is one click away.

Rule of thumb: a reader who arrived from a Slack link should understand the verdict, the static / dynamic numbers, and the proposed fixes — assuming they spent 30 seconds skimming the README first.

---

## 2. Aesthetic identity — "Field Audit"

Editorial engineering. The same identity the viewer has shipped since v0.1:

- **Display font**: Fraunces (variable, opsz + wght).
- **Body font**: system serif (`ui-serif`, Charter, Iowan Old Style, Georgia).
- **Mono**: system (`ui-monospace`, SF Mono, Menlo, Consolas).
- **Bone paper background** with a faint SVG-generated grain.
- **Vermillion accent** (`#c8421f` light / `#e2553a` dark) used sparingly for top rules, section counters, and a single border on cards.
- **Hairline horizontal rules** between sections.
- **Numbered sections** in mono (`01`, `02`, …) drawn from CSS counters; the same counter style is mirrored in the table of contents.
- **Single page-load motion**: each top-level section fades up with a 90 ms stagger. No scroll-triggered animation, no per-element hover wobble.

Do not introduce a second accent color. Do not switch the display font. The whole identity is the editorial restraint — adding flourishes erodes it.

Light/dark theme follows the OS via `prefers-color-scheme`. Both themes share the same numeric design tokens; only the color palette swaps.

---

## 3. Design tokens

Defined as CSS custom properties at the top of `render_html.py`'s `CSS` constant. When adding a token, add it to both the light and dark blocks.

| Group | Tokens | Notes |
|---|---|---|
| Surface | `--bg`, `--paper`, `--rule`, `--rule-strong` | `bg` is the canvas; `paper` is the slightly raised card surface |
| Text | `--ink`, `--ink-soft`, `--muted` | Three levels: primary, secondary, tertiary |
| Accent | `--accent`, `--accent-soft` | Vermillion + a paled tint for backgrounds |
| Status | `--ok`, `--ok-bg`, `--warn`, `--warn-bg`, `--fail`, `--fail-bg`, `--info`, `--info-bg` | Paired fg/bg for badges |
| Typography | `--font-display`, `--font-body`, `--font-mono` | One value per role |

The type scale is set inline (no scale variable). Use `clamp()` for any heading that needs to be responsive. Tabular numerals are on by default (`font-variant-numeric: tabular-nums oldstyle-nums`) so metric columns align.

Layout column is 880 px max. The container padding is asymmetric: more top than bottom. Mobile breakpoint at 640 px collapses the section-number `::before` to flow above the heading instead of beside it.

---

## 4. Section taxonomy

The HTML always renders these six sections, in this order. A section is allowed to be empty (showing a "this run did not produce …" note) but must not be omitted — the consistent skeleton makes the report skimmable across iterations.

| # | Section | Source data | Purpose |
|---|---|---|---|
| (banner) | README pointer | hard-coded in renderer | One-line "for plugin overview / glossary, see README" hint above the TOC |
| §01 | Evals run | `evals.json` (workspace copy) | What each eval tests, with the prompt and the assertions |
| §02 | Verdict | parsed from `report.md` | One-line ship/needs-work/etc. call with a paragraph of reasoning |
| §03 | Static layer | `static.json` | Score + axes + evidence |
| §04 | Dynamic layer | `benchmark.json` | with/without/Δ + per-eval + differentiating assertions |
| §05 | Top fixes | parsed from `report.md` | Before/after change proposals (max 3) |
| §06 | Files | walked from workspace | Index of artifacts on disk for the curious reader |

Multi-angle sub-reports (`NN-*.md`) remain a fallback section, appended after §06 as a collapsible appendix. Not part of the core narrative.

Each section header is preceded by a mono `§NN` counter. Reset `counter-reset: section` on `.container`.

The README pointer sits between the banner and the table of contents, styled as a single paragraph on `var(--paper)` with a left `var(--accent)` rule. Same chrome as the TOC card, half the size.

---

## 5. Component patterns

### 5.1 Hero / banner

The page opens with:

- **Kicker** in mono caps: `SKILL EVALUATION REPORT`.
- **Title** in Fraunces display, ~52 px on desktop.
- **Subtitle** in mono: the workspace path.
- A 4 px vermillion rule on the top edge of the banner.

No motion on the banner itself — it sets the type, the rest of the page animates.

### 5.2 README pointer (banner-adjacent)

One sentence on `var(--paper)` with a 2 px `var(--accent)` left rule, sitting between the banner and the TOC. Single line of text in body serif, ~13.5 px, `var(--ink-soft)`. Both Japanese and English copies hard-coded in `LOCALES["ja"|"en"]["readme_pointer"]`.

Purpose: redirect first-time readers to the README without taking space inside the numbered sections. Do not link directly — workspaces are often opened over `file://` and the relative path back to the README is non-trivial; the README is canonical enough that the reader can find it.

### 5.3 Evals run (§01)

A vertical stack of eval cards. Each card:

- **Eval name** as Fraunces display, ~22 px.
- **One-paragraph description** (pulled from `evals.json` → new `description` field).
- **Prompt** in a `<pre>` block with a left vermillion bar (existing `<pre>` style).
- **Assertions** as a `<ul>` with each item as `kind` (small mono caps) + assertion text.

Cards do not have a vermillion top bar — only the `<pre>` inside does. The visual rhythm is: heading, paragraph, indented evidence.

### 5.4 Verdict card (§02)

Single block. Largest type unit in the report after the banner.

- **Verdict label** (`Ship-ready` / `Needs work` / `Net negative` / `Inconclusive`) as Fraunces display, ~36 px, in `--accent`.
- **Variance flag** if any, as a smaller mono tag next to the label.
- **One paragraph** explaining why (body serif). This is the same paragraph that opens the verdict section in `report.md`.

Left edge: 4 px vermillion bar matching the banner's top rule. No card padding tricks — this is content, not chrome.

### 5.5 Static layer (§03)

- **Big number**: the score, ~64 px Fraunces. Color: `--ok` if ≥0.8, `--warn` if 0.4-0.79, `--fail` if hard_fail tripped.
- **Three badges** beneath: `score`, `hard_fail`, `warnings` (existing badge style).
- **Per-axis table** (existing). Add tooltip-style mono captions on the `severity` column header explaining what `hard_fail` / `warn` / `info` mean.

### 5.6 Dynamic layer (§04)

- **Metric stack**: three lines, one per metric (`pass_rate`, `time`, `tokens`). Each line:
  - Metric name in body serif, small.
  - Three numeric cells in a CSS grid: `with_skill`, `without_skill`, `Δ`.
  - The `Δ` cell carries the vermillion accent if positive direction = with_skill better (pass_rate↑ wins, time↓ wins, tokens↓ wins).
- **Per-eval breakdown** — existing table.
- **Differentiating assertions** — each rendered as a quote-style block with two large paired numbers (with-rate vs without-rate). No table.

### 5.7 Top fixes (§05)

Each fix is a `<article class="fix">`. Inside, in order:

1. **Heading** in Fraunces display: "**What is wrong** — *one-line summary*". When the report is rendered in a non-English language (per skill-eval `SKILL.md`'s report-language policy), this heading is translated.
2. **Before** block:
   - Mono kicker `BEFORE`.
   - Body paragraph describing the current behavior, including the exact symptom an iteration would see (concrete log line, file path, pass-rate, etc.).
3. **After** block:
   - Mono kicker `AFTER`.
   - Body paragraph describing the proposed state.
   - Optional code block if the change has a literal text edit.
4. **How to verify** in italic body, prefixed with "Verifiability:".

Order is fixed: problem → current → proposed → how to verify. Do not collapse before/after into a single paragraph — the visual two-block contrast IS the readability gain over the old rank/category schema.

The renderer keeps the old machine-facing metadata (rank, category, priority, source) as `<meta>`-style mono micro-text under the heading so engineers can still grep / index by category, but the prose body never starts with those tokens.

### 5.8 File index (§06)

Plain `<ul>` of the workspace files actually present, with absolute paths in mono. Useful for the engineer who wants to dig further; invisible to the casual reader unless they scroll past §05.

---

## 6. Layout & motion

- **Single column**. No sidebars. The 880 px max-width ensures comfortable line length.
- **Section padding**: top 56 px / bottom 16 px. The first section sits flush against the TOC card.
- **Card spacing**: 32 px between cards in §01 (evals) and §05 (fixes).
- **Motion**: only the initial fade-up cascade. No hover transforms beyond the existing link / row hover.

---

## 7. Content sources & report-language policy

- **Verdict text, top-fix narratives, paragraphs**: pulled from `report.md`. The renderer parses by H2 headers — sections named `Verdict` (or its translated equivalent) map to §02; `Top issues to fix` / `Top fixes` (or its translated equivalent) map to §05. Header matching is case-insensitive and accepts a translation-pair pattern on the same line. Translated keywords accepted by the parser live in the renderer's locale tables (`LOCALES` in `scripts/render_html.py`); reference docs stay English-only.
- **Eval descriptions**: pulled from `evals.json` → `description` field. Falls back to the prompt if no description present.
- **README pointer copy / section titles / verdict labels / before-after kickers**: hard-coded inside the renderer in `LOCALES["ja"|"en"]`.

**Language is driven by `report.md` content**, which the orchestrating `skill-eval` skill confirms with the user via `AskUserQuestion` before writing the markdown (see `SKILL.md` Inputs → Report language and Step 6a). The renderer inspects the first 400 characters of `report.md` and picks `ja` if CJK ≥ 25%, otherwise `en` — by the time it runs, `report.md` is already in the target language, so the auto-detect simply mirrors it. There is intentionally no CLI flag on the renderer: introducing one created two competing sources of truth (the flag vs. the markdown), and forgetting to pass it produced silently mismatched chrome. The markdown is the single source.

The skill-eval workspace (`<skill-name>-eval-workspace/`) is treated like `tmp/` artefacts (see project `CLAUDE.md` language policy), so non-English text is permitted in the workspace even though core SKILL.md / `references/` stay English-only.

Plugin overview, glossary, and trigger criteria live in `plugins/skill-eval/README.md` (Japanese) and `plugins/skill-eval/README-en.md` (English). The report never duplicates that content — it links the reader there via the banner-adjacent README pointer.

---

## 8. Implementation constraints

- Single self-contained HTML file. Inline CSS. No JS.
- Stdlib Python only. Markdown parsing is the existing regex-based pass.
- One external dependency: the Fraunces Google Fonts link. System-serif fallback works offline.
- The renderer must produce a valid HTML page even when `report.md` is missing — fall back to a banner + glossary + "no evaluation found" empty note. The skeleton is the value, the data is the variable.

---

## 9. When to update this reference

Edit `frontend-design.md` whenever:

- A new section is added to the report (define its purpose and component pattern here first).
- A new design token is introduced (record it under §3).
- A component pattern changes shape (update §5 with the new structure and rationale).

Do **not** edit this file just to record a bug fix in `render_html.py`. The reference is for *intent*; the code carries the implementation detail.
