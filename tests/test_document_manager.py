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

    def test_pagination_basic(self):
        """ページネーション基本機能のテスト（文字数ベース）"""
        # 長いテストファイルを作成（約600文字）
        content = "\n".join([f"Line {i+1}: This is test content with some additional text to increase character count" for i in range(10)])
        test_file = self.docs_dir / "long_test.md"
        test_file.write_text(content)

        # デフォルトの文字数を調整（300文字/ページ）
        os.environ["DOCS_MAX_CHARS_PER_PAGE"] = "300"
        
        manager = DocumentManager()
        manager.load_documents()

        # 1ページ目
        page1 = manager.get_document("long_test.md", page=1)
        assert "Page 1/" in page1
        assert "chars 1-" in page1
        assert "Line 1:" in page1

        # 2ページ目
        page2 = manager.get_document("long_test.md", page=2)
        assert "Page 2/" in page2
        assert "chars " in page2
        assert "Line " in page2
        
        # 環境変数をクリア
        del os.environ["DOCS_MAX_CHARS_PER_PAGE"]

    def test_pagination_errors(self):
        """ページネーションエラーハンドリングのテスト"""
        content = "\n".join([f"Line {i+1}" for i in range(5)])
        test_file = self.docs_dir / "test.md"
        test_file.write_text(content)

        # 10文字/ページに設定
        os.environ["DOCS_MAX_CHARS_PER_PAGE"] = "10"
        
        manager = DocumentManager()
        manager.load_documents()

        # ページ番号が1未満
        result = manager.get_document("test.md", page=0)
        assert "Error: Page number must be 1 or greater" in result

        # ページ番号が総ページ数を超過
        result = manager.get_document("test.md", page=50)
        assert "Error: Page 50 not found" in result
        assert "Total pages:" in result
        
        # 環境変数をクリア
        del os.environ["DOCS_MAX_CHARS_PER_PAGE"]

    def test_large_file_warning(self):
        """大きなファイル警告機能のテスト（文字数ベース）"""
        # 大きなファイルを作成（約20000文字）
        content = "\n".join([f"Line {i+1}: This is content with sufficient characters to test large file threshold functionality" for i in range(200)])
        test_file = self.docs_dir / "large_test.md"
        test_file.write_text(content)

        manager = DocumentManager()
        manager.load_documents()

        # ページ指定なしで取得（自動的に1ページ目が表示される）
        result = manager.get_document("large_test.md")
        assert "📄 Document: large_test.md" in result
        assert "📖 Page 1/" in result
        assert "chars 1-" in result
        assert "⚠️  Large document auto-paginated" in result
        assert "💡 get_doc('large_test.md', page=2)" in result
        # 1ページ目の内容が含まれる
        assert "Line 1:" in result

    def test_small_file_no_warning(self):
        """小さなファイルには警告が表示されないテスト"""
        content = "\n".join([f"Line {i+1}" for i in range(10)])
        test_file = self.docs_dir / "small_test.md"
        test_file.write_text(content)

        manager = DocumentManager()
        manager.load_documents()

        # ページ指定なしで取得（警告なし）
        result = manager.get_document("small_test.md")
        assert "⚠️  Large document" not in result
        assert "Line 1" in result

    def test_pagination_environment_variables(self):
        """ページネーション環境変数のテスト（文字数ベース）"""
        # 環境変数を設定
        os.environ["DOCS_MAX_CHARS_PER_PAGE"] = "500"
        os.environ["DOCS_LARGE_FILE_THRESHOLD"] = "1000"

        content = "\n".join([f"Line {i+1}: Content with sufficient length to test character-based pagination" for i in range(20)])
        test_file = self.docs_dir / "env_test.md"
        test_file.write_text(content)

        manager = DocumentManager()
        manager.load_documents()

        # 設定が正しく読み込まれているか確認
        assert manager.max_chars_per_page == 500
        assert manager.large_file_threshold == 1000

        # 閾値を超えるため警告が表示される
        result = manager.get_document("env_test.md")
        assert "⚠️  Large document auto-paginated" in result

        # 最大文字数500でページネーション
        page1 = manager.get_document("env_test.md", page=1)
        assert "Max chars per page: 500" in page1

        # 環境変数をクリア
        del os.environ["DOCS_MAX_CHARS_PER_PAGE"]
        del os.environ["DOCS_LARGE_FILE_THRESHOLD"]

    def test_backward_compatibility(self):
        """後方互換性のテスト（既存のAPIが引き続き動作する）"""
        content = "# Test Document\n\nThis is a test."
        test_file = self.docs_dir / "compat_test.md"
        test_file.write_text(content)

        manager = DocumentManager()
        manager.load_documents()

        # 従来の引数なしの呼び出し
        result = manager.get_document("compat_test.md")
        assert result == content

        # 存在しないファイル
        result = manager.get_document("notfound.md")
        assert "Error: Document not found" in result
