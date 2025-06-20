#!/usr/bin/env python3
"""
メタデータとembeddings生成スクリプト
docs/内のすべてのドキュメントに対して1行説明とembeddingsを生成します
"""

import os
import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import numpy as np

load_dotenv()


def generate_description(doc_path: str, content: str, client: OpenAI) -> str:
    """ドキュメントの1行説明を生成"""
    try:
        # ファイルタイプに応じた説明
        if doc_path.endswith('.json'):
            return "JSONデータ定義"
        elif doc_path.endswith('.ts'):
            return "TypeScript型定義"
        elif doc_path.endswith(('.yml', '.yaml')):
            return "YAML設定ファイル"
        
        # 内容から説明を生成
        content_preview = content[:3000]
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "MCPドキュメントの内容から、技術的に正確で簡潔な1行の日本語説明を生成してください。"
                },
                {
                    "role": "user",
                    "content": f"ファイル: {doc_path}\n\n内容:\n{content_preview}"
                }
            ],
            temperature=0.3,
            max_tokens=100
        )
        
        return response.choices[0].message.content.strip().strip('"\'。.')
        
    except Exception as e:
        print(f"Error generating description for {doc_path}: {e}")
        return "MCPドキュメント"


def generate_embedding(content: str, client: OpenAI) -> list:
    """テキストのembeddingを生成"""
    # 最大50000文字まで
    text = content[:50000].replace("\n", " ")
    response = client.embeddings.create(
        input=[text],
        model="text-embedding-3-large"
    )
    return response.data[0].embedding


def main():
    # OpenAI クライアント初期化
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    client = OpenAI(api_key=api_key)
    
    # パス設定
    base_dir = Path(__file__).parent.parent
    docs_dir = base_dir / "docs"
    metadata_file = base_dir / "docs_metadata.json"
    embeddings_file = base_dir / "docs_embeddings.json"
    
    # 既存のデータを読み込み
    metadata = {}
    embeddings = {}
    
    if metadata_file.exists():
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    
    if embeddings_file.exists():
        with open(embeddings_file, 'r', encoding='utf-8') as f:
            embeddings = json.load(f)
    
    # docs内のすべてのテキストファイルを処理
    metadata_updated = False
    embeddings_updated = False
    
    for file_path in docs_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix in ['.mdx', '.md', '.txt', '.json', '.ts', '.yml', '.yaml']:
            doc_path = str(file_path.relative_to(base_dir)).replace('\\', '/')
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # メタデータ生成（存在しない場合のみ）
                if doc_path not in metadata:
                    description = generate_description(doc_path, content, client)
                    metadata[doc_path] = description
                    metadata_updated = True
                    print(f"Generated metadata: {doc_path} - {description}")
                
                # Embeddings生成（存在しない場合のみ）
                if doc_path not in embeddings and len(content.strip()) > 0:
                    print(f"Generating embedding: {doc_path}")
                    embedding = generate_embedding(content, client)
                    # リストをそのまま保存（JSONで保存可能）
                    embeddings[doc_path] = embedding
                    embeddings_updated = True
                    print(f"Generated embedding: {doc_path} (dim: {len(embedding)})")
                
            except Exception as e:
                print(f"Error processing {doc_path}: {e}")
    
    # メタデータを保存
    if metadata_updated:
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"\nMetadata saved to {metadata_file}")
    
    # Embeddingsを保存
    if embeddings_updated:
        with open(embeddings_file, 'w', encoding='utf-8') as f:
            json.dump(embeddings, f, ensure_ascii=False)
        print(f"Embeddings saved to {embeddings_file}")
    
    if not metadata_updated and not embeddings_updated:
        print("\nNo updates needed")
    
    print(f"\nTotal documents: {len(metadata)}")
    print(f"Total embeddings: {len(embeddings)}")


if __name__ == "__main__":
    main()