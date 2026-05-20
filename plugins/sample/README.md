# sample

A minimal sample plugin for the
[almondoo-claude-plugins](../../README.md) marketplace.

It exists so you can:

- See the canonical layout of a Claude Code plugin at the smallest possible
  size.
- Copy it as a starter when adding a new plugin to this marketplace.
- Smoke-test that the marketplace is wired up correctly end-to-end.

## Layout

```
sample/
├── .claude-plugin/
│   └── plugin.json          # plugin manifest (name + description required)
├── skills/
│   └── hello/
│       └── SKILL.md         # the only skill in this plugin
└── README.md
```

## Install

```
/plugin marketplace add almondoo/almondoo-claude-plugins
/plugin install sample@almondoo-claude-plugins
```

## Usage

```
/sample:hello
```

Replies with one line containing the current working directory and git
branch — e.g. `Hello from sample plugin — cwd=/Users/me/proj branch=main`.

## License

[Apache-2.0](../../LICENSE)
