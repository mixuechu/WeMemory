#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取关键信息用于手动评估
"""
import json

def extract_top1_results():
    """提取每个查询在不同权重下的Top-1结果"""

    with open('eval_data_alex_li.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    summary = {
        'conversation': data['conversation'],
        'evaluations': []
    }

    for idx, query_data in enumerate(data['queries'], 1):
        query = query_data['query']
        qtype = query_data['type']

        eval_item = {
            'query_id': idx,
            'query': query,
            'type': qtype,
            'weight_comparisons': []
        }

        # 提取每个权重的Top-1
        for weight_result in query_data['weight_results']:
            bm25_w = weight_result['bm25_weight']
            top1 = weight_result['results'][0]

            comp = {
                'bm25_weight': bm25_w,
                'vector_weight': weight_result['vector_weight'],
                'top1_content': top1['content'][:300],  # 只取前300字符
                'hybrid_score': top1['hybrid_score'],
                'bm25_score': top1['bm25_score'],
                'vector_score': top1['vector_score']
            }

            eval_item['weight_comparisons'].append(comp)

        summary['evaluations'].append(eval_item)

    # 保存精简版
    with open('eval_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 同时生成可读的文本报告
    with open('eval_summary.txt', 'w', encoding='utf-8') as f:
        f.write("="*100 + "\n")
        f.write("评估报告：alex_li对话 - 不同权重配比的Top-1检索结果对比\n")
        f.write("="*100 + "\n\n")

        for eval_item in summary['evaluations']:
            f.write(f"\n查询{eval_item['query_id']}: {eval_item['query']} (类型: {eval_item['type']})\n")
            f.write("-" * 100 + "\n")

            for comp in eval_item['weight_comparisons']:
                f.write(f"\nBM25:{comp['bm25_weight']:.1f} Vector:{comp['vector_weight']:.1f}\n")
                f.write(f"  分数: 混合={comp['hybrid_score']:.3f} BM25={comp['bm25_score']:.3f} Vec={comp['vector_score']:.3f}\n")
                f.write(f"  Top-1内容:\n")
                f.write(f"    {comp['top1_content']}\n")

            f.write("\n")

    print("[OK] 提取完成")
    print(f"  - eval_summary.json (精简的JSON)")
    print(f"  - eval_summary.txt (可读文本报告)")

if __name__ == "__main__":
    extract_top1_results()
