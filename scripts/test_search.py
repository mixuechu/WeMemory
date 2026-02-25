#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试向量库搜索功能
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
from dotenv import load_dotenv
from retrieval import HybridVectorStore
from embedding import GoogleEmbeddingClient

# 加载环境变量
load_dotenv()


def test_vector_store(vector_file: str = "vector_stores/conversations.pkl"):
    """
    测试向量库的完整性和搜索功能

    Args:
        vector_file: 向量库文件路径
    """
    print("=" * 80)
    print("测试向量库")
    print("=" * 80)

    vector_path = Path(vector_file)
    if not vector_path.exists():
        print(f"[ERROR] 向量库文件不存在: {vector_file}")
        return

    # 1. 加载向量库
    print(f"\n[1] 加载向量库: {vector_file}")
    vs = HybridVectorStore(dimension=768, use_faiss=True)
    vs.load(str(vector_path))
    print(f"[OK] 已加载 {len(vs.metadata):,} 个sessions")

    # 2. 检查数据完整性
    print(f"\n[2] 检查数据完整性...")
    zero_content = sum(1 for emb in vs.content_embeddings if np.all(emb == 0))
    zero_context = sum(1 for emb in vs.context_embeddings if np.all(emb == 0))

    print(f"  零Content向量: {zero_content} ({zero_content/len(vs.metadata)*100:.2f}%)")
    print(f"  零Context向量: {zero_context} ({zero_context/len(vs.metadata)*100:.2f}%)")

    if zero_content == 0:
        print(f"  [OK] 完美！所有sessions都有有效的content向量")
    else:
        print(f"  [WARNING] 存在 {zero_content} 个零向量")

    # 3. 构建索引
    print(f"\n[3] 构建搜索索引...")
    print(f"  构建BM25索引...")
    vs.build_bm25_index()
    print(f"  构建FAISS索引...")
    vs.build_faiss_index()
    print(f"  [OK] 索引构建完成")

    # 4. 测试搜索
    print(f"\n[4] 测试搜索功能...")

    # 初始化embedding客户端
    client = GoogleEmbeddingClient()

    test_queries = [
        "AI相关的讨论",
        "开会时间安排",
        "项目进展"
    ]

    for query in test_queries:
        print(f"\n  查询: '{query}'")

        # 生成查询向量
        query_embedding = client.get_embeddings([query])[0]

        # 混合搜索
        results = vs.hybrid_search(
            query_content_embedding=query_embedding,
            query_text=query,
            top_k=3
        )

        if len(results) > 0:
            print(f"    找到 {len(results)} 个结果:")
            for i, result in enumerate(results[:3], 1):
                meta = result['metadata']
                print(f"      {i}. 对话: {meta['conversation_name']}")
                print(f"         分数: {result['score']:.3f} (BM25:{result['bm25_score']:.3f}, Vector:{result['vector_score']:.3f})")
                print(f"         内容: {meta['content_text'][:80]}...")
        else:
            print(f"    [WARNING] 没有找到结果")

    # 5. 统计
    print(f"\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"总sessions: {len(vs.metadata):,}")
    print(f"有效sessions: {len(vs.metadata) - zero_content:,} ({(len(vs.metadata) - zero_content)/len(vs.metadata)*100:.1f}%)")
    print(f"FAISS索引: {'✓' if vs.faiss_built else '✗'}")
    print(f"BM25索引: {'✓' if vs.bm25_index is not None else '✗'}")

    if zero_content == 0 and len(results) > 0:
        print(f"\n[SUCCESS] 测试通过！向量库完全正常！")
    else:
        print(f"\n[WARNING] 存在问题，需要检查")

    print("=" * 80)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="测试向量库搜索功能")
    parser.add_argument(
        "--vector-file",
        type=str,
        default="vector_stores/conversations.pkl",
        help="向量库文件路径（默认: vector_stores/conversations.pkl）"
    )

    args = parser.parse_args()
    test_vector_store(args.vector_file)


if __name__ == "__main__":
    main()
