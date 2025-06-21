# タグとリリースの作成手順

## PRマージ後の手順

1. **mainブランチに切り替え**
```bash
git checkout main
git pull origin main
```

2. **タグを作成**
```bash
# 注釈付きタグを作成
git tag -a v0.1.0 -m "Release v0.1.0: MCPサーバー標準構造への移行とPyPI公開準備"

# タグをプッシュ
git push origin v0.1.0
```

3. **GitHubでリリースを作成**
```bash
# ghコマンドでリリースを作成
gh release create v0.1.0 \
  --title "v0.1.0: 初回リリース" \
  --notes "## 🎉 docs-mcp v0.1.0

MCPサーバー標準構造に準拠した初回リリースです。

### 主な機能
- 📚 ローカルドキュメントの高速検索
- 🔍 セマンティック検索（OpenAI API使用）
- 📂 フォルダ・拡張子のフィルタリング
- 🌐 URLからのドキュメントインポート
- 🐙 GitHubリポジトリからのインポート

### インストール
\`\`\`bash
pip install docs-mcp
\`\`\`

詳細な使用方法は[README.md](https://github.com/herring101/docs-mcp#readme)をご覧ください。"
```

## タグの命名規則

- `v{major}.{minor}.{patch}` 形式を使用
- 例: `v0.1.0`, `v1.0.0`, `v1.0.1`

## 自動化について

GitHub Actionsの`release.yml`により、タグがプッシュされると自動的に：
1. GitHubリリースが作成される
2. PyPIへの公開がトリガーされる（PyPI_TOKENの設定が必要）