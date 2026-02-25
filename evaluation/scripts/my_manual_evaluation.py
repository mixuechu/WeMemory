#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
我（Claude）手动评估每个权重配比的语义相关性质量
"""
import json

def evaluate_semantic_relevance():
    """
    我会查看eval_data_alex_li.json中的所有查询和结果，
    然后给出基于语义相关性的评分
    """

    with open('eval_data_alex_li.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("="*100)
    print("Claude手动语义评估报告")
    print("="*100)

    # 手动评分结果
    # 格式：{查询索引: {BM25权重: 评分(0-10)}}
    manual_scores = {}

    for idx, query_data in enumerate(data['queries']):
        query = query_data['query']
        qtype = query_data['type']

        print(f"\n查询{idx+1}: {query} (类型: {qtype})")
        print("-" * 100)

        # 显示每个权重配比的Top-1结果
        for weight_result in query_data['weight_results']:
            bm25_w = weight_result['bm25_weight']
            top1 = weight_result['results'][0]

            print(f"\nBM25:{bm25_w:.1f} Top-1:")
            print(f"  分数: 混合={top1['hybrid_score']:.3f} BM25={top1['bm25_score']:.3f} Vec={top1['vector_score']:.3f}")
            print(f"  内容: {top1['content'][:150]}...")

    # 现在我会基于以上内容给出手动评分
    # 评分标准：
    # 10分：高度相关，直接回答查询
    # 7-9分：相关性强
    # 4-6分：有一定相关性
    # 1-3分：弱相关
    # 0分：不相关

    print("\n\n" + "="*100)
    print("手动评分（基于语义相关性）")
    print("="*100)

    # 我会在下面给出每个查询的评分

    # 查询1: "可以" (keyword)
    # BM25:0.3 Top1: "可以的\n你那边是不是有一个新的HTML了" - 相关性：7分（直接匹配）
    # BM25:0.5 Top1: "可以的\n你那边是不是有一个新的HTML了" - 相关性：7分（同上）
    # BM25:0.7 Top1: "你接不接私活...可以随时把信息发给我" - 相关性：6分（有"可以"，但不是主要语义）
    # BM25:0.9 Top1: "你接不接私活...可以随时把信息发给我" - 相关性：6分（同上）
    # 结论：0.3和0.5更好

    manual_scores[1] = {
        0.3: 7,
        0.5: 7,
        0.7: 6,
        0.9: 6
    }

    # 由于我无法在代码中看到所有查询的完整内容，
    # 我需要完整读取JSON文件来进行全面评估

    # 返回现在已评估的部分
    return manual_scores

if __name__ == "__main__":
    scores = evaluate_semantic_relevance()
    print("\n当前评分:")
    for query_idx, weight_scores in scores.items():
        print(f"\n查询{query_idx}:")
        for bm25_w, score in weight_scores.items():
            print(f"  BM25:{bm25_w:.1f} => {score}/10")
