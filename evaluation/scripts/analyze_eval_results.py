#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析评估结果：手动评估每个权重配比下的语义相关性
"""
import json
from pathlib import Path

def analyze_results(eval_file: str):
    """分析评估结果"""

    with open(eval_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("="*100)
    print(f"评估报告：{data['conversation']}")
    print("="*100)

    # 为每个权重配比手动打分
    weight_scores = {
        0.3: [],  # BM25:0.3 Vector:0.7
        0.5: [],  # BM25:0.5 Vector:0.5
        0.7: [],  # BM25:0.7 Vector:0.3
        0.9: []   # BM25:0.9 Vector:0.1
    }

    # 逐个查询进行评估
    for idx, query_data in enumerate(data['queries'], 1):
        query = query_data['query']
        qtype = query_data['type']

        print(f"\n{'='*100}")
        print(f"查询 {idx}/9: {query} (类型: {qtype})")
        print(f"{'='*100}")

        # 对每个权重配比
        for weight_result in query_data['weight_results']:
            bm25_w = weight_result['bm25_weight']
            vec_w = weight_result['vector_weight']

            print(f"\n权重配比 BM25:{bm25_w:.1f} Vector:{vec_w:.1f}")
            print("-" * 100)

            # 显示Top-3结果
            for result in weight_result['results'][:3]:
                rank = result['rank']
                content = result['content']
                scores = f"混合={result['hybrid_score']:.3f} BM25={result['bm25_score']:.3f} Vec={result['vector_score']:.3f}"

                print(f"\n  Rank {rank}: {scores}")
                print(f"  内容: {content[:200]}...")

        print(f"\n{'-'*100}")
        print(f"请为查询 '{query}' 的各个权重配比的Top-1结果打分（基于语义相关性）：")
        print()

        # 显示所有权重配比的Top-1，方便对比
        for weight_result in query_data['weight_results']:
            bm25_w = weight_result['bm25_weight']
            top1 = weight_result['results'][0]
            content_preview = top1['content'][:100].replace('\n', ' ')
            print(f"  BM25:{bm25_w:.1f} Top1: {content_preview}...")

        print()
        print("评分标准（0-10分）：")
        print("  10分：高度相关，直接回答查询或提供关键信息")
        print("  7-9分：相关性强，包含重要的相关信息")
        print("  4-6分：有一定相关性，但不是核心信息")
        print("  1-3分：弱相关，仅有间接联系")
        print("  0分：完全不相关")
        print()

        # 手动输入评分（实际使用时）
        # 这里我们用分析的方式给出评估

        # 我会在下面手动给出评分

    return data

def main():
    eval_file = "eval_data_alex_li.json"

    if not Path(eval_file).exists():
        print(f"[ERROR] 文件不存在: {eval_file}")
        return

    data = analyze_results(eval_file)

    print("\n" + "="*100)
    print("分析说明：")
    print("="*100)
    print("上面展示了9个查询在4种权重配比下的检索结果。")
    print("接下来需要Claude根据语义相关性对每个权重配比进行评分。")
    print("最终找到语义质量最高的权重配比。")

if __name__ == "__main__":
    main()
