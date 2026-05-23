# almondoo-claude-plugins

**almondoo** が公開する [Claude Code](https://code.claude.com/docs/en/plugins) プラグインマーケットプレイス。

このリポジトリはマーケットプレイス本体であり、各プラグインは `plugins/` 配下のサブディレクトリとして管理されます。プラグインのエントリは `.claude-plugin/marketplace.json` で一元管理しています。

## 収録プラグイン

| プラグイン | 概要 |
|---|---|
| [`configure-github-permissions`](plugins/configure-github-permissions) | `.claude/settings.local.json` 上で `gh` コマンドの permission を 10 カテゴリ × 3 択 (allow / ask / deny) でインタラクティブに設定。破壊的カテゴリ (merge / release / workflow exec / gh api) は deny がデフォルト |
| [`parallel-audit`](plugins/parallel-audit) | 指示ファイル (CLAUDE.md / CLAUDE.local.md / AGENTS.md / GEMINI.md / SKILL.md) を multi-agent で並列 audit。N 個の subagent を独立に走らせ、再現性 (≥2/3 デフォルト) で issue を絞り込んで fix を提案。`target_type` 分岐で CLAUDE.md / SKILL.md を統一処理、event-driven 診断として設計 (Phase 1 で routine 利用を警告) |

## マーケットプレイスの追加

Claude Code 内で:

```
/plugin marketplace add almondoo/almondoo-claude-plugins
```

プラグインの閲覧・インストール:

```
/plugin                                           # Discover UI を開く
/plugin install <plugin-name>@almondoo-claude-plugins
```

後でアップデートする場合:

```
/plugin marketplace update almondoo-claude-plugins
```

## リポジトリ構成

```
almondoo-claude-plugins/
├── .claude-plugin/
│   └── marketplace.json     # マーケットプレイスマニフェスト (全プラグインを列挙)
├── plugins/                 # 各サブディレクトリが 1 プラグイン
└── LICENSE                  # Apache-2.0
```

新規プラグインは `plugins/<plugin-name>/` として配置し、`.claude-plugin/marketplace.json` の `"plugins"` 配列に `"source": "./plugins/<plugin-name>"` で登録します。

## プラグインの追加手順

1. プラグインディレクトリを作成:
   ```
   plugins/<plugin-name>/
   ├── .claude-plugin/
   │   └── plugin.json       # name + description (必須)
   ├── skills/               # 任意
   ├── agents/               # 任意
   ├── commands/             # 任意
   ├── hooks/                # 任意
   ├── .mcp.json             # 任意
   └── README.md
   ```
2. `.claude-plugin/marketplace.json` の `"plugins"` にエントリを追加:
   ```json
   {
     "name": "<plugin-name>",
     "description": "...",
     "source": "./plugins/<plugin-name>",
     "version": "0.1.0"
   }
   ```
3. ローカル検証:
   ```
   /plugin marketplace add .
   /plugin install <plugin-name>@almondoo-claude-plugins
   /plugin validate .
   ```

マニフェストの完全なリファレンスは [Claude Code プラグインドキュメント](https://code.claude.com/docs/en/plugins) および [marketplace ドキュメント](https://code.claude.com/docs/en/plugin-marketplaces) を参照してください。

## ライセンス

[Apache-2.0](LICENSE)
