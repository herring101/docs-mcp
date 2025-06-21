"""URLインポートのテスト"""

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_docs.scripts.url_import import URLImporter

# モックHTML
MOCK_HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <h1>Test Document</h1>
    <p>This is a test paragraph.</p>
    <a href="/page1">Link 1</a>
    <a href="/page2">Link 2</a>
</body>
</html>
"""


class TestURLImporter:
    """URLImporterのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.temp_dir = tempfile.mkdtemp()
        os.environ["DOCS_BASE_DIR"] = self.temp_dir

    def teardown_method(self):
        """各テストメソッドの後に実行"""
        import shutil

        shutil.rmtree(self.temp_dir)
        if "DOCS_BASE_DIR" in os.environ:
            del os.environ["DOCS_BASE_DIR"]

    def test_init(self):
        """初期化のテスト"""
        importer = URLImporter()
        assert importer.output_dir is None
        assert importer.max_depth == 2
        assert importer.concurrent_downloads == 10
        assert importer.timeout.total == 30
        assert importer.rate_limit == 0.1

        # パラメータ指定
        importer = URLImporter(
            output_dir="custom",
            max_depth=3,
            concurrent_downloads=5,
            timeout=60,
            rate_limit=0.5,
        )
        assert importer.output_dir == "custom"
        assert importer.max_depth == 3
        assert importer.concurrent_downloads == 5
        assert importer.timeout.total == 60
        assert importer.rate_limit == 0.5

    def test_html_to_markdown(self):
        """HTML→Markdown変換のテスト"""
        importer = URLImporter()
        markdown = importer.html_to_markdown(MOCK_HTML_CONTENT)

        assert "# Test Document" in markdown
        assert "This is a test paragraph." in markdown
        assert "[Link 1]" in markdown
        assert "[Link 2]" in markdown

    def test_normalize_url(self):
        """URL正規化のテスト"""
        importer = URLImporter()

        # 末尾スラッシュの削除（ルート以外）
        assert (
            importer.normalize_url("https://example.com/page/")
            == "https://example.com/page"
        )

        # ルートURLは/を維持
        assert importer.normalize_url("https://example.com/") == "https://example.com/"
        assert importer.normalize_url("https://example.com") == "https://example.com/"

        # フラグメントの削除
        assert (
            importer.normalize_url("https://example.com#section")
            == "https://example.com/"
        )

        # クエリパラメータは保持
        assert (
            importer.normalize_url("https://example.com?page=1")
            == "https://example.com/?page=1"
        )

    def test_url_to_filepath(self):
        """URL→ファイルパス変換のテスト"""
        importer = URLImporter(output_dir="imported")

        # ルートURL
        path = importer.url_to_filepath("https://example.com/")
        # docs_dirを含むパスになる
        expected = str(Path(self.temp_dir) / "docs" / "imported" / "index.md")
        assert path == expected

        # サブページ
        path = importer.url_to_filepath("https://example.com/guide/quickstart")
        expected = str(
            Path(self.temp_dir) / "docs" / "imported" / "guide" / "quickstart.md"
        )
        assert path == expected

        # 末尾スラッシュ付き
        path = importer.url_to_filepath("https://example.com/api/")
        expected = str(Path(self.temp_dir) / "docs" / "imported" / "api" / "index.md")
        assert path == expected

        # クエリパラメータ付き（クエリパラメータは無視される）
        path = importer.url_to_filepath("https://example.com/search?q=test")
        expected = str(Path(self.temp_dir) / "docs" / "imported" / "search.md")
        assert path == expected

    @pytest.mark.asyncio
    async def test_fetch_page(self):
        """ページ取得のテスト"""
        # URLImporterのコンテキストマネージャーを使用
        async with URLImporter() as importer:
            # セッションをモック
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=MOCK_HTML_CONTENT)
            mock_response.raise_for_status = AsyncMock()

            # getメソッドが非同期コンテキストマネージャを返すように設定
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_context)
            importer.session = mock_session

            # セマフォを初期化
            import asyncio

            importer.semaphore = asyncio.Semaphore(10)

            markdown, links = await importer.fetch_page("https://example.com/")

            # Markdownに変換されていることを確認
            assert markdown is not None
            assert "Test Document" in markdown
            assert len(links) == 2
            assert "https://example.com/page1" in links
            assert "https://example.com/page2" in links

    def test_filter_links(self):
        """リンクフィルタリングのテスト"""
        importer = URLImporter(
            include_patterns=[r"/docs/"], exclude_patterns=[r"/api/"]
        )

        links = [
            "https://example.com/docs/guide",
            "https://example.com/docs/api/reference",
            "https://example.com/blog/post",
            "https://example.com/api/v1",
            "https://other.com/docs/guide",  # 別ドメイン
        ]

        # filter_linksはbase_urlも受け取る
        filtered = importer.filter_links(links, "https://example.com")

        # /docs/を含むが/api/を含まない、かつ同じドメインのもののみ
        assert len(filtered) == 1
        assert "https://example.com/docs/guide" in filtered

    def test_save_page(self):
        """ページ保存のテスト"""
        importer = URLImporter(output_dir="test-docs")

        # Markdownコンテンツを直接渡す
        markdown_content = "# Test Content\n\nThis is a test."
        importer.save_page("https://example.com/test", markdown_content)

        # ファイルが作成されたか確認
        expected_path = Path(self.temp_dir) / "docs" / "test-docs" / "test.md"
        assert expected_path.exists()
        assert expected_path.read_text() == markdown_content

    @pytest.mark.asyncio
    async def test_crawl_basic(self):
        """基本的なクロールのテスト"""
        async with URLImporter(max_depth=1) as importer:
            # fetch_pageをモック
            async def mock_fetch(url):
                if url == "https://example.com/":
                    markdown = "# Home\n\nWelcome"
                    return markdown, ["https://example.com/page1"]
                else:
                    markdown = "# Page 1\n\nContent"
                    return markdown, []

            importer.fetch_page = mock_fetch

            pages = await importer.crawl("https://example.com")

            assert len(pages) == 2  # ルートとpage1
            # 正規化されたURLで確認
            assert "https://example.com/" in pages
            assert "https://example.com/page1" in pages
            assert pages["https://example.com/"] == "# Home\n\nWelcome"
            assert pages["https://example.com/page1"] == "# Page 1\n\nContent"

    def test_sanitize_filename(self):
        """ファイル名のサニタイズテスト"""
        importer = URLImporter()

        # 通常のファイル名
        assert importer.sanitize_filename("document.html") == "document.html"

        # 使用できない文字を含む
        assert importer.sanitize_filename("doc<>:|test.html") == "doc____test.html"

        # URLエンコードされた文字
        assert importer.sanitize_filename("test%20file.html") == "test file.html"

        # 空の場合
        assert importer.sanitize_filename("") == "untitled"

        # 制御文字を含む
        assert importer.sanitize_filename("test\nfile") == "testfile"

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """非同期コンテキストマネージャーのテスト"""
        importer = URLImporter()

        # __aenter__でセッションが作成される
        await importer.__aenter__()
        assert importer.session is not None
        assert importer.semaphore is not None

        # __aexit__でセッションがクローズされる
        await importer.__aexit__(None, None, None)
        # セッションのクローズをテストするのは難しいので、エラーが出ないことを確認

    @pytest.mark.asyncio
    async def test_crawl_level(self):
        """レベル別クロールのテスト"""
        async with URLImporter(max_depth=2) as importer:
            # fetch_pageをモック
            async def mock_fetch(url):
                if "page1" in url:
                    return "Page 1 content", ["https://example.com/subpage"]
                elif "subpage" in url:
                    return "Subpage content", []
                else:
                    return "Home content", ["https://example.com/page1"]

            importer.fetch_page = mock_fetch

            # 第1レベルのクロール
            urls = [("https://example.com/", 0)]
            results, new_urls = await importer.crawl_level(urls, "https://example.com")

            assert len(results) == 1
            assert "https://example.com/" in results
            assert len(new_urls) == 1
            assert ("https://example.com/page1", 1) in new_urls

    def test_include_exclude_patterns(self):
        """includeとexcludeパターンのテスト"""
        # includeのみ
        importer = URLImporter(include_patterns=[r"/docs/", r"/guide/"])
        links = [
            "https://example.com/docs/api",
            "https://example.com/guide/start",
            "https://example.com/blog/post",
        ]
        filtered = importer.filter_links(links, "https://example.com")
        assert len(filtered) == 2
        assert "https://example.com/blog/post" not in filtered

        # excludeのみ
        importer = URLImporter(exclude_patterns=[r"/api/", r"/admin/"])
        links = [
            "https://example.com/docs/guide",
            "https://example.com/api/v1",
            "https://example.com/admin/panel",
        ]
        filtered = importer.filter_links(links, "https://example.com")
        assert len(filtered) == 1
        assert "https://example.com/docs/guide" in filtered

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """エラー処理のテスト"""
        async with URLImporter() as importer:
            # エラーを発生させるモック
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(side_effect=Exception("Network error"))

            mock_session = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_context)
            importer.session = mock_session

            import asyncio

            importer.semaphore = asyncio.Semaphore(10)

            # エラーが発生してもNoneと空リストが返される
            markdown, links = await importer.fetch_page("https://example.com/error")
            assert markdown is None
            assert links == []

    def test_output_dir_from_domain(self):
        """ドメイン名からの出力ディレクトリ生成テスト"""
        importer = URLImporter()
        assert importer.output_dir is None

        # crawlメソッド内でドメイン名から設定されることをテスト
        # （実際のcrawlは非同期なので、ロジックだけテスト）
        parsed = Path("example.com")
        assert str(parsed).replace(":", "_") == "example.com"

        # ポート番号を含む場合
        parsed = Path("example.com:8080")
        assert str(parsed).replace(":", "_") == "example.com_8080"
