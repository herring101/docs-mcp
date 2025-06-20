import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class DocumentManager:
    def __init__(self, allowed_folders: Optional[List[str]] = None):
        self.base_dir = Path(__file__).parent.parent
        self.docs_dir = self.base_dir / "docs"
        self.metadata_file = self.base_dir / "docs_metadata.json"
        self.embeddings_file = self.base_dir / "docs_embeddings.json"
        
        # 許可されたフォルダのリスト
        self.allowed_folders = allowed_folders
        
        self.docs_content: Dict[str, str] = {}
        self.docs_metadata: Dict[str, str] = {}
        self.embeddings_cache: Dict[str, List[float]] = {}
        
        # OpenAI クライアント初期化
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key else None
    
    def load_documents(self):
        """ドキュメント、メタデータ、embeddingsを読み込み"""
        # メタデータを読み込み
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                self.docs_metadata = json.load(f)
        
        # Embeddingsを読み込み
        if self.embeddings_file.exists():
            with open(self.embeddings_file, 'r', encoding='utf-8') as f:
                self.embeddings_cache = json.load(f)
                print(f"Loaded {len(self.embeddings_cache)} embeddings from cache")
        
        # 読み込むフォルダを決定
        if self.allowed_folders:
            # 指定されたフォルダのみを読み込む
            for folder_name in self.allowed_folders:
                folder_path = self.docs_dir / folder_name
                if folder_path.exists() and folder_path.is_dir():
                    self._load_folder(folder_path)
                else:
                    print(f"Warning: Folder not found: {folder_name}")
        else:
            # 全てのファイルを読み込む（従来の動作）
            self._load_all_files()
    
    def _load_folder(self, folder_path: Path):
        """特定のフォルダ内のファイルを読み込む"""
        for file_path in folder_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in ['.mdx', '.md', '.txt', '.json', '.ts', '.yml', '.yaml']:
                doc_path = str(file_path.relative_to(self.base_dir)).replace('\\', '/')
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.docs_content[doc_path] = content
                except Exception as e:
                    print(f"Error loading {doc_path}: {e}")
    
    def _load_all_files(self):
        """docs内のすべてのテキストファイルを読み込む"""
        for file_path in self.docs_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in ['.mdx', '.md', '.txt', '.json', '.ts', '.yml', '.yaml']:
                doc_path = str(file_path.relative_to(self.base_dir)).replace('\\', '/')
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.docs_content[doc_path] = content
                except Exception as e:
                    print(f"Error loading {doc_path}: {e}")
    
    def list_documents(self) -> str:
        """ドキュメント一覧を返す"""
        result = []
        for path in sorted(self.docs_content.keys()):
            description = self.docs_metadata.get(path, "")
            if description:
                result.append(f"{path} - {description}")
            else:
                result.append(path)
        return "\n".join(result)
    
    def get_document(self, path: str) -> str:
        """指定されたドキュメントの内容を返す"""
        if path not in self.docs_content:
            return f"Error: Document not found: {path}"
        return self.docs_content[path]
    
    def grep_search(self, pattern: str, ignore_case: bool = True) -> str:
        """正規表現でドキュメントを検索"""
        try:
            flags = re.IGNORECASE if ignore_case else 0
            regex = re.compile(pattern, flags)
        except re.error as e:
            return f"Error: Invalid regex pattern: {e}"
        
        results = []
        for doc_path, content in sorted(self.docs_content.items()):
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if regex.search(line):
                    line_preview = line.strip()
                    if len(line_preview) > 120:
                        line_preview = line_preview[:117] + "..."
                    results.append(f"{doc_path}:{i}: {line_preview}")
        
        if not results:
            return "No matches found"
        
        # 結果が多すぎる場合は制限
        if len(results) > 100:
            total = len(results)
            results = results[:100]
            results.append(f"\n... and {total - 100} more matches")
        
        return "\n".join(results)
    
    def semantic_search(self, query: str, limit: int = 5) -> str:
        """意味的に関連する内容を検索"""
        if not self.client:
            return "Error: OpenAI API key not configured"
        
        if not self.embeddings_cache:
            return "Error: No embeddings available. Run 'python scripts/generate_metadata.py' first."
        
        try:
            # クエリのembeddingを取得
            query_embedding = self._get_embedding(query)
            
            # 各ドキュメントとの類似度を計算
            similarities = []
            for doc_path, doc_embedding in self.embeddings_cache.items():
                # embeddingがリストとして保存されているので、そのまま使用
                similarity = self._cosine_similarity(query_embedding, doc_embedding)
                similarities.append((doc_path, similarity))
            
            # 類似度でソート
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # 結果を構築
            results = []
            for doc_path, similarity in similarities[:limit]:
                description = self.docs_metadata.get(doc_path, "")
                result_line = f"{doc_path} (相似度: {similarity:.3f})"
                if description:
                    result_line += f" - {description}"
                results.append(result_line)
                
                # 関連する内容を一部抽出
                if doc_path in self.docs_content:
                    content = self.docs_content[doc_path]
                    preview = self._extract_preview(content, query)
                    if preview:
                        results.append(f"  → {preview}")
            
            return "\n\n".join(results)
            
        except Exception as e:
            return f"Error during semantic search: {e}"
    
    def get_doc_count(self) -> int:
        """読み込まれたドキュメント数を返す"""
        return len(self.docs_content)
    
    def _get_embedding(self, text: str) -> List[float]:
        """テキストのembeddingを取得"""
        text = text.replace("\n", " ")
        response = self.client.embeddings.create(
            input=[text],
            model="text-embedding-3-large"
        )
        return response.data[0].embedding
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """コサイン類似度を計算"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def _extract_preview(self, content: str, query: str, max_length: int = 200) -> str:
        """クエリに関連する部分を抽出"""
        lines = content.split('\n')
        query_words = query.lower().split()
        
        for line in lines:
            line_lower = line.lower()
            if any(word in line_lower for word in query_words) and len(line.strip()) > 20:
                preview = line.strip()
                if len(preview) > max_length:
                    preview = preview[:max_length - 3] + "..."
                return preview
        
        # キーワードが見つからない場合は最初の意味のある行を返す
        for line in lines:
            if len(line.strip()) > 20:
                preview = line.strip()
                if len(preview) > max_length:
                    preview = preview[:max_length - 3] + "..."
                return preview
        
        return ""