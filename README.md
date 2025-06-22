# docs-mcp

[![Test](https://github.com/herring101/docs-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/herring101/docs-mcp/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

ユーザーが設定したドキュメントを効率的に検索・参照できるMCPサーバーです。

## 前提条件

docs-mcpを使用するには[uv](https://docs.astral.sh/uv/)が必要です。uvはPythonパッケージとプロジェクト管理のための高速なツールです。

### uvのインストール

<details>
<summary>お使いのOSに合わせて選択してください</summary>

#### macOS/Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Windows
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### Homebrew (macOS)
```bash
brew install uv
```

#### pipでのインストール
```bash
pip install uv
```

</details>

詳細は[uvのインストールガイド](https://docs.astral.sh/uv/getting-started/installation/)を参照してください。

## 主な機能

- 📄 **ドキュメント一覧表示** - すべてのドキュメントとその説明を一覧表示
- 🔍 **grep検索** - 正規表現を使った高速な全文検索
- 🧠 **セマンティック検索** - OpenAI Embeddingsを使った意味的な類似検索（要設定）
- 📝 **ドキュメント取得** - 指定したドキュメントの全内容を取得

## クイックスタート

### 🚀 最もシンプルな使い方

既存のドキュメントがあるプロジェクトですぐに使えます：

```bash
# ドキュメント管理用フォルダを作成
mkdir -p my-docs/docs
# ドキュメントファイルをdocs/に配置
```

Claude Desktopの設定（`claude_desktop_config.json`）に追加：
```json
{
  "mcpServers": {
    "docs": {
      "command": "uvx",
      "args": ["docs-mcp"],
      "env": {
        "DOCS_BASE_DIR": "/path/to/my-docs"
      }
    }
  }
}
```

**重要**: docs-mcpは常にプロジェクトフォルダ内の`docs/`ディレクトリを参照します。

## セットアップガイド

### 方法1: 既存のドキュメントで使う

手元にあるMarkdownやテキストファイルをすぐに検索可能にできます：

1. プロジェクトフォルダを作成
2. `docs/`ディレクトリにドキュメントを配置
3. Claude Desktopの設定を更新

✅ **メリット**: コマンドライン操作不要、すぐに使える  
❌ **デメリット**: インポートツールが使えない

### 方法2: インポートツールを活用する

GitHubやWebサイトからドキュメントを取り込む場合：

```bash
# ドキュメント管理プロジェクトをセットアップ
uv init my-docs
cd my-docs
uv add docs-mcp

# GitHubからドキュメントをインポート
uv run docs-mcp-import-github https://github.com/owner/repo

# 特定のディレクトリだけインポート
uv run docs-mcp-import-github https://github.com/owner/repo/tree/main/docs -o project-docs
```

✅ **メリット**: 外部ドキュメントを簡単に取り込める  
❌ **デメリット**: uvのセットアップが必要

## 高度な機能

### 🧠 セマンティック検索を有効にする

OpenAI Embeddingsを使った意味的な検索を追加できます：

```bash
# 1. OpenAI APIキーを設定
export OPENAI_API_KEY="sk-..."

# 2. メタデータを生成（プロジェクトディレクトリで実行）
uv run docs-mcp-generate-metadata
```

Claude Desktopの設定でAPIキーを追加：
```json
{
  "mcpServers": {
    "docs": {
      "command": "uvx",
      "args": ["docs-mcp"],
      "env": {
        "DOCS_BASE_DIR": "/path/to/my-docs",
        "OPENAI_API_KEY": "sk-..."  // セマンティック検索が有効になる
      }
    }
  }
}
```

### 詳細な設定オプション

```json
{
  "mcpServers": {
    "docs": {
      "command": "uvx",
      "args": ["docs-mcp"],
      "env": {
        "DOCS_BASE_DIR": "/path/to/my-docs",
        "OPENAI_API_KEY": "sk-...",
        "DOCS_FOLDERS": "api,guides,examples",  // 特定のフォルダのみ読み込み
        "DOCS_FILE_EXTENSIONS": ".md,.mdx,.txt,.py"  // 対象ファイル拡張子を制限
      }
    }
  }
}
```

## 利用可能なツール

### MCPツール（Claude内で使用）
- `list_docs` - ドキュメント一覧表示
- `get_doc` - ドキュメント内容取得  
- `grep_docs` - 正規表現検索
- `semantic_search` - 意味的な類似検索（要OpenAI APIキー）

### コマンドラインツール（ドキュメント管理用）
- `docs-mcp-import-url` - Webサイトからドキュメントをインポート
- `docs-mcp-import-github` - GitHubリポジトリからインポート
- `docs-mcp-generate-metadata` - セマンティック検索用メタデータを生成

## 必要な環境

- [uv](https://docs.astral.sh/uv/) - Python環境とパッケージ管理ツール（`uvx`コマンドで実行）
- Python 3.12以上（uvが自動的に管理）
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
my-docs/
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
docs-mcp-import-url https://example.com/docs --output-dir imported
```

オプション:
- `--output-dir`, `-o`: 出力ディレクトリ名（`docs/`配下に保存）
- `--depth`, `-d`: クロール深度
- `--include-pattern`, `-i`: 含めるURLパターン
- `--exclude-pattern`, `-e`: 除外するURLパターン
- `--concurrent`, `-c`: 同時ダウンロード数

#### docs-mcp-import-github

GitHubリポジトリからインポート。ブランチを指定しない場合はデフォルトブランチ（main/master等）を自動検出します。

```bash
# リポジトリ全体をインポート
docs-mcp-import-github https://github.com/owner/repo

# 特定のパスのみインポート（docs/importedに保存される）
docs-mcp-import-github https://github.com/owner/repo/tree/main/docs --output-dir imported

# masterブランチのリポジトリも自動検出
docs-mcp-import-github https://github.com/Cysharp/UniTask
```

オプション:
- `--output-dir`, `-o`: 出力ディレクトリ名（`docs/`配下に保存。デフォルト: リポジトリ名）

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
