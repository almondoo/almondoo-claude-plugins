# reviewing-dependency-updates

Dependabot / Renovate あるいは手動の依存関係更新 PR をマージするべきかを、**セキュリティ重視の 3 段階チェックリスト**で判定し、推奨アクション (`merge` / `保留` / `マージ不可`) を提示する Claude Code スキル。CI が緑だけではマージしません。

## なぜ必要か

依存関係更新 PR で起こりがちな見落としは「CI が通っているから安全」という早合点です。Dependabot / Renovate が作る **PR 自体は信頼できる**ものの、**バンプ先のパッケージは第三者コード**で、緑の CI が証明するのはあくまで「このプロジェクトのテストが落ちなかった」ことだけです。

このスキルは PR ごとに以下を順に検証します。

| Phase | 観点 | 主なチェック |
|-------|------|------------|
| **Phase 1: 基本検証** | CI とバージョンジャンプ | マトリックス全部が SUCCESS / `mergeable=MERGEABLE` / patch・minor・major の区別 |
| **Phase 2: セキュリティ検証** | サプライチェーン信頼性 | GitHub Security Advisory / 公式 org か / メンテナ変更 / 推移的依存の差分量 / GitHub Actions は SHA 固定推奨 |
| **Phase 3: 変更影響分析** | 互換性 | changelog の breaking change / `go` directive・`engines` 等の言語バージョン要件と CI マトリックス最小バージョンとの整合 / lockfile 整合性 |

各 Phase でブロッカーを見つけたらその場で **マージ不可** と判定して停止します。

## 出力

最終判定は次の表形式でユーザーに提示します。

```
| PR | バージョン変更 | CI | セキュリティ | 破壊的変更 | 判定 | 推奨アクション |
|----|--------------|-----|------------|----------|------|-------------|
```

推奨アクション (`merge` / `close` / `保留`) を提案するだけで、**マージは自動実行しません**。ユーザーが明示的に承認した PR だけを順に処理します。

## インストール

```
/plugin marketplace add almondoo/almondoo-claude-plugins
/plugin install reviewing-dependency-updates@almondoo-claude-plugins
```

## 使い方

明示的なトリガーは不要です。以下のような依頼で自動的に起動します。

- 「Dependabot の PR をレビューして」
- 「Renovate の更新 PR、マージしていい？」
- 「依存関係のバンプ PR が溜まってる、整理して」
- `gh pr list` で見つけた dependency update PR について判定を求めたとき

## なぜ Phase で区切るか

ブロッカーは早い Phase ほど検出コストが低くなります。

- Phase 1 は `gh pr view` 1 回で済む。
- Phase 2 はパッケージリサーチが必要だが、Phase 1 で落ちた PR には不要。
- Phase 3 は changelog の精読が必要で、最も時間がかかる。Phase 1 / 2 で落ちた PR には不要。

Phase 1 で CI が落ちている PR にいきなり changelog を読みに行くのは時間の無駄なので、必ず順序通りに走らせます。

## License

Apache-2.0
