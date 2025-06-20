#!/usr/bin/env python3
"""
GitHubリポジトリの特定フォルダ以下を取得するスクリプト
"""
import argparse
import asyncio
import os
import re
import base64
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

import aiohttp
from tqdm import tqdm


class GitHubImporter:
    def __init__(
        self,
        output_dir: str = "docs/github",
        github_token: Optional[str] = None,
        concurrent_downloads: int = 10,
        timeout: int = 30,
        rate_limit: float = 0.1,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ):
        self.output_dir = output_dir
        self.github_token = github_token or os.environ.get('GITHUB_TOKEN')
        self.concurrent_downloads = concurrent_downloads
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.rate_limit = rate_limit
        self.include_patterns = [re.compile(p) for p in (include_patterns or [])]
        self.exclude_patterns = [re.compile(p) for p in (exclude_patterns or [])]
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore: Optional[asyncio.Semaphore] = None
        self.progress_bar: Optional[tqdm] = None
        
        # GitHub API用のヘッダー
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
        }
        if self.github_token:
            self.headers['Authorization'] = f'token {self.github_token}'
    
    def parse_github_url(self, url: str) -> Tuple[str, str, str, str]:
        """GitHubのURLを解析してowner、repo、branch、pathを取得"""
        # URLパターン: https://github.com/{owner}/{repo}/tree/{branch}/{path}
        parsed = urlparse(url)
        parts = parsed.path.strip('/').split('/')
        
        if len(parts) < 2:
            raise ValueError("Invalid GitHub URL")
        
        owner = parts[0]
        repo = parts[1]
        
        # デフォルトブランチとパス
        branch = 'main'
        path = ''
        
        if len(parts) > 3 and parts[2] == 'tree':
            branch = parts[3]
            if len(parts) > 4:
                path = '/'.join(parts[4:])
        elif len(parts) > 2:
            # tree/がない場合はパスとして扱う
            path = '/'.join(parts[2:])
        
        return owner, repo, branch, path
    
    def should_include_file(self, file_path: str) -> bool:
        """ファイルがフィルタ条件に合致するかチェック"""
        # exclude_patternsにマッチしたら除外
        if any(p.search(file_path) for p in self.exclude_patterns):
            return False
            
        # include_patternsが指定されている場合、いずれかにマッチする必要がある
        if self.include_patterns:
            return any(p.search(file_path) for p in self.include_patterns)
            
        return True
    
    async def __aenter__(self):
        """非同期コンテキストマネージャーのエントリー"""
        connector = aiohttp.TCPConnector(
            limit=self.concurrent_downloads * 2,
            limit_per_host=self.concurrent_downloads
        )
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout,
            headers=self.headers
        )
        self.semaphore = asyncio.Semaphore(self.concurrent_downloads)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャーのエグジット"""
        if self.session:
            await self.session.close()
    
    async def get_contents(self, owner: str, repo: str, path: str, branch: str) -> List[Dict]:
        """GitHub APIを使用してディレクトリの内容を取得"""
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        params = {'ref': branch}
        
        async with self.session.get(url, params=params) as response:
            if response.status == 404:
                # 404の場合、ブランチ名が違う可能性があるので'master'を試す
                params['ref'] = 'master'
                async with self.session.get(url, params=params) as retry_response:
                    retry_response.raise_for_status()
                    return await retry_response.json()
            else:
                response.raise_for_status()
                return await response.json()
    
    async def download_file(self, file_info: Dict) -> Tuple[str, bytes]:
        """ファイルの内容をダウンロード"""
        async with self.semaphore:
            try:
                # download_urlがある場合はそれを使用
                if 'download_url' in file_info and file_info['download_url']:
                    async with self.session.get(file_info['download_url']) as response:
                        response.raise_for_status()
                        content = await response.read()
                else:
                    # APIから内容を取得
                    async with self.session.get(file_info['url']) as response:
                        response.raise_for_status()
                        data = await response.json()
                        content = base64.b64decode(data['content'])
                
                if self.progress_bar is not None:
                    self.progress_bar.update(1)
                    
                return file_info['path'], content
                
            except Exception as e:
                print(f"\nError downloading {file_info['path']}: {e}")
                if self.progress_bar is not None:
                    self.progress_bar.update(1)
                return file_info['path'], b''
    
    async def collect_files(self, owner: str, repo: str, path: str, branch: str) -> List[Dict]:
        """再帰的にすべてのファイルを収集"""
        all_files = []
        
        async def process_directory(current_path: str):
            try:
                contents = await self.get_contents(owner, repo, current_path, branch)
                
                # contentsが辞書の場合（単一ファイル）はリストに変換
                if isinstance(contents, dict):
                    contents = [contents]
                
                tasks = []
                for item in contents:
                    if item['type'] == 'file':
                        if self.should_include_file(item['path']):
                            all_files.append(item)
                    elif item['type'] == 'dir':
                        tasks.append(process_directory(item['path']))
                
                # サブディレクトリを並列で処理
                if tasks:
                    await asyncio.gather(*tasks)
                    
            except Exception as e:
                print(f"Error processing directory {current_path}: {e}")
        
        await process_directory(path)
        return all_files
    
    def save_file(self, base_path: str, file_path: str, content: bytes):
        """ファイルを保存"""
        # 相対パスを計算
        rel_path = file_path
        if base_path and file_path.startswith(base_path):
            rel_path = file_path[len(base_path):].lstrip('/')
        
        output_path = os.path.join(self.output_dir, rel_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        try:
            # テキストファイルとして保存を試みる
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content.decode('utf-8'))
        except UnicodeDecodeError:
            # バイナリファイルとして保存
            with open(output_path, 'wb') as f:
                f.write(content)
    
    async def import_from_github(self, url: str):
        """GitHubリポジトリからファイルをインポート"""
        owner, repo, branch, path = self.parse_github_url(url)
        
        print(f"Importing from GitHub repository")
        print(f"Owner: {owner}")
        print(f"Repository: {repo}")
        print(f"Branch: {branch}")
        print(f"Path: /{path}")
        print(f"Output directory: {self.output_dir}")
        
        # ファイル一覧を収集
        print("\nCollecting file list...")
        files = await self.collect_files(owner, repo, path, branch)
        
        if not files:
            print("No files found matching the criteria.")
            return
        
        print(f"Found {len(files)} files")
        
        # ファイルをダウンロード
        with tqdm(total=len(files), desc="Downloading files", unit="files") as pbar:
            self.progress_bar = pbar
            
            # バッチ処理で並列ダウンロード
            batch_size = self.concurrent_downloads * 2
            for i in range(0, len(files), batch_size):
                batch = files[i:i+batch_size]
                tasks = [self.download_file(file_info) for file_info in batch]
                results = await asyncio.gather(*tasks)
                
                # ファイルを保存
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = []
                    for file_path, content in results:
                        if content:
                            future = executor.submit(self.save_file, path, file_path, content)
                            futures.append(future)
                    
                    # 完了を待つ
                    for future in futures:
                        future.result()
                
                # レート制限
                if self.rate_limit > 0 and i + batch_size < len(files):
                    await asyncio.sleep(self.rate_limit)
        
        self.progress_bar = None
        print(f"\nImport completed! {len(files)} files saved to {self.output_dir}")


async def main():
    parser = argparse.ArgumentParser(
        description='GitHubリポジトリの特定フォルダ以下を取得'
    )
    parser.add_argument('url', help='GitHubリポジトリのURL（例: https://github.com/owner/repo/tree/main/path）')
    parser.add_argument(
        '--output-dir', '-o',
        default='docs/github',
        help='出力先ディレクトリ (default: docs/github)'
    )
    parser.add_argument(
        '--token', '-t',
        help='GitHub Personal Access Token（環境変数GITHUB_TOKENでも設定可）'
    )
    parser.add_argument(
        '--include-pattern', '-i',
        action='append',
        dest='include_patterns',
        help='含めるファイルパターン（正規表現）'
    )
    parser.add_argument(
        '--exclude-pattern', '-e',
        action='append',
        dest='exclude_patterns',
        help='除外するファイルパターン（正規表現）'
    )
    parser.add_argument(
        '--concurrent', '-c',
        type=int,
        default=10,
        help='同時ダウンロード数 (default: 10)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='タイムアウト（秒） (default: 30)'
    )
    parser.add_argument(
        '--rate-limit',
        type=float,
        default=0.1,
        help='レート制限（秒） (default: 0.1)'
    )
    
    args = parser.parse_args()
    
    async with GitHubImporter(
        output_dir=args.output_dir,
        github_token=args.token,
        concurrent_downloads=args.concurrent,
        timeout=args.timeout,
        rate_limit=args.rate_limit,
        include_patterns=args.include_patterns,
        exclude_patterns=args.exclude_patterns,
    ) as importer:
        await importer.import_from_github(args.url)


if __name__ == '__main__':
    asyncio.run(main())