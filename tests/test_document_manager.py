import sys
from pathlib import Path
import tempfile
import shutil

# srcディレクトリをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from document_manager import DocumentManager


class TestDocumentManager:
    """DocumentManagerのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.temp_dir = tempfile.mkdtemp()
        self.docs_dir = Path(self.temp_dir) / "docs"
        self.docs_dir.mkdir()
        
        # テスト用のフォルダとファイルを作成
        # docs1フォルダ
        docs1 = self.docs_dir / "docs1"
        docs1.mkdir()
        (docs1 / "test1.md").write_text("# Test Document 1\nThis is test content.")
        (docs1 / "test2.mdx").write_text("# Test Document 2\nAnother test content.")
        
        # docs2フォルダ
        docs2 = self.docs_dir / "docs2"
        docs2.mkdir()
        (docs2 / "config.json").write_text('{"key": "value"}')
        
        # docs3フォルダ
        docs3 = self.docs_dir / "docs3"
        docs3.mkdir()
        (docs3 / "guide.md").write_text("# Guide\nThis is a guide.")
    
    def teardown_method(self):
        """各テストメソッドの後に実行"""
        shutil.rmtree(self.temp_dir)
    
    def test_load_all_documents(self):
        """全ドキュメントを読み込むテスト"""
        manager = DocumentManager()
        manager.base_dir = Path(self.temp_dir)
        manager.docs_dir = self.docs_dir
        manager.load_documents()
        
        # 全てのファイルが読み込まれているか確認
        assert len(manager.docs_content) == 4
        assert "docs/docs1/test1.md" in manager.docs_content
        assert "docs/docs1/test2.mdx" in manager.docs_content
        assert "docs/docs2/config.json" in manager.docs_content
        assert "docs/docs3/guide.md" in manager.docs_content
    
    def test_load_specific_folders(self):
        """特定フォルダのみを読み込むテスト"""
        # docs1とdocs3のみを指定
        manager = DocumentManager(allowed_folders=["docs1", "docs3"])
        manager.base_dir = Path(self.temp_dir)
        manager.docs_dir = self.docs_dir
        manager.load_documents()
        
        # 指定したフォルダのファイルのみが読み込まれているか確認
        assert len(manager.docs_content) == 3
        assert "docs/docs1/test1.md" in manager.docs_content
        assert "docs/docs1/test2.mdx" in manager.docs_content
        assert "docs/docs3/guide.md" in manager.docs_content
        # docs2のファイルは読み込まれていないはず
        assert "docs/docs2/config.json" not in manager.docs_content
    
    def test_load_single_folder(self):
        """単一フォルダのみを読み込むテスト"""
        # docs2のみを指定
        manager = DocumentManager(allowed_folders=["docs2"])
        manager.base_dir = Path(self.temp_dir)
        manager.docs_dir = self.docs_dir
        manager.load_documents()
        
        # docs2のファイルのみが読み込まれているか確認
        assert len(manager.docs_content) == 1
        assert "docs/docs2/config.json" in manager.docs_content
    
    def test_load_nonexistent_folder(self, capsys):
        """存在しないフォルダを指定した場合のテスト"""
        # 存在しないフォルダを指定
        manager = DocumentManager(allowed_folders=["nonexistent"])
        manager.base_dir = Path(self.temp_dir)
        manager.docs_dir = self.docs_dir
        manager.load_documents()
        
        # ファイルが読み込まれていないことを確認
        assert len(manager.docs_content) == 0
        
        # 警告メッセージが出力されているか確認
        captured = capsys.readouterr()
        assert "Warning: Folder not found: nonexistent" in captured.out
    
    def test_get_document(self):
        """ドキュメント取得のテスト"""
        manager = DocumentManager(allowed_folders=["docs1"])
        manager.base_dir = Path(self.temp_dir)
        manager.docs_dir = self.docs_dir
        manager.load_documents()
        
        # 存在するドキュメントを取得
        content = manager.get_document("docs/docs1/test1.md")
        assert "# Test Document 1" in content
        
        # 存在しないドキュメントを取得
        error = manager.get_document("docs/nonexistent.md")
        assert "Error: Document not found" in error