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

`docs/`ディレクトリにドキュメントを配置します。すべてのテキストファイルが対象になります。

例 （docs以下のフォルダ名はなんでもOKです。）
```
docs-mcp/
└── docs/
    ├── docs1/
    │   ├── architecture.mdx
    │   └── tools.mdx
    ├── docs2/
    │   ├── schema.json
    │   └── schema.ts
    └── docs3/
        └── building-mcp-with-llms.mdx
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

## テスト

テストを実行するには：

```bash
uv run pytest tests/
```

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
