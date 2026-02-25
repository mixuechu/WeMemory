#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试同义词/近义词查询 - 这是向量检索的核心优势
"""
import sys
sys.path.insert(0, '.')
from test_hybrid_search import *
from pathlib import Path
import json

def test_synonym_queries():
    """测试同义词查询的检索效果"""

    print("="*100)
    print("同义词/近义词查询测试 - 检验向量检索的语义理解能力")
    print("="*100)

    # 1. 加载同义词测试查询
    with open('synonym_test_queries.json', 'r', encoding='utf-8') as f:
        query_data = json.load(f)

    test_queries = query_data['synonym_tests']

    # 2. 加载向量库
    conv_file = Path("chat_data_filtered/alex_li/alex_li.json")
    pkl_file = conv_file.parent / f"{conv_file.stem}_dual.pkl"

    if not pkl_file.exists():
        print(f"[ERROR] 向量库不存在: {pkl_file}")
        return

    print(f"[INFO] 加载向量库...")
    vector_store = HybridVectorStore(dimension=768)
    vector_store.load(str(pkl_file))
    vector_store.build_bm25_index()

    # 3. 初始化embedding客户端
    embedding_client = GoogleEmbeddingClient()

    # 4. 权重候选（关注0.3和0.7的对比）
    weight_candidates = [0.3, 0.5, 0.7, 0.9]

    # 5. 测试结果
    results = {
        'conversation': 'alex_li',
        'test_type': 'synonym_semantic',
        'queries': []
    }

    for idx, query_info in enumerate(test_queries, 1):
        query = query_info['query']
        synonyms = query_info['synonyms_in_data']
        qtype = query_info['type']
        expected = query_info['expected']

        print(f"\n{'='*100}")
        print(f"[{idx}/{len(test_queries)}] 查询: {query}")
        print(f"类型: {qtype}")
        print(f"数据中的同义词: {', '.join(synonyms)}")
        print(f"期望: {expected}")
        print(f"{'='*100}")

        # 生成查询向量
        query_emb = embedding_client.get_embeddings([query])[0]

        query_result = {
            'query': query,
            'type': qtype,
            'synonyms_in_data': synonyms,
            'expected': expected,
            'weight_results': []
        }

        # 测试每个权重配比
        for bm25_w in weight_candidates:
            print(f"\n权重配比 BM25:{bm25_w:.1f} Vector:{1-bm25_w:.1f}")
            print("-" * 100)

            # 检索
            search_results = vector_store.hybrid_search(
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

            # 展示Top-3结果
            for rank, result in enumerate(search_results, 1):
                meta = result['metadata']
                content = meta.get('content_text', '')

                print(f"  Rank {rank}: 混合={result['score']:.3f} BM25={result['bm25_score']:.3f} Vec={result['vector_score']:.3f}")

                weight_result['results'].append({
                    'rank': rank,
                    'hybrid_score': result['score'],
                    'bm25_score': result['bm25_score'],
                    'vector_score': result['vector_score'],
                    'content': content[:500],
                    'timestamp': meta['start_timestamp']
                })

            query_result['weight_results'].append(weight_result)

        results['queries'].append(query_result)

    # 6. 保存结果
    output_file = 'synonym_test_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*100}")
    print(f"结果已保存到: {output_file}")
    print(f"{'='*100}")

    # 7. 生成可读报告
    with open('synonym_test_summary.txt', 'w', encoding='utf-8') as f:
        f.write("="*100 + "\n")
        f.write("同义词/近义词查询测试报告\n")
        f.write("="*100 + "\n\n")

        for query_result in results['queries']:
            f.write(f"\n查询: {query_result['query']}\n")
            f.write(f"类型: {query_result['type']}\n")
            f.write(f"数据中的同义词: {', '.join(query_result['synonyms_in_data'])}\n")
            f.write(f"期望结果: {query_result['expected']}\n")
            f.write("-" * 100 + "\n\n")

            for weight_result in query_result['weight_results']:
                bm25_w = weight_result['bm25_weight']
                f.write(f"权重配比 BM25:{bm25_w:.1f} Vector:{1-bm25_w:.1f}\n\n")

                for result in weight_result['results']:
                    rank = result['rank']
                    f.write(f"  Rank {rank}: 混合={result['hybrid_score']:.3f} BM25={result['bm25_score']:.3f} Vec={result['vector_score']:.3f}\n")
                    f.write(f"  内容: {result['content'][:300]}\n\n")

                f.write("\n")

            f.write("="*100 + "\n\n")

    print(f"可读报告已保存到: synonym_test_summary.txt")

    return results

def main():
    load_dotenv()
    test_synonym_queries()

if __name__ == "__main__":
    main()
