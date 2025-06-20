# docs-mcp

ユーザーが設定したドキュメントを効率的に検索・参照できるMCPサーバーです。

## 主な機能

- 📄 **ドキュメント一覧表示** - すべてのドキュメントとその説明を一覧表示
- 🔍 **grep検索** - 正規表現を使った高速な全文検索
- 🧠 **セマンティック検索** - OpenAI Embeddingsを使った意味的な類似検索
- 📝 **ドキュメント取得** - 指定したドキュメントの全内容を取得

## 必要な環境

- uv （install方法は[こちら](https://docs.astral.sh/uv/getting-started/installation/)）
- OpenAI APIキー（セマンティック検索を使用する場合）

## インストール

```bash
git clone https://github.com/herring101/docs-mcp.git
cd docs-mcp
uv sync
```

## セットアップ

### 1. 環境変数を設定

```bash
cp .env.example .env
# .envファイルを編集してOpenAI APIキーを設定
```

### 2. ドキュメントを配置

`docs/`ディレクトリにドキュメントを配置します。デフォルトでは、以下の拡張子のファイルが読み込まれます：

- **ドキュメント系**: `.md`, `.mdx`, `.txt`, `.rst`, `.asciidoc`, `.org`
- **設定・データ系**: `.json`, `.yaml`, `.yml`, `.toml`, `.ini`, `.cfg`, `.conf`, `.xml`, `.csv`
- **プログラミング言語**: `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.java`, `.cpp`, `.c`, `.h`, `.go`, `.rs`, `.rb`, `.php` など
- **スクリプト**: `.sh`, `.bash`, `.zsh`, `.ps1`, `.bat`
- **Web系**: `.html`, `.css`, `.scss`, `.vue`, `.svelte`
- **その他**: `.sql`, `.graphql`, `.proto`, `.ipynb`, `.dockerfile`, `.gitignore` など

例 （docs以下のフォルダ名はなんでもOKです。）
```
docs-mcp/
└── docs/
    ├── project1/
    │   ├── README.md
    │   ├── main.py
    │   └── config.yaml
    ├── project2/
    │   ├── index.js
    │   ├── styles.css
    │   └── package.json
    └── project3/
        ├── api.graphql
        └── docker-compose.yml
```

### 3. メタデータを生成（推奨）

```bash
uv run python scripts/generate_metadata.py
```

これにより以下のファイルが生成されます：
- `docs_metadata.json` - 各ドキュメントの1行説明
- `docs_embeddings.json` - セマンティック検索用のベクトルデータ

**注意**: このステップをスキップした場合：
- `list_docs`コマンドはファイルパスのみを表示します（説明文なし）
- `semantic_search`コマンドは使用できません

新しいドキュメントを追加した場合も同じコマンドを実行してください。

## MCPの設定json例

### 基本設定（すべてのドキュメントを読み込む）

```json
{
    "mcpServers": {
        "docs-mcp": {
            "command": "uv",
            "args": [
                "run",
                "--directory",
                "{path/to}/docs-mcp/src",
                "docs_mcp.py"
            ],
            "env": {
                "OPENAI_API_KEY": "your-openai-api-key"
            }
        }
    }
}
```

### フォルダを指定して読み込む

環境変数`DOCS_FOLDERS`を使用して、特定のフォルダのみを読み込むことができます：

```json
{
    "mcpServers": {
        "docs-mcp-project1": {
            "command": "uv",
            "args": [
                "run",
                "--directory",
                "{path/to}/docs-mcp/src",
                "docs_mcp.py"
            ],
            "env": {
                "OPENAI_API_KEY": "your-openai-api-key",
                "DOCS_FOLDERS": "docs1,docs3"  // docs1とdocs3のみを読み込む
            }
        },
        "docs-mcp-project2": {
            "command": "uv",
            "args": [
                "run",
                "--directory",
                "{path/to}/docs-mcp/src",
                "docs_mcp.py"
            ],
            "env": {
                "OPENAI_API_KEY": "your-openai-api-key",
                "DOCS_FOLDERS": "docs2"  // docs2のみを読み込む
            }
        }
    }
}
```

複数のプロジェクトを管理する場合、異なるサーバー名で複数の設定を作成できます。

### カスタムファイル拡張子の設定

デフォルトで多くのファイル形式に対応していますが、特定の拡張子のみを対象にしたい場合は、環境変数`DOCS_FILE_EXTENSIONS`で指定できます：

```json
{
    "mcpServers": {
        "docs-mcp-custom": {
            "command": "uv",
            "args": [
                "run",
                "--directory",
                "{path/to}/docs-mcp/src",
                "docs_mcp.py"
            ],
            "env": {
                "OPENAI_API_KEY": "your-openai-api-key",
                "DOCS_FILE_EXTENSIONS": ".md,.mdx,.py,.js"  // 特定の拡張子のみ
            }
        }
    }
}
```

拡張子はカンマ区切りで指定し、ドット（.）は省略可能です。この設定は`generate_metadata.py`スクリプトでも同様に機能します。

## テスト

テストを実行するには：

```bash
uv run pytest tests/
```

## スクリプト

### URLからドキュメントをインポート

WebサイトのドキュメントをMarkdown形式で高速にインポートできます。並列ダウンロード機能により、大量のページも効率的に取得可能です。

```bash
uv run python scripts/url_import.py https://example.com/docs
```

**主な特徴:**
- 🚀 並列ダウンロード（デフォルト10並列）で高速化
- 📊 プログレスバーでダウンロード・保存状況を可視化
- 🌏 日本語URLを適切にデコードしてファイル名に変換
- 🌲 URLのパス構造を維持したディレクトリツリーで保存

**オプション:**
- `--output-dir`, `-o`: 出力先ディレクトリ（デフォルト: ドメイン名）
- `--depth`, `-d`: クロールの深さ（デフォルト: 2）
- `--include-pattern`, `-i`: 含めるURLパターン（正規表現、複数指定可）
- `--exclude-pattern`, `-e`: 除外するURLパターン（正規表現、複数指定可）
- `--concurrent`, `-c`: 同時ダウンロード数（デフォルト: 10）
- `--timeout`: タイムアウト（秒、デフォルト: 30）
- `--rate-limit`: レート制限（秒、デフォルト: 0.1）

**使用例:**

```bash
# 基本的な使用
uv run python scripts/url_import.py https://mcp-jp.apidog.io/

# 特定のパスのみを深さ3でインポート
uv run python scripts/url_import.py https://docs.example.com \
    --depth 3 \
    --include-pattern "/api/.*" \
    --exclude-pattern ".*/deprecated/.*"

# 同時接続数を増やして高速化（サーバーに優しく）
uv run python scripts/url_import.py https://docs.example.com \
    --concurrent 20 \
    --rate-limit 0.05
```

インポート後は`generate_metadata.py`を実行してメタデータを更新してください。

### GitHubリポジトリからインポート

Gitのsparse-checkoutを使用して、GitHubリポジトリの特定フォルダをローカルに取得できます。

```bash
uv run python scripts/github_import.py https://github.com/owner/repo/tree/branch/path
```

**主な特徴:**
- 📁 指定したフォルダのみを効率的に取得（sparse-checkout使用）
- 🚀 Gitの機能を使った高速ダウンロード
- 🔒 APIレート制限なし
- 📦 最小限のデータ転送（shallow clone & blob filter）

**オプション:**
- `--output-dir`, `-o`: 出力先ディレクトリ（デフォルト: リポジトリ名）

**使用例:**

```bash
# 基本的な使用（特定フォルダを取得）
uv run python scripts/github_import.py https://github.com/modelcontextprotocol/modelcontextprotocol/tree/main/docs

# リポジトリ全体を取得
uv run python scripts/github_import.py https://github.com/owner/repo

# 別のブランチから取得
uv run python scripts/github_import.py https://github.com/owner/repo/tree/develop/src

# カスタム出力ディレクトリを指定
uv run python scripts/github_import.py https://github.com/owner/repo/tree/main/docs \
    --output-dir my-docs
```

インポート後は`generate_metadata.py`を実行してメタデータを更新してください。

## 利用可能なMCPツール

### list_docs
すべてのドキュメントの一覧を取得
- メタデータ生成済み: `ファイルパス - 説明文`の形式で表示
- メタデータ未生成: `ファイルパス`のみ表示

### get_doc
指定したドキュメントの全内容を取得
- 引数: `path` - ドキュメントのファイルパス

### grep_docs
正規表現でドキュメント内を検索
- 引数: `pattern` - 検索パターン、`ignore_case` - 大文字小文字を無視（デフォルト: true）

### semantic_search
意味的に関連する内容を検索
- 引数: `query` - 検索クエリ、`limit` - 結果数（デフォルト: 5）
- **注意**: `generate_metadata.py`を実行していない場合は使用できません
