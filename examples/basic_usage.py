#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基本使用示例 - 微信记忆系统

展示如何：
1. 加载向量库
2. 执行搜索
3. 过滤结果
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from retrieval import HybridVectorStore
from embedding import GoogleEmbeddingClient

# 加载环境变量
load_dotenv()


def basic_search_example():
    """基本搜索示例"""
    print("=" * 70)
    print("示例 1: 基本搜索")
    print("=" * 70)

    # 1. 加载向量库
    print("\n[1] 加载向量库...")
    vs = HybridVectorStore(dimension=768, use_faiss=True)
    vs.load("vector_stores/conversations.pkl")
    print(f"    已加载 {len(vs.metadata):,} 个会话片段")

    # 2. 构建索引（首次使用需要）
    print("\n[2] 构建搜索索引...")
    vs.build_bm25_index()
    vs.build_faiss_index()
    print("    索引构建完成")

    # 3. 初始化 embedding 客户端
    print("\n[3] 初始化 Embedding 客户端...")
    client = GoogleEmbeddingClient()

    # 4. 执行搜索
    print("\n[4] 执行搜索...")
    query = "讨论 AI 项目的对话"

    # 生成查询向量
    query_embedding = client.get_embeddings([query])[0]

    # 搜索
    results = vs.hybrid_search(
        query_content_embedding=query_embedding,
        query_text=query,
        top_k=5
    )

    # 5. 显示结果
    print(f"\n[5] 搜索结果（查询: '{query}'）:\n")
    for i, result in enumerate(results, 1):
        meta = result['metadata']
        print(f"  {i}. 对话: {meta['conversation_name']}")
        print(f"     分数: {result['score']:.3f}")
        print(f"     时间: {meta.get('start_timestamp', 'N/A')}")
        print(f"     内容: {meta['content_text'][:100]}...")
        print()


def advanced_search_example():
    """高级搜索示例 - 带过滤"""
    print("=" * 70)
    print("示例 2: 高级搜索（带时间和参与者过滤）")
    print("=" * 70)

    # 加载向量库
    vs = HybridVectorStore(dimension=768, use_faiss=True)
    vs.load("vector_stores/conversations.pkl")
    vs.build_bm25_index()
    vs.build_faiss_index()

    # 初始化客户端
    client = GoogleEmbeddingClient()

    # 搜索查询
    query = "项目进展"
    query_embedding = client.get_embeddings([query])[0]

    # 定义过滤器
    from datetime import datetime
    filters = {
        'time_range': (
            datetime(2024, 1, 1).timestamp(),
            datetime(2024, 12, 31).timestamp()
        ),
        # 'participants': ['Alice', 'Bob']  # 可选：按参与者过滤
    }

    # 执行搜索
    results = vs.hybrid_search(
        query_content_embedding=query_embedding,
        query_text=query,
        top_k=3,
        filters=filters
    )

    # 显示结果
    print(f"\n搜索结果（查询: '{query}'，时间: 2024年）:\n")
    for i, result in enumerate(results, 1):
        meta = result['metadata']
        print(f"  {i}. {meta['conversation_name']}")
        print(f"     综合分数: {result['score']:.3f}")
        print(f"     - BM25: {result['bm25_score']:.3f}")
        print(f"     - 向量: {result['vector_score']:.3f}")
        print()


def custom_weights_example():
    """自定义权重示例"""
    print("=" * 70)
    print("示例 3: 自定义搜索权重")
    print("=" * 70)

    vs = HybridVectorStore(dimension=768, use_faiss=True)
    vs.load("vector_stores/conversations.pkl")
    vs.build_bm25_index()
    vs.build_faiss_index()

    client = GoogleEmbeddingClient()
    query = "开会时间"
    query_embedding = client.get_embeddings([query])[0]

    # 对比不同权重配置
    weight_configs = [
        {"name": "关键词优先", "bm25": 0.8, "vector": 0.2},
        {"name": "均衡模式", "bm25": 0.5, "vector": 0.5},
        {"name": "语义优先", "bm25": 0.2, "vector": 0.8},
    ]

    for config in weight_configs:
        print(f"\n[{config['name']}] BM25:{config['bm25']}, Vector:{config['vector']}")

        results = vs.hybrid_search(
            query_content_embedding=query_embedding,
            query_text=query,
            top_k=3,
            bm25_weight=config['bm25'],
            vector_weight=config['vector']
        )

        for i, r in enumerate(results, 1):
            print(f"  {i}. {r['metadata']['conversation_name'][:30]}... (分数: {r['score']:.3f})")


if __name__ == "__main__":
    # 运行示例
    try:
        basic_search_example()
        print("\n" + "=" * 70 + "\n")

        advanced_search_example()
        print("\n" + "=" * 70 + "\n")

        custom_weights_example()

    except FileNotFoundError:
        print("\n[ERROR] 向量库文件不存在")
        print("请先运行: python scripts/generate_embeddings.py")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
