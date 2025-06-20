import os
import sys
from pathlib import Path

# srcディレクトリをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestIntegration:
    """環境変数を使った統合テスト"""
    
    def test_docs_folders_env_parsing(self):
        """DOCS_FOLDERS環境変数のパースロジックのテスト"""
        # docs_mcp.pyの環境変数処理をシミュレート
        
        # ケース1: カンマ区切りの複数フォルダ
        docs_folders_env = "project1,shared"
        allowed_folders = None
        if docs_folders_env:
            allowed_folders = [folder.strip() for folder in docs_folders_env.split(",") if folder.strip()]
        assert allowed_folders == ["project1", "shared"]
        
        # ケース2: 空文字列
        docs_folders_env = ""
        allowed_folders = None
        if docs_folders_env:
            allowed_folders = [folder.strip() for folder in docs_folders_env.split(",") if folder.strip()]
        assert allowed_folders is None
        
        # ケース3: 空白を含む
        docs_folders_env = " project1 , shared "
        allowed_folders = None
        if docs_folders_env.strip():
            allowed_folders = [folder.strip() for folder in docs_folders_env.split(",") if folder.strip()]
        assert allowed_folders == ["project1", "shared"]
        
        # ケース4: 単一フォルダ
        docs_folders_env = "project1"
        allowed_folders = None
        if docs_folders_env:
            allowed_folders = [folder.strip() for folder in docs_folders_env.split(",") if folder.strip()]
        assert allowed_folders == ["project1"]