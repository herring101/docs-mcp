# 開発者ガイド

このドキュメントは、docs-mcpプロジェクトの開発、リリース、公開に関する包括的なガイドです。

## 目次

1. [開発環境のセットアップ](#開発環境のセットアップ)
2. [開発ワークフロー](#開発ワークフロー)
3. [テスト](#テスト)
4. [リリース手順](#リリース手順)
5. [PyPI公開](#pypi公開)
6. [トラブルシューティング](#トラブルシューティング)

## 開発環境のセットアップ

### 前提条件

- Python 3.12以上
- [uv](https://github.com/astral-sh/uv)（推奨）またはpip
- Git
- GitHub CLI（`gh`コマンド、オプション）

### 初期セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/herring101/docs-mcp.git
cd docs-mcp

# uvを使用する場合
uv sync

# pipを使用する場合
pip install -e ".[dev]"
```

### 環境変数

開発時に使用する環境変数を`.env`ファイルに設定：

```bash
# OpenAI APIキー（セマンティック検索機能のテスト用）
OPENAI_API_KEY=sk-...

# ドキュメントのベースディレクトリ
DOCS_BASE_DIR=/path/to/your/docs
```

## 開発ワークフロー

### ブランチ戦略

- `main`: 本番ブランチ
- `develop`: 開発ブランチ（オプション）
- `feature/*`: 新機能開発
- `fix/*`: バグ修正
- `release/*`: リリース準備

### コミット規約

[Conventional Commits](https://www.conventionalcommits.org/ja/)に従います：

- `feat:` 新機能
- `fix:` バグ修正
- `docs:` ドキュメントのみの変更
- `style:` コードの意味に影響しない変更
- `refactor:` バグ修正や機能追加を含まないコード変更
- `test:` テストの追加や修正
- `chore:` ビルドプロセスやツールの変更
- `ci:` CI/CDの設定変更

### 開発フロー

1. **新しいブランチを作成**
```bash
git checkout -b feature/new-feature
```

2. **変更を実装**
```bash
# コードを編集
# テストを実行
uv run pytest tests/ -v
```

3. **リントとフォーマット**
```bash
# リント
uv run ruff check .

# 自動修正
uv run ruff check . --fix

# フォーマット
uv run ruff format .

# 型チェック
uv run pyright
```

4. **コミット**
```bash
git add .
git commit -m "feat: 新機能の追加"
```

5. **プルリクエスト作成**
```bash
git push -u origin feature/new-feature
gh pr create
```

## テスト

### テストの実行

```bash
# 全テストを実行
uv run pytest tests/ -v

# 特定のテストファイルを実行
uv run pytest tests/test_document_manager.py -v

# カバレッジレポート付き
uv run pytest tests/ --cov=mcp_server_docs --cov-report=html
```

### テストの種類

- **単体テスト**: 個々のクラスや関数のテスト
- **統合テスト**: コンポーネント間の連携テスト
- **E2Eテスト**: MCPサーバーとしての動作テスト

### テスト作成のガイドライン

1. テストファイルは`test_*.py`の形式で命名
2. テストクラスは`Test*`、テスト関数は`test_*`で始める
3. 各テストは独立して実行可能にする
4. モックは最小限に留める
5. エッジケースをカバーする

## リリース手順

### 1. バージョン更新

```bash
# pyproject.tomlのバージョンを更新
# 例: 0.1.0 → 0.2.0
```

### 2. CHANGELOG更新

`CHANGELOG.md`に変更内容を記載：

```markdown
## [0.2.0] - 2025-01-21

### 追加
- 新機能の説明

### 変更
- 既存機能の改善

### 修正
- バグ修正の内容
```

### 3. リリースブランチ作成

```bash
git checkout -b release/v0.2.0
git add -A
git commit -m "chore: v0.2.0のリリース準備"
git push -u origin release/v0.2.0
```

### 4. プルリクエストとマージ

```bash
gh pr create --title "Release v0.2.0" --body "v0.2.0のリリース"
# レビュー後、マージ
```

### 5. タグとGitHubリリース

```bash
# mainブランチに切り替え
git checkout main
git pull origin main

# タグを作成
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0

# GitHubリリースを作成
gh release create v0.2.0 \
  --title "v0.2.0" \
  --notes "CHANGELOGの内容をここに記載"
```

## PyPI公開

### 初回設定

#### PyPIアカウントとAPIトークン

1. [PyPI](https://pypi.org/)でアカウントを作成
2. Account settings → API tokens でトークンを作成
3. GitHubリポジトリのSecrets（`PYPI_API_TOKEN`）に設定

### 手動公開

```bash
# ビルド
uv build

# TestPyPIでテスト（初回推奨）
uv publish --publish-url https://test.pypi.org/legacy/

# 本番公開
export UV_PUBLISH_TOKEN="pypi-your-token-here"
uv publish
```

### 自動公開

GitHub Actionsにより、タグプッシュ時に自動的に公開：

```yaml
# .github/workflows/release.yml
on:
  push:
    tags:
      - 'v*'
```

## トラブルシューティング

### よくある問題

#### インポートエラー

```bash
# パッケージを再インストール
uv sync --reinstall
```

#### 型チェックエラー

```bash
# pyrightの設定を確認
cat pyproject.toml | grep -A5 "[tool.pyright]"

# 個別ファイルをチェック
uv run pyright src/mcp_server_docs/server.py
```

#### テスト失敗

```bash
# 詳細な出力でテスト実行
uv run pytest tests/ -vv --tb=long

# 特定のテストのみ実行
uv run pytest tests/test_document_manager.py::TestDocumentManager::test_init -v
```

#### PyPI公開エラー

- **"Package already exists"**: バージョン番号を上げる
- **認証エラー**: APIトークンを確認
- **ビルドエラー**: `uv cache clean && uv sync`

### デバッグ方法

```bash
# MCPサーバーをデバッグモードで起動
MCP_DEBUG=1 uv run docs-mcp

# ログレベルを上げる
LOG_LEVEL=DEBUG uv run docs-mcp
```

## コントリビューション

プロジェクトへの貢献を歓迎します！詳細は[CONTRIBUTING.md](CONTRIBUTING.md)をご覧ください。

### 貢献の流れ

1. Issueを作成（または既存のIssueを選択）
2. フォークしてブランチを作成
3. 変更を実装し、テストを追加
4. プルリクエストを作成
5. レビューを受けて修正
6. マージ

### コードレビューのポイント

- [ ] テストが追加されているか
- [ ] ドキュメントが更新されているか
- [ ] 型アノテーションが適切か
- [ ] エラーハンドリングが適切か
- [ ] パフォーマンスへの影響は許容範囲か

## その他の情報

### 依存関係の管理

```bash
# 新しい依存関係を追加
uv add package-name

# 開発用依存関係を追加
uv add --dev package-name

# 依存関係の更新
uv update
```

### ドキュメントの生成

```bash
# APIドキュメントを生成（将来的に追加予定）
# uv run sphinx-build docs/ docs/_build/
```

### パフォーマンス最適化

- 大量のドキュメントを扱う場合は、`DOCS_FOLDERS`で対象を限定
- セマンティック検索は必要な場合のみ有効化
- 並行処理の数を環境に合わせて調整

---

質問や問題がある場合は、[Issues](https://github.com/herring101/docs-mcp/issues)でお知らせください。