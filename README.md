# almondoo-claude-plugins

A [Claude Code](https://code.claude.com/docs/en/plugins) plugin marketplace published by **almondoo**.

This repository is the marketplace itself — the place where individual plugins
will live as subdirectories under `plugins/`. It is currently a scaffold with
no plugins yet; entries will be added to `.claude-plugin/marketplace.json` as
plugins ship.

## Install the marketplace

From Claude Code:

```
/plugin marketplace add almondoo/almondoo-claude-plugins
```

Then browse and install plugins:

```
/plugin                                           # open the Discover UI
/plugin install <plugin-name>@almondoo-claude-plugins
```

To update later:

```
/plugin marketplace update almondoo-claude-plugins
```

## Repository layout

```
almondoo-claude-plugins/
├── .claude-plugin/
│   └── marketplace.json     # marketplace manifest (lists every plugin)
├── plugins/                 # each subdirectory is one plugin
└── LICENSE                  # Apache-2.0
```

A new plugin is added as `plugins/<plugin-name>/` and registered as an entry
in `.claude-plugin/marketplace.json` with `"source": "./plugins/<plugin-name>"`.

## Adding a plugin

1. Create the plugin directory:
   ```
   plugins/<plugin-name>/
   ├── .claude-plugin/
   │   └── plugin.json       # name + description (required)
   ├── skills/               # optional
   ├── agents/               # optional
   ├── commands/             # optional
   ├── hooks/                # optional
   ├── .mcp.json             # optional
   └── README.md
   ```
2. Register the plugin in `.claude-plugin/marketplace.json` under `"plugins"`:
   ```json
   {
     "name": "<plugin-name>",
     "description": "...",
     "source": "./plugins/<plugin-name>",
     "version": "0.1.0"
   }
   ```
3. Validate locally:
   ```
   /plugin marketplace add .
   /plugin install <plugin-name>@almondoo-claude-plugins
   /plugin validate .
   ```

See the [Claude Code plugin docs](https://code.claude.com/docs/en/plugins) and
[marketplace docs](https://code.claude.com/docs/en/plugin-marketplaces) for
the full manifest reference.

## License

[Apache-2.0](LICENSE)
