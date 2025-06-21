#!/usr/bin/env python3
"""
URLからドキュメントを高速に取得してMarkdownに変換するスクリプト
"""

import argparse
import asyncio
import os
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse, urlunparse

import aiohttp
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from tqdm import tqdm


class URLImporter:
    def __init__(
        self,
        output_dir: str | None = None,
        max_depth: int = 2,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        concurrent_downloads: int = 10,
        timeout: int = 30,
        rate_limit: float = 0.1,
    ):
        self.output_dir = output_dir
        self.max_depth = max_depth
        self.include_patterns = [re.compile(p) for p in (include_patterns or [])]
        self.exclude_patterns = [re.compile(p) for p in (exclude_patterns or [])]
        self.concurrent_downloads = concurrent_downloads
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.rate_limit = rate_limit
        self.visited_urls: set[str] = set()
        self.session: aiohttp.ClientSession | None = None
        self.semaphore: asyncio.Semaphore | None = None
        self.progress_bar: tqdm | None = None

    async def __aenter__(self):
        """非同期コンテキストマネージャーのエントリー"""
        connector = aiohttp.TCPConnector(
            limit=self.concurrent_downloads * 2,
            limit_per_host=self.concurrent_downloads,
        )
        self.session = aiohttp.ClientSession(connector=connector, timeout=self.timeout)
        self.semaphore = asyncio.Semaphore(self.concurrent_downloads)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャーのエグジット"""
        if self.session:
            await self.session.close()

    async def fetch_page(self, url: str) -> tuple[str | None, list[str]]:
        """ページを非同期で取得してMarkdownに変換"""
        if self.semaphore is None:
            raise ValueError("Semaphore not initialized")
        async with self.semaphore:
            try:
                if self.session is None:
                    raise ValueError("Session not initialized")
                async with self.session.get(url) as response:
                    response.raise_for_status()
                    html_content = await response.text()

                    # BeautifulSoupでリンクを抽出（CPUバウンドタスク）
                    soup = BeautifulSoup(html_content, "html.parser")
                    links = []
                    for link in soup.find_all("a", href=True):
                        # BeautifulSoupのTagオブジェクトのみ処理
                        href = link.get("href", "")  # type: ignore
                        if href:
                            absolute_url = urljoin(url, str(href))
                            links.append(absolute_url)

                    # HTMLをMarkdownに変換
                    markdown = self.html_to_markdown(html_content)

                    if self.progress_bar is not None:
                        self.progress_bar.update(1)

                    return markdown, links

            except Exception as e:
                print(f"\nError fetching {url}: {e}")
                if self.progress_bar is not None:
                    self.progress_bar.update(1)
                return None, []

    def html_to_markdown(self, html: str) -> str:
        """HTMLをMarkdownに変換"""
        return md(
            html,
            heading_style="ATX",
            bullets="*",
            code_language="",
            strip=["script", "style", "meta", "link"],
        ).strip()

    def sanitize_filename(self, filename: str) -> str:
        """ファイル名をファイルシステムで安全な形式に変換"""
        # URLデコード
        filename = unquote(filename)

        # Windowsで使えない文字を置換
        invalid_chars = '<>:"|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")

        # 制御文字を削除
        filename = "".join(
            char for char in filename if not unicodedata.category(char).startswith("C")
        )

        # 先頭・末尾の空白とピリオドを削除
        filename = filename.strip(" .")

        # 空になった場合はデフォルト名
        if not filename:
            filename = "untitled"

        return filename

    def url_to_filepath(self, url: str) -> str:
        """URLをファイルパスに変換"""
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        # 空またはディレクトリ（末尾スラッシュ）の場合
        if not path:
            path = "index.md"
        elif parsed.path.endswith("/"):
            # パスの各部分をサニタイズ
            parts = [self.sanitize_filename(part) for part in path.split("/") if part]
            parts.append("index.md")
            path = os.path.join(*parts)
        else:
            # パスの各部分をサニタイズ
            parts = [self.sanitize_filename(part) for part in path.split("/") if part]
            if parts:
                # 最後の部分に拡張子がない場合は.mdを追加
                if not parts[-1].endswith(".md"):
                    parts[-1] += ".md"
                path = os.path.join(*parts)
            else:
                path = "index.md"

        # docs/ディレクトリ内に保存
        # DOCS_BASE_DIRが設定されていればそれを使用、なければ現在のディレクトリ
        docs_base_dir = os.getenv("DOCS_BASE_DIR", os.getcwd())
        base_dir = Path(docs_base_dir)
        docs_dir = base_dir / "docs"
        if self.output_dir is None:
            return str(docs_dir / path)
        return str(docs_dir / self.output_dir / path)

    def filter_links(self, links: list[str], base_url: str) -> list[str]:
        """リンクをフィルタリング"""
        base_domain = urlparse(base_url).netloc
        filtered = []

        for link in links:
            parsed = urlparse(link)

            # 同じドメインのみ
            if parsed.netloc != base_domain:
                continue

            # パターンマッチング
            path = parsed.path

            # exclude_patternsにマッチしたら除外
            if any(p.search(path) for p in self.exclude_patterns):
                continue

            # include_patternsが指定されている場合、いずれかにマッチする必要がある
            if self.include_patterns and not any(
                p.search(path) for p in self.include_patterns
            ):
                continue

            filtered.append(link)

        return filtered

    def normalize_url(self, url: str) -> str:
        """URLを正規化（末尾スラッシュやフラグメントを削除）"""
        parsed = urlparse(url)
        # フラグメントを削除し、末尾スラッシュを統一
        normalized = urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path.rstrip("/") or "/",
                parsed.params,
                parsed.query,
                "",
            )
        )
        return normalized

    async def crawl_level(
        self, urls: list[tuple[str, int]], start_url: str
    ) -> tuple[dict[str, tuple[str, int]], list[tuple[str, int]]]:
        """同じ深さのURLを並列でクロール"""
        tasks = []
        task_urls = []
        results = {}

        for url, depth in urls:
            if url in self.visited_urls or depth > self.max_depth:
                continue

            self.visited_urls.add(url)
            task = self.fetch_page(url)
            tasks.append(task)
            task_urls.append((url, depth))

        if not tasks:
            return {}, []

        # 並列でページを取得
        fetched_data = await asyncio.gather(*tasks)

        # 結果を処理
        new_urls = []

        for i, (url, depth) in enumerate(task_urls):
            content, links = fetched_data[i]
            if content:
                results[url] = (content, depth)

                # 次のレベルのリンクを収集
                if depth < self.max_depth:
                    filtered_links = self.filter_links(links, start_url)
                    for link in filtered_links:
                        normalized_link = self.normalize_url(link)
                        if normalized_link not in self.visited_urls:
                            new_urls.append((normalized_link, depth + 1))

        # レート制限
        if self.rate_limit > 0:
            await asyncio.sleep(self.rate_limit)

        return results, new_urls

    async def crawl(self, start_url: str) -> dict[str, str]:
        """指定された深さまで非同期でクロール"""
        pages = {}
        queue = [(self.normalize_url(start_url), 0)]

        # デフォルトの出力先をドメイン名に設定
        if self.output_dir is None:
            parsed_url = urlparse(start_url)
            self.output_dir = parsed_url.netloc.replace(
                ":", "_"
            )  # ポート番号の:を_に置換

        # 全URLを収集して進捗バーを初期化
        print(f"Starting import from: {start_url}")
        # 実際の出力ディレクトリを表示
        # DOCS_BASE_DIRが設定されていればそれを使用、なければ現在のディレクトリ
        docs_base_dir = os.getenv("DOCS_BASE_DIR", os.getcwd())
        base_dir = Path(docs_base_dir)
        docs_dir = base_dir / "docs"
        if self.output_dir is None:
            actual_output_dir = docs_dir
        else:
            actual_output_dir = docs_dir / self.output_dir
        print(f"Output directory: {actual_output_dir}")
        print(f"Max depth: {self.max_depth}")
        print(f"Concurrent downloads: {self.concurrent_downloads}")

        with tqdm(desc="Downloading pages", unit="pages", leave=True) as pbar:
            self.progress_bar = pbar

            while queue:
                # 同じ深さのURLをグループ化
                current_level_urls = []
                next_level_urls = []

                for url, depth in queue:
                    if depth == queue[0][1]:
                        current_level_urls.append((url, depth))
                    else:
                        next_level_urls.append((url, depth))

                # 現在のレベルを並列処理
                results, new_urls = await self.crawl_level(
                    current_level_urls, start_url
                )

                # 結果を保存
                for url, (content, _) in results.items():
                    if content:
                        pages[url] = content

                # 次のレベルのURLをキューに追加
                queue = next_level_urls + new_urls

        self.progress_bar = None
        return pages

    def save_page(self, url: str, content: str):
        """ページを保存"""
        filepath = self.url_to_filepath(url)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    async def import_from_url(self, url: str):
        """URLからドキュメントを高速にインポート"""
        pages = await self.crawl(url)

        print(f"\nFound {len(pages)} pages")

        # ページを並列で保存
        with (
            ThreadPoolExecutor(max_workers=10) as executor,
            tqdm(total=len(pages), desc="Saving files", unit="files") as pbar,
        ):
            futures = []
            for page_url, content in pages.items():
                future = executor.submit(self.save_page, page_url, content)
                futures.append(future)

            for future in futures:
                future.result()
                pbar.update(1)

        # 実際の出力ディレクトリを表示
        # DOCS_BASE_DIRが設定されていればそれを使用、なければ現在のディレクトリ
        docs_base_dir = os.getenv("DOCS_BASE_DIR", os.getcwd())
        base_dir = Path(docs_base_dir)
        docs_dir = base_dir / "docs"
        if self.output_dir is None:
            actual_output_dir = docs_dir
        else:
            actual_output_dir = docs_dir / self.output_dir
        print(f"\nImport completed! {len(pages)} pages saved to {actual_output_dir}")


async def main():
    parser = argparse.ArgumentParser(
        description="URLからドキュメントを高速に取得してMarkdownに変換"
    )
    parser.add_argument("url", help="インポート元のURL")
    parser.add_argument(
        "--output-dir",
        "-o",
        default=None,
        help="出力先ディレクトリ (default: ドメイン名)",
    )
    parser.add_argument(
        "--depth", "-d", type=int, default=2, help="クロールの深さ (default: 2)"
    )
    parser.add_argument(
        "--include-pattern",
        "-i",
        action="append",
        dest="include_patterns",
        help="含めるURLパターン（正規表現）",
    )
    parser.add_argument(
        "--exclude-pattern",
        "-e",
        action="append",
        dest="exclude_patterns",
        help="除外するURLパターン（正規表現）",
    )
    parser.add_argument(
        "--concurrent",
        "-c",
        type=int,
        default=10,
        help="同時ダウンロード数 (default: 10)",
    )
    parser.add_argument(
        "--timeout", type=int, default=30, help="タイムアウト（秒） (default: 30)"
    )
    parser.add_argument(
        "--rate-limit", type=float, default=0.1, help="レート制限（秒） (default: 0.1)"
    )

    args = parser.parse_args()

    async with URLImporter(
        output_dir=args.output_dir,
        max_depth=args.depth,
        include_patterns=args.include_patterns,
        exclude_patterns=args.exclude_patterns,
        concurrent_downloads=args.concurrent,
        timeout=args.timeout,
        rate_limit=args.rate_limit,
    ) as importer:
        await importer.import_from_url(args.url)


def cli():
    """CLI entry point for PyPI installation."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
