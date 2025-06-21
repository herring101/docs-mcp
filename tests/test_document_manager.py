"""DocumentManagerのテスト"""

import os
import shutil
import tempfile
from pathlib import Path

from mcp_server_docs.document_manager import DocumentManager


class TestDocumentManager:
    """DocumentManagerのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.temp_dir = tempfile.mkdtemp()
        # DOCS_BASE_DIRを設定
        os.environ["DOCS_BASE_DIR"] = self.temp_dir
        self.docs_dir = Path(self.temp_dir) / "docs"
        self.docs_dir.mkdir()

    def teardown_method(self):
        """各テストメソッドの後に実行"""
        shutil.rmtree(self.temp_dir)
        # 環境変数をクリア
        if "DOCS_BASE_DIR" in os.environ:
            del os.environ["DOCS_BASE_DIR"]

    def test_init(self):
        """初期化のテスト"""
        manager = DocumentManager()
        assert manager.base_dir == Path(self.temp_dir)
        assert manager.docs_dir == self.docs_dir
        assert isinstance(manager.allowed_extensions, list)
        assert ".md" in manager.allowed_extensions

    def test_load_documents_empty(self):
        """空のディレクトリでのドキュメント読み込みテスト"""
        manager = DocumentManager()
        manager.load_documents()
        assert len(manager.docs_content) == 0

    def test_load_documents_with_files(self):
        """ファイルがある場合のドキュメント読み込みテスト"""
        # テストファイルを作成
        test_file = self.docs_dir / "test.md"
        test_file.write_text("# Test Document\n\nThis is a test.")

        manager = DocumentManager()
        manager.load_documents()

        assert len(manager.docs_content) == 1
        assert "test.md" in manager.docs_content
        assert "# Test Document" in manager.docs_content["test.md"]

    def test_load_documents_with_subdirectories(self):
        """サブディレクトリのファイル読み込みテスト"""
        # サブディレクトリとファイルを作成
        sub_dir = self.docs_dir / "api"
        sub_dir.mkdir()
        test_file = sub_dir / "reference.md"
        test_file.write_text("# API Reference")

        manager = DocumentManager()
        manager.load_documents()

        assert len(manager.docs_content) == 1
        assert "api/reference.md" in manager.docs_content

    def test_allowed_folders(self):
        """特定フォルダのみの読み込みテスト"""
        # 複数のフォルダを作成
        api_dir = self.docs_dir / "api"
        api_dir.mkdir()
        guide_dir = self.docs_dir / "guide"
        guide_dir.mkdir()

        (api_dir / "test.md").write_text("API test")
        (guide_dir / "test.md").write_text("Guide test")

        # apiフォルダのみを許可
        manager = DocumentManager(allowed_folders=["api"])
        manager.load_documents()

        assert len(manager.docs_content) == 1
        assert "api/test.md" in manager.docs_content
        assert "guide/test.md" not in manager.docs_content

    def test_list_documents(self):
        """ドキュメント一覧表示のテスト"""
        test_file = self.docs_dir / "test.md"
        test_file.write_text("Test content")

        manager = DocumentManager()
        manager.load_documents()

        doc_list = manager.list_documents()
        assert "test.md" in doc_list

    def test_get_document(self):
        """ドキュメント取得のテスト"""
        test_content = "# Test\n\nThis is test content."
        test_file = self.docs_dir / "test.md"
        test_file.write_text(test_content)

        manager = DocumentManager()
        manager.load_documents()

        content = manager.get_document("test.md")
        assert content == test_content

        # 存在しないファイル
        error = manager.get_document("notfound.md")
        assert "Error: Document not found" in error

    def test_grep_search(self):
        """grep検索のテスト"""
        test_file = self.docs_dir / "test.md"
        test_file.write_text("Line 1: Hello\nLine 2: World\nLine 3: Hello World")

        manager = DocumentManager()
        manager.load_documents()

        # 大文字小文字を無視した検索
        results = manager.grep_search("hello", ignore_case=True)
        assert "test.md:1: Line 1: Hello" in results
        assert "test.md:3: Line 3: Hello World" in results

        # 大文字小文字を区別した検索
        results = manager.grep_search("hello", ignore_case=False)
        assert "test.md:1:" not in results  # "Hello"は含まれない

        # 正規表現検索
        results = manager.grep_search(r"Line \d+:")
        assert results.count("test.md:") == 3

    def test_custom_extensions(self):
        """カスタム拡張子のテスト"""
        # 環境変数で拡張子を設定
        os.environ["DOCS_FILE_EXTENSIONS"] = ".txt,.json"

        # ファイルを作成
        (self.docs_dir / "test.txt").write_text("Text file")
        (self.docs_dir / "test.json").write_text('{"key": "value"}')
        (self.docs_dir / "test.md").write_text("Markdown file")

        manager = DocumentManager()
        manager.load_documents()

        assert "test.txt" in manager.docs_content
        assert "test.json" in manager.docs_content
        assert "test.md" not in manager.docs_content  # .mdは含まれない

        # 環境変数をクリア
        del os.environ["DOCS_FILE_EXTENSIONS"]

    def test_metadata_loading(self):
        """メタデータ読み込みのテスト"""
        # メタデータファイルを作成
        metadata_file = Path(self.temp_dir) / "docs_metadata.json"
        metadata_file.write_text('{"test.md": "テストドキュメントの説明"}')

        test_file = self.docs_dir / "test.md"
        test_file.write_text("Test content")

        manager = DocumentManager()
        manager.load_documents()

        doc_list = manager.list_documents()
        assert "test.md - テストドキュメントの説明" in doc_list

    def test_get_doc_count(self):
        """ドキュメント数取得のテスト"""
        # 複数のファイルを作成
        for i in range(3):
            (self.docs_dir / f"test{i}.md").write_text(f"Test {i}")

        manager = DocumentManager()
        manager.load_documents()

        assert manager.get_doc_count() == 3
