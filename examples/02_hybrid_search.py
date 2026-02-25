#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例2：混合检索（BM25 + 向量）

功能：
1. 加载已生成的向量库
2. 构建BM25索引
3. 执行混合检索
4. 展示检索结果
"""
import sys
sys.path.insert(0, '.')

from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 导入模块
from retrieval import HybridVectorStore
from embedding import GoogleEmbeddingClient

# 加载环境变量
load_dotenv()


def hybrid_search_demo(vector_store_file: Path):
    """
    混合检索演示

    Args:
        vector_store_file: 向量库文件路径
    """
    print("="*80)
    print("混合检索演示 - BM25:0.5 + Vector:0.5")
    print("="*80)

    # 1. 加载向量库
    print("\n[步骤1] 加载向量库...")
    store = HybridVectorStore(dimension=768)
    store.load(str(vector_store_file))

    # 2. 构建BM25索引
    print("\n[步骤2] 构建BM25索引...")
    store.build_bm25_index()

    # 3. 初始化embedding客户端
    print("\n[步骤3] 初始化embedding客户端...")
    client = GoogleEmbeddingClient()

    # 4. 测试查询
    test_queries = [
        "我们聊过AI相关的话题吗",
        "关于AWS权限的讨论",
        "alex让我不要做前端",
        "关于在国内开外包公司的想法",
    ]

    print("\n"+"="*80)
    print("开始检索")
    print("="*80)

    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"查询: {query}")
        print(f"{'='*80}")

        # 生成查询向量
        query_embedding = client.get_embeddings([query])[0]

        # 混合检索
        results = store.hybrid_search(
            query_content_embedding=query_embedding,
            query_text=query,
            top_k=3,
            bm25_weight=0.5,  # 推荐配比
            vector_weight=0.5
        )

        # 展示结果
        print(f"\n找到 {len(results)} 条结果:\n")

        for i, result in enumerate(results, 1):
            meta = result['metadata']
            print(f"[{i}] 混合分: {result['score']:.3f}")
            print(f"    - BM25分: {result['bm25_score']:.3f}")
            print(f"    - 向量分: {result['vector_score']:.3f}")
            print(f"    时间: {datetime.fromtimestamp(meta['start_timestamp']).strftime('%Y-%m-%d %H:%M')}")
            print(f"    对话预览:")
            content = meta.get('content_text', '')[:150]
            print(f"      {content}...")
            print()

    print("\n"+"="*80)
    print("检索完成！")
    print("="*80)


if __name__ == "__main__":
    # 使用已生成的向量库
    vector_store_file = Path("vector_stores/alex_li_dual.pkl")

    if not vector_store_file.exists():
        print(f"[ERROR] 向量库不存在: {vector_store_file}")
        print("请先运行 examples/01_generate_embeddings.py 生成向量库")
        sys.exit(1)

    # 运行混合检索演示
    hybrid_search_demo(vector_store_file)
