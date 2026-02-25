#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动LLM评估：展示检索结果，由Claude直接评估质量
"""
import sys
sys.path.insert(0, '.')
from test_hybrid_search import *
from pathlib import Path
import json

def collect_evaluation_data(
    conv_file: Path,
    weight_candidates: list = [0.3, 0.5, 0.7, 0.9],
    queries_per_type: int = 3
):
    """
    收集评估数据：对不同权重配比进行检索，输出结果供人工评估
    """
    print("="*80)
    print(f"收集评估数据: {conv_file.name}")
    print("="*80)

    # 1. 加载向量库
    pkl_file = conv_file.parent / f"{conv_file.stem}_dual.pkl"

    if not pkl_file.exists():
        print(f"[INFO] 生成双向量...")
        from test_embedding_simple import VectorKnowledgeBasePipeline
        pipeline = VectorKnowledgeBasePipeline()
        pipeline.process_conversation(conv_file)
        pipeline.vector_store.save(str(pkl_file))

    print(f"[INFO] 加载向量库...")
    vector_store = HybridVectorStore(dimension=768)
    vector_store.load(str(pkl_file))
    vector_store.build_bm25_index()

    # 2. 生成测试查询
    print(f"[INFO] 生成测试查询...")
    from optimize_weights import generate_test_queries_from_conversation
    test_queries = generate_test_queries_from_conversation(conv_file)

    # 3. 选择代表性查询（每种类型选几个）
    selected_queries = []
    for qtype in ['keyword', 'semantic', 'mixed']:
        queries = test_queries.get(qtype, [])[:queries_per_type]
        for q in queries:
            selected_queries.append({'query': q, 'type': qtype})

    print(f"[INFO] 选择了 {len(selected_queries)} 个测试查询")

    # 4. 初始化embedding客户端
    embedding_client = GoogleEmbeddingClient()

    # 5. 对每个查询，测试所有权重配比
    evaluation_data = {
        'conversation': conv_file.stem,
        'queries': []
    }

    for idx, query_info in enumerate(selected_queries, 1):
        query = query_info['query']
        qtype = query_info['type']

        print(f"\n{'='*80}")
        print(f"[{idx}/{len(selected_queries)}] 查询: {query} (类型: {qtype})")
        print(f"{'='*80}")

        # 生成查询向量
        query_emb = embedding_client.get_embeddings([query])[0]

        query_data = {
            'query': query,
            'type': qtype,
            'weight_results': []
        }

        # 测试每种权重配比
        for bm25_w in weight_candidates:
            print(f"\n权重配比 BM25:{bm25_w:.1f} Vector:{1-bm25_w:.1f}")
            print("-" * 40)

            # 检索
            results = vector_store.hybrid_search(
                query_content_embedding=query_emb,
                query_text=query,
                top_k=3,
                bm25_weight=bm25_w,
                vector_weight=1-bm25_w
            )

            weight_result = {
                'bm25_weight': bm25_w,
                'vector_weight': 1 - bm25_w,
                'results': []
            }

            # 收集结果（不打印，避免编码问题）
            for rank, result in enumerate(results, 1):
                meta = result['metadata']
                content = meta.get('content_text', '')

                print(f"  Rank {rank}: 混合={result['score']:.3f} BM25={result['bm25_score']:.3f} Vec={result['vector_score']:.3f}")

                weight_result['results'].append({
                    'rank': rank,
                    'hybrid_score': result['score'],
                    'bm25_score': result['bm25_score'],
                    'vector_score': result['vector_score'],
                    'content': content,
                    'timestamp': meta['start_timestamp']
                })

            query_data['weight_results'].append(weight_result)

        evaluation_data['queries'].append(query_data)

    # 6. 保存数据
    output_file = f"eval_data_{conv_file.stem}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(evaluation_data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*80}")
    print(f"评估数据已保存到: {output_file}")
    print(f"{'='*80}")

    return evaluation_data

def main():
    # 先用一个对话做测试
    conv_file = Path("chat_data_filtered/alex_li/alex_li.json")

    if not conv_file.exists():
        print("[ERROR] 文件不存在")
        return

    # 收集评估数据
    data = collect_evaluation_data(
        conv_file,
        weight_candidates=[0.3, 0.5, 0.7, 0.9],
        queries_per_type=3  # 每种类型3个查询，共9个
    )

    print("\n" + "="*80)
    print("数据收集完成！")
    print("="*80)
    print(f"\n共收集了 {len(data['queries'])} 个查询的检索结果")
    print(f"每个查询测试了 4 种权重配比")
    print(f"每种配比返回 Top-3 结果")
    print(f"\n接下来可以查看 eval_data_alex_li.json 文件，")
    print(f"或者直接在这里分析结果的语义相关性质量。")

if __name__ == "__main__":
    load_dotenv()
    main()
