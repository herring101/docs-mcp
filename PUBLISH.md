# PyPI公開手順

## 初回設定

### 1. PyPIアカウントの作成

1. [PyPI](https://pypi.org/)でアカウントを作成
2. メールアドレスを確認
3. 2要素認証を設定（推奨）

### 2. APIトークンの作成

1. PyPIにログイン
2. Account settings → API tokens
3. "Add API token"をクリック
4. トークン名を入力（例: `docs-mcp`）
5. Scope: "Entire account"を選択（初回のみ、後でプロジェクト限定に変更可能）
6. トークンをコピーして安全に保管

### 3. GitHubシークレットの設定

1. GitHubリポジトリの Settings → Secrets and variables → Actions
2. "New repository secret"をクリック
3. Name: `PYPI_API_TOKEN`
4. Value: コピーしたAPIトークン（`pypi-`で始まる）

## 手動公開

### ローカルから公開する場合

```bash
# 1. ビルド
uv build

# 2. TestPyPIでテスト（オプション）
uv publish --publish-url https://test.pypi.org/legacy/

# 3. 本番PyPIに公開
uv publish
```

### 環境変数での認証

```bash
export UV_PUBLISH_TOKEN="pypi-your-token-here"
uv publish
```

## 自動公開（GitHub Actions）

### リリース作成時に自動公開

1. GitHubでリリースを作成
2. バージョンタグを設定（例: `v0.1.0`）
3. リリースを公開すると自動的にPyPIにアップロード

### 手動トリガー

1. Actions → Publish to PyPI
2. "Run workflow"をクリック

## 公開前チェックリスト

- [ ] バージョン番号を更新（`pyproject.toml`）
- [ ] CHANGELOGを更新
- [ ] テストが全て成功
- [ ] READMEが最新
- [ ] ライセンスファイルが存在
- [ ] 不要なファイルが`.gitignore`に含まれている

## トラブルシューティング

### "Package already exists"エラー

- 同じバージョンは再アップロードできません
- バージョン番号を上げて再度公開

### 認証エラー

- APIトークンが正しいか確認
- トークンの前後に空白がないか確認
- トークンのスコープが適切か確認

### ビルドエラー

```bash
# キャッシュをクリア
uv cache clean

# 依存関係を再インストール
uv sync

# 再度ビルド
uv build
```