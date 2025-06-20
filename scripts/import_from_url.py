#!/usr/bin/env python3
"""
URLからドキュメントを取得してMarkdownに変換するスクリプト
"""
import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Set, Optional
from urllib.parse import urljoin, urlparse, urlunparse, unquote
import time
import unicodedata

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md


class URLImporter:
    def __init__(
        self,
        output_dir: str = "docs/imported",
        max_depth: int = 2,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        delay: float = 0.5
    ):
        self.output_dir = output_dir
        self.max_depth = max_depth
        self.include_patterns = [re.compile(p) for p in (include_patterns or [])]
        self.exclude_patterns = [re.compile(p) for p in (exclude_patterns or [])]
        self.delay = delay
        self.visited_urls: Set[str] = set()
        
    def fetch_page(self, url: str) -> Tuple[Optional[str], List[str]]:
        """ページを取得してMarkdownに変換"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # リンクを抽出
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(url, href)
                links.append(absolute_url)
            
            # HTMLをMarkdownに変換
            markdown = self.html_to_markdown(response.text)
            
            return markdown, links
            
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None, []
    
    def html_to_markdown(self, html: str) -> str:
        """HTMLをMarkdownに変換"""
        # markdownifyのオプション
        return md(
            html,
            heading_style="ATX",
            bullets="*",
            code_language="",
            strip=['script', 'style', 'meta', 'link']
        ).strip()
    
    def sanitize_filename(self, filename: str) -> str:
        """ファイル名をファイルシステムで安全な形式に変換"""
        # URLデコード
        filename = unquote(filename)
        
        # Windowsで使えない文字を置換
        invalid_chars = '<>:"|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # 制御文字を削除
        filename = ''.join(char for char in filename if not unicodedata.category(char).startswith('C'))
        
        # 先頭・末尾の空白とピリオドを削除
        filename = filename.strip(' .')
        
        # 空になった場合はデフォルト名
        if not filename:
            filename = 'untitled'
            
        return filename
    
    def url_to_filepath(self, url: str) -> str:
        """URLをファイルパスに変換"""
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        # 空またはディレクトリ（末尾スラッシュ）の場合
        if not path:
            path = 'index.md'
        elif parsed.path.endswith('/'):
            # パスの各部分をサニタイズ
            parts = [self.sanitize_filename(part) for part in path.split('/') if part]
            parts.append('index.md')
            path = os.path.join(*parts)
        else:
            # パスの各部分をサニタイズ
            parts = [self.sanitize_filename(part) for part in path.split('/') if part]
            if parts:
                # 最後の部分に拡張子がない場合は.mdを追加
                if not parts[-1].endswith('.md'):
                    parts[-1] += '.md'
                path = os.path.join(*parts)
            else:
                path = 'index.md'
            
        return os.path.join(self.output_dir, path)
    
    def filter_links(self, links: List[str], base_url: str) -> List[str]:
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
            if self.include_patterns:
                if not any(p.search(path) for p in self.include_patterns):
                    continue
                    
            filtered.append(link)
            
        return filtered
    
    def normalize_url(self, url: str) -> str:
        """URLを正規化（末尾スラッシュやフラグメントを削除）"""
        parsed = urlparse(url)
        # フラグメントを削除し、末尾スラッシュを統一
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip('/') or '/',
            parsed.params,
            parsed.query,
            ''
        ))
        return normalized
    
    def crawl(self, start_url: str) -> dict:
        """指定された深さまでクロール"""
        pages = {}
        queue = [(self.normalize_url(start_url), 0)]
        
        while queue:
            url, depth = queue.pop(0)
            
            if url in self.visited_urls or depth > self.max_depth:
                continue
                
            self.visited_urls.add(url)
            
            print(f"Fetching: {url} (depth: {depth})")
            content, links = self.fetch_page(url)
            
            if content:
                pages[url] = content
                
                # 次のレベルのリンクを追加
                if depth < self.max_depth:
                    filtered_links = self.filter_links(links, start_url)
                    for link in filtered_links:
                        normalized_link = self.normalize_url(link)
                        if normalized_link not in self.visited_urls:
                            queue.append((normalized_link, depth + 1))
            
            # レート制限
            time.sleep(self.delay)
            
        return pages
    
    def save_page(self, url: str, content: str):
        """ページを保存"""
        filepath = self.url_to_filepath(url)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"Saved: {filepath}")
    
    def import_from_url(self, url: str):
        """URLからドキュメントをインポート"""
        print(f"Starting import from: {url}")
        print(f"Output directory: {self.output_dir}")
        print(f"Max depth: {self.max_depth}")
        
        pages = self.crawl(url)
        
        print(f"\nFound {len(pages)} pages")
        
        for page_url, content in pages.items():
            self.save_page(page_url, content)
            
        print(f"\nImport completed! {len(pages)} pages saved to {self.output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='URLからドキュメントを取得してMarkdownに変換'
    )
    parser.add_argument('url', help='インポート元のURL')
    parser.add_argument(
        '--output-dir', '-o',
        default='docs/imported',
        help='出力先ディレクトリ (default: docs/imported)'
    )
    parser.add_argument(
        '--depth', '-d',
        type=int,
        default=2,
        help='クロールの深さ (default: 2)'
    )
    parser.add_argument(
        '--include-pattern', '-i',
        action='append',
        dest='include_patterns',
        help='含めるURLパターン（正規表現）'
    )
    parser.add_argument(
        '--exclude-pattern', '-e',
        action='append',
        dest='exclude_patterns',
        help='除外するURLパターン（正規表現）'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=0.5,
        help='リクエスト間の遅延（秒） (default: 0.5)'
    )
    
    args = parser.parse_args()
    
    importer = URLImporter(
        output_dir=args.output_dir,
        max_depth=args.depth,
        include_patterns=args.include_patterns,
        exclude_patterns=args.exclude_patterns,
        delay=args.delay
    )
    
    importer.import_from_url(args.url)


if __name__ == '__main__':
    main()