#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取Top-1结果对比，生成简洁的对比表
"""
import json

def extract_comparison():
    """提取关键对比信息"""

    with open('meaningful_eval_results.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 生成对比表
    comparison = []

    for idx, query_result in enumerate(data['queries'], 1):
        query = query_result['query']

        # 提取每个权重的Top-1内容（只取前100字符）
        tops = {}
        for weight_result in query_result['weight_results']:
            bm25_w = weight_result['bm25_weight']
            top1 = weight_result['results'][0]
            tops[bm25_w] = {
                'content': top1['content'][:150],
                'hybrid': top1['hybrid_score'],
                'bm25': top1['bm25_score'],
                'vec': top1['vector_score']
            }

        comparison.append({
            'id': idx,
            'query': query,
            'tops': tops
        })

    # 保存为JSON
    with open('top1_comparison.json', 'w', encoding='utf-8') as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)

    print(f"[OK] 已生成 top1_comparison.json")
    print(f"共 {len(comparison)} 个查询的Top-1对比")

if __name__ == "__main__":
    extract_comparison()
