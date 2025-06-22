#!/usr/bin/env python3
"""
Gitのsparse-checkoutを使用してGitHubリポジトリの特定フォルダを取得するスクリプト
"""

import argparse
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse


def parse_github_url(url: str) -> tuple[str, str, str | None, str]:
    """GitHub の URL を解析してリポジトリ情報を取得

    ブランチが URL に明示されていない場合は ``None`` を返す。
    """
    # URLパターン: https://github.com/{owner}/{repo}/tree/{branch}/{path}
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")

    if len(parts) < 2:
        raise ValueError("Invalid GitHub URL")

    owner = parts[0]
    repo = parts[1]

    # デフォルトブランチとパス
    branch: str | None = None
    path = ""

    if len(parts) > 3 and parts[2] == "tree":
        branch = parts[3]
        if len(parts) > 4:
            path = "/".join(parts[4:])
    elif len(parts) > 2:
        # tree/がない場合はパスとして扱う
        path = "/".join(parts[2:])

    return owner, repo, branch, path


def run_command(cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    """コマンドを実行"""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}")
        print(f"Error: {result.stderr}")
        raise subprocess.CalledProcessError(
            result.returncode, cmd, result.stdout, result.stderr
        )
    return result


def detect_default_branch(clone_url: str) -> str:
    """リポジトリのデフォルトブランチを検出する"""
    try:
        result = run_command(["git", "ls-remote", "--symref", clone_url, "HEAD"])
        for line in result.stdout.splitlines():
            match = re.search(r"refs/heads/(?P<branch>[^\t]+)\tHEAD", line)
            if match:
                return match.group("branch")
    except Exception as exc:
        print(f"Warning: failed to detect default branch: {exc}")
    return "main"


def import_with_sparse_checkout(url: str, output_dir: str | None = None):
    """sparse-checkoutを使用して特定のディレクトリのみをクローン"""
    owner, repo, branch, target_path = parse_github_url(url)

    clone_url = f"https://github.com/{owner}/{repo}.git"

    if branch is None:
        branch = detect_default_branch(clone_url)

    # デフォルトの出力先をリポジトリ名に設定
    if output_dir is None:
        output_dir = repo

    print("Importing from GitHub repository using Git")
    print(f"Owner: {owner}")
    print(f"Repository: {repo}")
    print(f"Branch: {branch}")
    print(f"Path: /{target_path}")

    # 一時ディレクトリでクローン
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = os.path.join(temp_dir, repo)

        print("\nCloning repository (sparse checkout)...")

        # 1. 最小限のクローン（no-checkoutで）
        run_command(
            [
                "git",
                "clone",
                "--no-checkout",
                "--depth",
                "1",
                "--filter=blob:none",
                "--branch",
                branch,
                clone_url,
                repo_dir,
            ]
        )

        # 2. sparse-checkoutを有効化
        run_command(["git", "sparse-checkout", "init", "--cone"], cwd=repo_dir)

        # 3. 必要なパスを設定
        if target_path:
            run_command(["git", "sparse-checkout", "set", target_path], cwd=repo_dir)
        else:
            # ルートディレクトリ全体の場合はsparse-checkoutを無効化
            run_command(["git", "sparse-checkout", "disable"], cwd=repo_dir)

        # 4. チェックアウト
        print(f"Checking out /{target_path}...")
        run_command(["git", "checkout"], cwd=repo_dir)

        # 5. ファイルをコピー
        # DOCS_BASE_DIRが設定されていればそれを使用、なければ現在のディレクトリ
        docs_base_dir = os.getenv("DOCS_BASE_DIR", os.getcwd())
        base_dir = Path(docs_base_dir)
        docs_dir = base_dir / "docs"
        output_path = docs_dir / output_dir

        # ソースディレクトリ
        src_dir = Path(repo_dir) / target_path if target_path else Path(repo_dir)

        if not src_dir.exists():
            print(f"Error: Directory {target_path} not found in repository")
            return

        # 出力ディレクトリを作成
        output_path.mkdir(parents=True, exist_ok=True)

        # ファイルをコピー
        print(f"\nCopying files to {output_path}...")
        file_count = 0

        # .gitディレクトリを除外してコピー
        for item in src_dir.rglob("*"):
            if ".git" in item.parts:
                continue

            if item.is_file():
                rel_path = item.relative_to(src_dir)
                dest_file = output_path / rel_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest_file)
                file_count += 1

        print(f"\nImport completed! {file_count} files saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Gitのsparse-checkoutを使用してGitHubリポジトリの特定フォルダを取得"
    )
    parser.add_argument(
        "url",
        help="GitHubリポジトリのURL（例: https://github.com/owner/repo/tree/main/path）",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=None,
        help="出力先ディレクトリ (default: リポジトリ名)",
    )

    args = parser.parse_args()

    try:
        import_with_sparse_checkout(args.url, args.output_dir)
    except subprocess.CalledProcessError:
        print("\nError: Git command failed")
        print("Please make sure Git is installed and you have internet connection")
        return 1
    except Exception as e:
        print(f"\nError: {e}")
        return 1

    return 0


def cli():
    """CLI entry point for PyPI installation."""
    exit(main())


if __name__ == "__main__":
    cli()
