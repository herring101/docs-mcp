import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

# モックHTML
MOCK_HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <title>MCP JP - Model Context Protocol日本語ドキュメント</title>
</head>
<body>
    <header>
        <h1>MCP JP</h1>
        <nav>
            <a href="/docs">ドキュメント</a>
            <a href="/tutorial">チュートリアル</a>
        </nav>
    </header>
    
    <main>
        <section>
            <h2>Model Context Protocolとは</h2>
            <p>MCPは、LLMアプリケーションが外部のデータソースやツールと<strong>安全に</strong>接続するための標準プロトコルです。</p>
            
            <h3>主な特徴</h3>
            <ul>
                <li>統一されたインターフェース</li>
                <li>セキュアな接続</li>
                <li>拡張性の高い設計</li>
            </ul>
            
            <h3>サンプルコード</h3>
            <pre><code class="language-python">
from mcp import Server

server = Server("my-server")
server.run()
            </code></pre>
        </section>
        
        <section>
            <h2>関連リンク</h2>
            <a href="/docs/getting-started">はじめに</a>
            <a href="https://github.com/example/mcp">GitHub</a>
        </section>
    </main>
</body>
</html>
"""

EXPECTED_MARKDOWN = """# MCP JP

[ドキュメント](/docs)
[チュートリアル](/tutorial)

## Model Context Protocolとは

MCPは、LLMアプリケーションが外部のデータソースやツールと**安全に**接続するための標準プロトコルです。

### 主な特徴

* 統一されたインターフェース
* セキュアな接続
* 拡張性の高い設計

### サンプルコード

```
from mcp import Server

server = Server("my-server")
server.run()
```

## 関連リンク

[はじめに](/docs/getting-started)
[GitHub](https://github.com/example/mcp)"""


class TestURLImporter:
    
    @patch('requests.get')
    def test_fetch_single_page(self, mock_get):
        """単一ページの取得とMarkdown変換のテスト"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = MOCK_HTML_CONTENT
        mock_response.url = "https://mcp-jp.apidog.io/"
        mock_get.return_value = mock_response
        
        from import_from_url import URLImporter
        
        importer = URLImporter()
        content, links = importer.fetch_page("https://mcp-jp.apidog.io/")
        
        assert content is not None
        assert "MCP JP" in content
        assert "Model Context Protocolとは" in content
        assert len(links) > 0
        
    def test_html_to_markdown_conversion(self):
        """HTMLからMarkdownへの変換テスト"""
        from import_from_url import URLImporter
        
        importer = URLImporter()
        markdown = importer.html_to_markdown(MOCK_HTML_CONTENT)
        
        # 基本的な変換確認
        assert "# MCP JP" in markdown
        assert "## Model Context Protocolとは" in markdown
        assert "**安全に**" in markdown
        assert "* 統一されたインターフェース" in markdown
        assert "```" in markdown  # コードブロック
        assert "[ドキュメント]" in markdown  # リンク
        
    def test_url_to_filepath(self):
        """URLからファイルパスへの変換テスト"""
        from import_from_url import URLImporter
        
        importer = URLImporter(output_dir="docs/imported")
        
        # ルートURL
        path = importer.url_to_filepath("https://mcp-jp.apidog.io/")
        assert path == "docs/imported/index.md"
        
        # サブページ
        path = importer.url_to_filepath("https://mcp-jp.apidog.io/docs/getting-started")
        assert path == "docs/imported/docs/getting-started.md"
        
        # 末尾スラッシュ付き
        path = importer.url_to_filepath("https://mcp-jp.apidog.io/tutorial/")
        assert path == "docs/imported/tutorial/index.md"
        
        # 日本語URLのテスト
        path = importer.url_to_filepath("https://mcp-jp.apidog.io/%E3%82%B5%E3%83%BC%E3%83%90%E3%83%BC%E9%96%8B%E7%99%BA%E8%80%85%E5%90%91%E3%81%91-870822m0")
        assert path == "docs/imported/サーバー開発者向け-870822m0.md"
        
        # 特殊文字を含むURL
        path = importer.url_to_filepath("https://example.com/path/with:special*chars")
        assert path == "docs/imported/path/with_special_chars.md"
        
    @patch('requests.get')
    def test_crawl_with_depth(self, mock_get):
        """深さ制限付きクロールのテスト"""
        # ルートページ
        root_response = Mock()
        root_response.status_code = 200
        root_response.text = MOCK_HTML_CONTENT
        root_response.url = "https://mcp-jp.apidog.io/"
        
        # サブページ
        sub_response = Mock()
        sub_response.status_code = 200
        sub_response.text = "<html><body><h1>Getting Started</h1></body></html>"
        sub_response.url = "https://mcp-jp.apidog.io/docs/getting-started"
        
        mock_get.side_effect = [root_response, sub_response]
        
        from import_from_url import URLImporter
        
        importer = URLImporter(max_depth=1)
        pages = importer.crawl("https://mcp-jp.apidog.io/")
        
        assert len(pages) >= 1
        assert "https://mcp-jp.apidog.io/" in pages
        
    def test_filter_links(self):
        """リンクフィルタリングのテスト"""
        from import_from_url import URLImporter
        
        importer = URLImporter(
            include_patterns=[r"/docs/.*"],
            exclude_patterns=[r".*/api/.*"]
        )
        
        links = [
            "https://mcp-jp.apidog.io/docs/intro",
            "https://mcp-jp.apidog.io/tutorial",
            "https://mcp-jp.apidog.io/docs/api/reference",
            "https://external.com/page"
        ]
        
        filtered = importer.filter_links(links, "https://mcp-jp.apidog.io/")
        
        assert "https://mcp-jp.apidog.io/docs/intro" in filtered
        assert "https://mcp-jp.apidog.io/tutorial" not in filtered
        assert "https://mcp-jp.apidog.io/docs/api/reference" not in filtered
        assert "https://external.com/page" not in filtered
        
    @patch('os.makedirs')
    @patch('builtins.open', new_callable=MagicMock)
    def test_save_markdown(self, mock_open, mock_makedirs):
        """Markdownファイルの保存テスト"""
        from import_from_url import URLImporter
        
        importer = URLImporter(output_dir="docs/imported")
        
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        importer.save_page("https://mcp-jp.apidog.io/", "# Test Content")
        
        mock_makedirs.assert_called()
        mock_open.assert_called_with("docs/imported/index.md", "w", encoding="utf-8")
        mock_file.write.assert_called_with("# Test Content")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])