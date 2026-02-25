#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析有意义查询的结果，提取关键信息
"""
import json

def analyze_results():
    """分析结果并打印关键对比"""

    with open('meaningful_eval_results.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("="*100)
    print("有意义查询的评估分析")
    print("="*100)

    # 为每个查询分析Top-1结果的质量
    for idx, query_result in enumerate(data['queries'], 1):
        query = query_result['query']
        expected = query_result['expected_keywords']

        print(f"\n查询{idx}: {query}")
        print(f"预期关键词: {', '.join(expected)}")
        print("-" * 100)

        # 对比不同权重的Top-1结果
        for weight_result in query_result['weight_results']:
            bm25_w = weight_result['bm25_weight']
            top1 = weight_result['results'][0]

            content = top1['content'][:200].replace('\n', ' ')

            print(f"\nBM25:{bm25_w:.1f} Top-1:")
            print(f"  分数: 混合={top1['hybrid_score']:.3f} BM25={top1['bm25_score']:.3f} Vec={top1['vector_score']:.3f}")
            print(f"  内容: {content}...")

        print()

if __name__ == "__main__":
    analyze_results()
