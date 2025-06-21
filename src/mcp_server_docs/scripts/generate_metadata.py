#!/usr/bin/env python3
"""
メタデータとembeddings生成スクリプト（高速版）
docs/内のすべてのドキュメントに対して1行説明とembeddingsを生成します
"""

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from tqdm import tqdm

load_dotenv()

# デフォルトで対応するファイル拡張子（DocumentManagerと同じ）
DEFAULT_EXTENSIONS = [
    # ドキュメント系
    ".md",
    ".mdx",
    ".txt",
    ".rst",
    ".asciidoc",
    ".org",
    # データ・設定系
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".xml",
    ".csv",
    # プログラミング言語
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".cs",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".scala",
    ".r",
    ".m",
    # スクリプト・シェル
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".ps1",
    ".bat",
    ".cmd",
    # Web系
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".vue",
    ".svelte",
    ".astro",
    # 設定・ビルド系
    ".dockerfile",
    ".dockerignore",
    ".gitignore",
    ".env",
    ".env.example",
    ".editorconfig",
    ".prettierrc",
    ".eslintrc",
    ".babelrc",
    # その他
    ".sql",
    ".graphql",
    ".proto",
    ".ipynb",
]


class MetadataGenerator:
    def __init__(self, api_key: str, concurrent_requests: int = 10):
        self.client = AsyncOpenAI(api_key=api_key)
        self.concurrent_requests = concurrent_requests
        self.semaphore = asyncio.Semaphore(concurrent_requests)

    def get_context_from_path(self, doc_path: str) -> dict[str, str]:
        """ファイルパスからコンテキスト情報を抽出"""
        parts = doc_path.split("/")

        # プロジェクト/カテゴリを判定（docs/プレフィックスなし）
        if len(parts) >= 1:
            project = parts[0]  # mcp, uv, voice-api など

            # サブカテゴリを取得
            subcategory = ""
            if len(parts) > 2:
                subcategory = "/".join(parts[1:-1])
            elif len(parts) == 2:
                subcategory = "ルート"

            filename = parts[-1]

            # プロジェクトごとの説明
            project_descriptions = {
                "mcp": "Model Context Protocol",
                "uv": "Python パッケージマネージャー uv",
                "voice-api": "音声API",
            }

            return {
                "project": project_descriptions.get(project, project),
                "subcategory": subcategory,
                "filename": filename,
                "full_path": doc_path,
            }

        return {
            "project": "不明",
            "subcategory": "",
            "filename": doc_path.split("/")[-1],
            "full_path": doc_path,
        }

    async def generate_description(
        self, doc_path: str, content: str, all_paths: list[str]
    ) -> tuple[str, str]:
        """ドキュメントの1行説明を生成"""
        async with self.semaphore:
            try:
                # ファイルタイプに応じた説明
                if doc_path.endswith(".json"):
                    context = self.get_context_from_path(doc_path)
                    return (
                        doc_path,
                        f"{context['project']}の{context['subcategory']}セクションのJSONスキーマ定義",
                    )
                elif doc_path.endswith(".ts"):
                    context = self.get_context_from_path(doc_path)
                    return (
                        doc_path,
                        f"{context['project']}の{context['subcategory']}セクションのTypeScript型定義",
                    )
                elif doc_path.endswith((".yml", ".yaml")):
                    context = self.get_context_from_path(doc_path)
                    return (
                        doc_path,
                        f"{context['project']}の{context['subcategory']}セクションのYAML設定ファイル",
                    )

                # コンテキスト情報を取得
                context = self.get_context_from_path(doc_path)

                # 同じディレクトリ内の他のファイルを取得（構造理解のため）
                dir_path = "/".join(doc_path.split("/")[:-1])
                siblings = [
                    p for p in all_paths if p.startswith(dir_path) and p != doc_path
                ][:5]

                # 内容から説明を生成
                content_preview = content[:3000]

                response = await self.client.chat.completions.create(
                    model="gpt-4o-mini",  # より高速なモデルを使用
                    messages=[
                        {
                            "role": "system",
                            "content": """ドキュメントの内容とファイルパスから、そのドキュメントが全体の中でどのような役割を持つかを含めた、技術的に正確で簡潔な1行の日本語説明を生成してください。

以下の観点を考慮してください：
- どのプロジェクト/製品のドキュメントか
- どのセクション/カテゴリに属するか
- 何について説明しているか
- 誰向けの情報か（開発者、ユーザーなど）

説明は60文字程度で、全体の文脈における位置づけがわかるようにしてください。""",
                        },
                        {
                            "role": "user",
                            "content": f"""ファイルパス: {doc_path}
プロジェクト: {context["project"]}
カテゴリ: {context["subcategory"]}
ファイル名: {context["filename"]}

同じディレクトリの他のファイル:
{chr(10).join(siblings)}

内容の冒頭:
{content_preview}""",
                        },
                    ],
                    temperature=0.3,
                    max_tokens=150,
                )

                message_content = response.choices[0].message.content
                if message_content is None:
                    description = "ドキュメント"
                else:
                    description = message_content.strip().strip("\"'。.")
                return doc_path, description

            except Exception as e:
                print(f"\nError generating description for {doc_path}: {e}")
                return doc_path, "ドキュメント"

    async def generate_embedding(
        self, doc_path: str, content: str
    ) -> tuple[str, list[float] | None]:
        """テキストのembeddingを生成"""
        async with self.semaphore:
            try:
                # text-embedding-3-largeのトークン制限を考慮（約8192トークン≒日本語なら約10000文字）
                text = content[:10000].replace("\n", " ")
                response = await self.client.embeddings.create(
                    input=[text], model="text-embedding-3-large"
                )
                return doc_path, response.data[0].embedding

            except Exception as e:
                print(f"\nError generating embedding for {doc_path}: {e}")
                return doc_path, None

    async def process_files(
        self,
        files_data: list[tuple[str, str]],
        existing_metadata: dict[str, str],
        existing_embeddings: dict[str, list[float]],
    ) -> tuple[dict[str, str], dict[str, list[float]]]:
        """ファイルを並列処理"""
        metadata_tasks = []
        embedding_tasks = []

        # 全ファイルパスのリスト（構造理解のため）
        all_paths = [doc_path for doc_path, _ in files_data]

        # メタデータとembeddingのタスクを作成
        for doc_path, content in files_data:
            if doc_path not in existing_metadata:
                metadata_tasks.append(
                    self.generate_description(doc_path, content, all_paths)
                )

            if doc_path not in existing_embeddings and len(content.strip()) > 0:
                embedding_tasks.append(self.generate_embedding(doc_path, content))

        new_metadata = {}
        new_embeddings = {}

        # メタデータを並列生成
        if metadata_tasks:
            print(f"\nGenerating descriptions for {len(metadata_tasks)} files...")
            with tqdm(
                total=len(metadata_tasks), desc="Descriptions", unit="files"
            ) as pbar:
                for coro in asyncio.as_completed(metadata_tasks):
                    doc_path, description = await coro
                    new_metadata[doc_path] = description
                    pbar.update(1)
                    pbar.set_postfix_str(f"{doc_path}: {description[:50]}...")

        # Embeddingsを並列生成
        if embedding_tasks:
            print(f"\nGenerating embeddings for {len(embedding_tasks)} files...")
            with tqdm(
                total=len(embedding_tasks), desc="Embeddings", unit="files"
            ) as pbar:
                for coro in asyncio.as_completed(embedding_tasks):
                    doc_path, embedding = await coro
                    if embedding:
                        new_embeddings[doc_path] = embedding
                        pbar.update(1)
                        pbar.set_postfix_str(f"{doc_path}")

        return new_metadata, new_embeddings


def read_file_safe(file_path: Path) -> str | None:
    """ファイルを安全に読み込む"""
    try:
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None


async def main():
    # OpenAI APIキーチェック
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return

    # パス設定
    # DOCS_BASE_DIRが設定されていればそれを使用、なければ現在のディレクトリ
    docs_base_dir = os.getenv("DOCS_BASE_DIR", os.getcwd())
    base_dir = Path(docs_base_dir)
    docs_dir = base_dir / "docs"
    metadata_file = base_dir / "docs_metadata.json"
    embeddings_file = base_dir / "docs_embeddings.json"

    # 既存のデータを読み込み
    metadata = {}
    embeddings = {}

    if metadata_file.exists():
        with open(metadata_file, encoding="utf-8") as f:
            metadata = json.load(f)
        print(f"Loaded existing metadata: {len(metadata)} entries")

    if embeddings_file.exists():
        with open(embeddings_file, encoding="utf-8") as f:
            embeddings = json.load(f)
        print(f"Loaded existing embeddings: {len(embeddings)} entries")

    # ファイル拡張子の設定を取得
    extensions_env = os.getenv("DOCS_FILE_EXTENSIONS")
    if extensions_env:
        # 環境変数が設定されている場合は、それを使用（カンマ区切り）
        allowed_extensions = [
            ext.strip() for ext in extensions_env.split(",") if ext.strip()
        ]
        # ドットがない場合は追加
        allowed_extensions = [
            ext if ext.startswith(".") else f".{ext}" for ext in allowed_extensions
        ]
        print(f"Using custom file extensions: {', '.join(allowed_extensions)}")
    else:
        # デフォルトの拡張子を使用
        allowed_extensions = DEFAULT_EXTENSIONS

    # docs内のすべてのテキストファイルを収集
    print("\nScanning for documents...")
    files_data = []

    for file_path in docs_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in allowed_extensions:
            # docs/プレフィックスを除去
            doc_path = str(file_path.relative_to(docs_dir)).replace("\\", "/")

            # ファイルを読み込み（並列読み込み用）
            content = read_file_safe(file_path)
            if content:
                files_data.append((doc_path, content))

    print(f"Found {len(files_data)} documents")

    # 現在存在するファイルのパスセット
    existing_files = {doc_path for doc_path, _ in files_data}

    # 削除されたファイルをチェック
    deleted_from_metadata = [path for path in metadata if path not in existing_files]
    deleted_from_embeddings = [
        path for path in embeddings if path not in existing_files
    ]

    # 削除されたファイルの情報を削除
    if deleted_from_metadata or deleted_from_embeddings:
        print("\nCleaning up deleted files...")
        if deleted_from_metadata:
            print(f"- Removing {len(deleted_from_metadata)} entries from metadata")
            for path in deleted_from_metadata:
                del metadata[path]
        if deleted_from_embeddings:
            print(f"- Removing {len(deleted_from_embeddings)} entries from embeddings")
            for path in deleted_from_embeddings:
                del embeddings[path]

    # 処理が必要なファイルをチェック
    need_metadata = sum(1 for doc_path, _ in files_data if doc_path not in metadata)
    need_embeddings = sum(
        1
        for doc_path, content in files_data
        if doc_path not in embeddings and len(content.strip()) > 0
    )

    if (
        need_metadata == 0
        and need_embeddings == 0
        and not deleted_from_metadata
        and not deleted_from_embeddings
    ):
        print("\nAll files are up to date. No processing needed.")
        return

    print("\nNeed to process:")
    print(f"- Descriptions: {need_metadata} files")
    print(f"- Embeddings: {need_embeddings} files")

    # MetadataGeneratorを初期化
    generator = MetadataGenerator(api_key, concurrent_requests=10)

    # 並列処理
    new_metadata, new_embeddings = await generator.process_files(
        files_data, metadata, embeddings
    )

    # 新しいデータをマージ
    metadata_updated = len(new_metadata) > 0
    embeddings_updated = len(new_embeddings) > 0

    if metadata_updated:
        metadata.update(new_metadata)

    if embeddings_updated:
        embeddings.update(new_embeddings)

    # メタデータを保存（ソート済み）
    if metadata_updated or deleted_from_metadata:
        with open(metadata_file, "w", encoding="utf-8") as f:
            sorted_metadata = dict(sorted(metadata.items()))
            json.dump(sorted_metadata, f, ensure_ascii=False, indent=2)
        print(f"\nMetadata saved to {metadata_file}")

    # Embeddingsを保存（ソート済み）
    if embeddings_updated or deleted_from_embeddings:
        with open(embeddings_file, "w", encoding="utf-8") as f:
            sorted_embeddings = dict(sorted(embeddings.items()))
            json.dump(sorted_embeddings, f, ensure_ascii=False)
        print(f"Embeddings saved to {embeddings_file}")

    print("\nSummary:")
    print(f"- Total documents: {len(metadata)}")
    print(f"- Total embeddings: {len(embeddings)}")
    print(f"- New descriptions: {len(new_metadata)}")
    print(f"- New embeddings: {len(new_embeddings)}")
    if deleted_from_metadata:
        print(f"- Removed metadata: {len(deleted_from_metadata)}")
    if deleted_from_embeddings:
        print(f"- Removed embeddings: {len(deleted_from_embeddings)}")


def cli():
    """CLI entry point for PyPI installation."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
