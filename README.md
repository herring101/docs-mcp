# docs-mcp

[![Test](https://github.com/herring101/docs-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/herring101/docs-mcp/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

ユーザーが設定したドキュメントを効率的に検索・参照できるMCPサーバーです。

## 主な機能

- 📄 **ドキュメント一覧表示** - すべてのドキュメントとその説明を一覧表示
- 🔍 **grep検索** - 正規表現を使った高速な全文検索
- 🧠 **セマンティック検索** - OpenAI Embeddingsを使った意味的な類似検索（要設定）
- 📝 **ドキュメント取得** - 指定したドキュメントの全内容を取得

## 使い方は2種類

### 🚀 方法1: シンプルに使う（セマンティック検索なし）

```bash
# 1. プロジェクトを作成してドキュメントを配置
mkdir my-project
cd my-project
mkdir docs
# docs/にドキュメントを配置

# 2. Claude Desktopの設定に追加
```

Claude Desktop設定（`claude_desktop_config.json`）:
```json
{
  "mcpServers": {
    "docs": {
      "command": "uvx",
      "args": ["docs-mcp"],
      "env": {
        "DOCS_BASE_DIR": "/path/to/my-project"
      }
    }
  }
}
```

これだけで使えます！ただし、セマンティック検索は利用できません。

### 🎯 方法2: フル機能で使う（セマンティック検索あり）

```bash
# 1. インストール
pip install docs-mcp

# 2. プロジェクトを作成
mkdir my-project
cd my-project
mkdir docs

# 3. ドキュメントをインポート（オプション）
docs-mcp-import-url https://docs.example.com
# または
docs-mcp-import-github https://github.com/owner/repo/tree/main/docs

# 4. メタデータを生成（セマンティック検索用）
export OPENAI_API_KEY="your-key"
docs-mcp-generate-metadata

# 5. Claude Desktopの設定は方法1と同じ
```

## 利用可能なツール

### 基本ツール（方法1でも利用可能）
- `list_docs` - ドキュメント一覧表示
- `get_doc` - ドキュメント内容取得  
- `grep_docs` - 正規表現検索

### 追加ツール（方法2で利用可能）
- `semantic_search` - 意味的な類似検索（要メタデータ生成）

### コマンドラインツール（方法2で利用可能）
- `docs-mcp-import-url` - Webサイトからドキュメントをインポート
- `docs-mcp-import-github` - GitHubリポジトリからインポート
- `docs-mcp-generate-metadata` - 検索用メタデータを生成

## 必要な環境

- Python 3.12以上（サーバー実行用）
- OpenAI APIキー（セマンティック検索を使用する場合のみ）

## 詳細設定

### 環境変数

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| `OPENAI_API_KEY` | OpenAI APIキー（セマンティック検索用） | なし |
| `DOCS_BASE_DIR` | ドキュメントプロジェクトのルート | 現在のディレクトリ |
| `DOCS_FOLDERS` | 読み込むフォルダ（カンマ区切り） | `docs/`内の全フォルダ |
| `DOCS_FILE_EXTENSIONS` | 対象ファイル拡張子 | デフォルトの拡張子リスト |

### サポートされるファイル形式

<details>
<summary>クリックして展開</summary>

- **ドキュメント**: `.md`, `.mdx`, `.txt`, `.rst`, `.asciidoc`, `.org`
- **設定**: `.json`, `.yaml`, `.yml`, `.toml`, `.ini`, `.cfg`, `.conf`, `.xml`, `.csv`
- **コード**: `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.java`, `.cpp`, `.c`, `.h`, `.go`, `.rs`, `.rb`, `.php`
- **スクリプト**: `.sh`, `.bash`, `.zsh`, `.ps1`, `.bat`
- **Web**: `.html`, `.css`, `.scss`, `.vue`, `.svelte`
- **その他**: `.sql`, `.graphql`, `.proto`, `.ipynb`, `.dockerfile`, `.gitignore`

</details>

### ディレクトリ構造の例

```
my-project/
└── docs/
    ├── api/
    │   └── reference.md
    ├── guides/
    │   └── quickstart.md
    └── examples/
        └── sample.py
```
## 開発者向け情報

### ソースからの開発

```bash
git clone https://github.com/herring101/docs-mcp.git
cd docs-mcp
uv sync

# テスト
uv run pytest tests/

# ビルド
uv build
```

### コマンドラインツールの詳細

<details>
<summary>クリックして展開</summary>

#### docs-mcp-import-url

Webサイトからドキュメントをインポート

```bash
docs-mcp-import-url https://example.com/docs --output-dir docs/imported
```

オプション:
- `--output-dir`, `-o`: 出力ディレクトリ
- `--depth`, `-d`: クロール深度
- `--include-pattern`, `-i`: 含めるURLパターン
- `--exclude-pattern`, `-e`: 除外するURLパターン
- `--concurrent`, `-c`: 同時ダウンロード数

#### docs-mcp-import-github

GitHubリポジトリからインポート

```bash
docs-mcp-import-github https://github.com/owner/repo/tree/main/docs
```

#### docs-mcp-generate-metadata

セマンティック検索用のメタデータを生成

```bash
export OPENAI_API_KEY="your-key"
docs-mcp-generate-metadata
```

</details>

## セキュリティ

- APIキーは環境変数で管理
- `DOCS_FOLDERS`と`DOCS_FILE_EXTENSIONS`でアクセスを制限
- 外部ネットワークアクセスはOpenAI APIのみ

## トラブルシューティング

<details>
<summary>よくある問題</summary>

### Claude Desktopに表示されない
- 設定ファイルの構文を確認
- `DOCS_BASE_DIR`が正しいパスを指しているか確認
- Claude Desktopを再起動

### セマンティック検索が動作しない
- `OPENAI_API_KEY`が設定されているか確認
- `docs-mcp-generate-metadata`を実行したか確認

### インポートが失敗する  
- URL/GitHubリポジトリがアクセス可能か確認
- ネットワーク接続を確認

</details>

## ライセンス

MIT License - [LICENSE](LICENSE)

## コントリビューション

[CONTRIBUTING.md](CONTRIBUTING.md)を参照してください。
