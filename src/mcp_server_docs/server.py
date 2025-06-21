import os

from mcp.server.fastmcp import FastMCP

from .document_manager import DocumentManager

# FastMCP初期化
mcp = FastMCP("docs-mcp")

# 環境変数から読み込むフォルダを取得
docs_folders_env = os.getenv("DOCS_FOLDERS", "").strip()
allowed_folders = None
if docs_folders_env:
    # カンマ区切りでフォルダ名を分割し、空白を除去
    allowed_folders = [
        folder.strip() for folder in docs_folders_env.split(",") if folder.strip()
    ]
    print(f"Loading documents from folders: {', '.join(allowed_folders)}")
else:
    print("Loading all documents (no DOCS_FOLDERS specified)")

# ドキュメントマネージャー初期化
doc_manager = DocumentManager(allowed_folders=allowed_folders)


@mcp.tool()
async def list_docs() -> str:
    """所持しているドキュメントの一覧を取得"""
    return doc_manager.list_documents()


@mcp.tool()
async def get_doc(path: str) -> str:
    """指定したドキュメントの内容を取得

    Args:
        path: ドキュメントのファイルパス
    """
    return doc_manager.get_document(path)


@mcp.tool()
async def grep_docs(pattern: str, ignore_case: bool = True) -> str:
    """ドキュメント内をgrepで検索

    Args:
        pattern: 検索パターン（正規表現対応）
        ignore_case: 大文字小文字を無視するか（デフォルト: True）
    """
    return doc_manager.grep_search(pattern, ignore_case)


@mcp.tool()
async def semantic_search(query: str, limit: int = 5) -> str:
    """意味的に関連する内容を検索

    Args:
        query: 検索クエリ
        limit: 返す結果の最大数（デフォルト: 5）
    """
    return doc_manager.semantic_search(query, limit)


def main():
    """Entry point for the MCP server"""
    print("Loading documents...")
    doc_manager.load_documents()
    print(f"Loaded {doc_manager.get_doc_count()} documents")

    # MCPサーバーを起動
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
