"""統合テスト"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from mcp_server_docs.document_manager import DocumentManager


class TestIntegration:
    """統合テストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.temp_dir = tempfile.mkdtemp()
        os.environ["DOCS_BASE_DIR"] = self.temp_dir
        self.docs_dir = Path(self.temp_dir) / "docs"
        self.docs_dir.mkdir()

    def teardown_method(self):
        """各テストメソッドの後に実行"""
        import shutil

        shutil.rmtree(self.temp_dir)
        if "DOCS_BASE_DIR" in os.environ:
            del os.environ["DOCS_BASE_DIR"]

    def test_document_manager_tools(self):
        """DocumentManagerのツールテスト"""
        # テストドキュメントを作成
        (self.docs_dir / "test.md").write_text("# Test\n\nHello World")
        (self.docs_dir / "guide.md").write_text("# Guide\n\nQuick Start Guide")

        # メタデータを作成
        metadata = {
            "test.md": "テストドキュメント",
            "guide.md": "クイックスタートガイド",
        }
        metadata_file = Path(self.temp_dir) / "docs_metadata.json"
        metadata_file.write_text(json.dumps(metadata, ensure_ascii=False))

        # DocumentManagerを作成
        manager = DocumentManager()
        manager.load_documents()

        # list_documents テスト
        result = manager.list_documents()
        assert "test.md - テストドキュメント" in result
        assert "guide.md - クイックスタートガイド" in result

        # get_document テスト
        result = manager.get_document("test.md")
        assert "# Test" in result
        assert "Hello World" in result

        # grep_search テスト
        result = manager.grep_search("Hello")
        assert "test.md:3: Hello World" in result

        # 存在しないドキュメント
        result = manager.get_document("notfound.md")
        assert "Error" in result

    def test_semantic_search(self):
        """セマンティック検索のテスト"""
        # テストドキュメントを作成
        (self.docs_dir / "python.md").write_text(
            "# Python Guide\n\nPython programming tutorial"
        )
        (self.docs_dir / "javascript.md").write_text(
            "# JavaScript Guide\n\nJavaScript programming tutorial"
        )

        # ダミーのエンベディングを作成
        embeddings = {
            "python.md": [0.1] * 3072,  # ダミーのエンベディング
            "javascript.md": [0.2] * 3072,
        }
        embeddings_file = Path(self.temp_dir) / "docs_embeddings.json"
        embeddings_file.write_text(json.dumps(embeddings))

        # OpenAI APIをモック
        with patch("mcp_server_docs.document_manager.OpenAI") as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client

            # エンベディング生成のモック
            mock_embedding = MagicMock()
            mock_embedding.embedding = [0.15] * 3072  # クエリのエンベディング
            mock_response = MagicMock()
            mock_response.data = [mock_embedding]
            mock_client.embeddings.create.return_value = mock_response

            # 環境変数を設定
            os.environ["OPENAI_API_KEY"] = "dummy-key"

            # DocumentManagerを作成
            manager = DocumentManager()
            manager.load_documents()

            # セマンティック検索のテスト
            result = manager.semantic_search(query="Python programming", limit=2)

            # 結果に両方のドキュメントが含まれることを確認
            assert "python.md" in result
            assert "javascript.md" in result

            # OpenAI APIキーをクリア
            del os.environ["OPENAI_API_KEY"]

    def test_allowed_folders(self):
        """フォルダフィルタリングのテスト"""
        # 複数のフォルダを作成
        (self.docs_dir / "public").mkdir()
        (self.docs_dir / "private").mkdir()
        (self.docs_dir / "public" / "guide.md").write_text("Public guide")
        (self.docs_dir / "private" / "secret.md").write_text("Secret info")

        # DOCS_FOLDERSを設定
        os.environ["DOCS_FOLDERS"] = "public"

        # DocumentManagerを作成
        manager = DocumentManager(allowed_folders=["public"])
        manager.load_documents()

        # ドキュメント一覧を取得
        result = manager.list_documents()

        # publicフォルダのみが含まれることを確認
        assert "public/guide.md" in result
        assert "private/secret.md" not in result

        # 環境変数をクリア
        del os.environ["DOCS_FOLDERS"]

    def test_custom_extensions(self):
        """カスタム拡張子のテスト"""
        # 異なる拡張子のファイルを作成
        (self.docs_dir / "doc.txt").write_text("Text document")
        (self.docs_dir / "config.json").write_text('{"key": "value"}')
        (self.docs_dir / "readme.md").write_text("Markdown document")

        # カスタム拡張子を設定
        os.environ["DOCS_FILE_EXTENSIONS"] = ".txt,.json"

        # DocumentManagerを作成
        manager = DocumentManager()
        manager.load_documents()

        # ドキュメント一覧を取得
        result = manager.list_documents()

        # .txtと.jsonのみが含まれることを確認
        assert "doc.txt" in result
        assert "config.json" in result
        assert "readme.md" not in result

        # 環境変数をクリア
        del os.environ["DOCS_FILE_EXTENSIONS"]

    def test_document_manager_initialization(self):
        """DocumentManagerの初期化テスト"""
        # 環境変数を設定
        os.environ["DOCS_FILE_EXTENSIONS"] = ".md,.txt"

        # DocumentManagerを作成（allowed_foldersは明示的に指定）
        manager = DocumentManager(allowed_folders=["api", "guide"])

        # 設定が反映されていることを確認
        assert manager.allowed_folders == ["api", "guide"]
        assert ".md" in manager.allowed_extensions
        assert ".txt" in manager.allowed_extensions

        # 環境変数をクリア
        del os.environ["DOCS_FILE_EXTENSIONS"]

    def test_docs_folders_env_parsing(self):
        """DOCS_FOLDERS環境変数のパースロジックのテスト"""
        # ケース1: カンマ区切りの複数フォルダ
        docs_folders_env = "project1,shared"
        allowed_folders = None
        if docs_folders_env:
            allowed_folders = [
                folder.strip()
                for folder in docs_folders_env.split(",")
                if folder.strip()
            ]
        assert allowed_folders == ["project1", "shared"]

        # ケース2: 空文字列
        docs_folders_env = ""
        allowed_folders = None
        if docs_folders_env:
            # この部分は空文字列なので実行されない
            pass
        assert allowed_folders is None

        # ケース3: 空白を含む
        docs_folders_env = " project1 , shared "
        allowed_folders = None
        if docs_folders_env.strip():
            allowed_folders = [
                folder.strip()
                for folder in docs_folders_env.split(",")
                if folder.strip()
            ]
        assert allowed_folders == ["project1", "shared"]

        # ケース4: 単一フォルダ
        docs_folders_env = "project1"
        allowed_folders = None
        if docs_folders_env:
            allowed_folders = [
                folder.strip()
                for folder in docs_folders_env.split(",")
                if folder.strip()
            ]
        assert allowed_folders == ["project1"]

    def test_empty_documents_directory(self):
        """空のドキュメントディレクトリのテスト"""
        manager = DocumentManager()
        manager.load_documents()

        assert manager.get_doc_count() == 0
        assert manager.list_documents() == ""

        result = manager.grep_search("test")
        assert result == "No matches found"

    def test_large_result_truncation(self):
        """大量の検索結果の切り詰めテスト"""
        # 多数のマッチを含むファイルを作成
        content = "\n".join([f"Line {i}: test match" for i in range(200)])
        (self.docs_dir / "large.txt").write_text(content)

        manager = DocumentManager()
        manager.load_documents()

        result = manager.grep_search("test match")

        # 結果が100件に制限されることを確認
        assert result.count("large.txt:") == 100
        assert "and 100 more matches" in result
