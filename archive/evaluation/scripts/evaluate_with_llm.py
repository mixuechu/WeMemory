#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用LLM评估检索质量：判断召回结果的语义相关性
"""
import sys
sys.path.insert(0, '.')
from test_hybrid_search import *
from pathlib import Path
import json
from collections import defaultdict
import anthropic
import os

def evaluate_result_relevance_with_llm(query: str, result_content: str, query_type: str) -> dict:
    """
    使用Claude API评估单个召回结果的语义相关性

    返回:
        {
            'relevance_score': 0-10的分数,
            'reasoning': 评分理由
        }
    """
    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    prompt = f"""你是一个专业的信息检索评估专家。请评估下面的检索结果与查询的语义相关性。

查询类型: {query_type}
查询: "{query}"

检索到的对话内容:
{result_content}

请从以下几个维度评估相关性（0-10分）：
1. 直接匹配：内容是否直接讨论查询主题
2. 语义相关：内容是否涉及相关概念、同义词、上下文
3. 隐含相关：内容是否有隐含的相关性（如情绪、场景、人物关系等）
4. 信息价值：这段对话对理解查询主题是否有帮助

评分标准：
10分：高度相关，直接回答查询或提供关键信息
7-9分：相关性强，包含重要的相关信息
4-6分：有一定相关性，但不是核心信息
1-3分：弱相关，仅有间接联系
0分：完全不相关

请以JSON格式返回：
{{
    "relevance_score": <0-10的整数>,
    "reasoning": "<简短的评分理由，说明为什么给这个分数>"
}}
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text

        # 提取JSON
        import re
        json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result
        else:
            # 备用：手动解析
            return {
                'relevance_score': 5,
                'reasoning': '无法解析LLM响应'
            }

    except Exception as e:
        print(f"[ERROR] LLM评估失败: {e}")
        return {
            'relevance_score': 0,
            'reasoning': f'评估失败: {str(e)}'
        }

def evaluate_weight_with_llm(
    vector_store: HybridVectorStore,
    embedding_client,
    test_queries: dict,
    bm25_weight: float,
    use_llm: bool = True
) -> dict:
    """使用LLM评估单个权重配置的检索质量"""

    print(f"\n{'='*80}")
    print(f"评估权重配比 BM25:{bm25_weight:.1f} Vector:{1-bm25_weight:.1f}")
    print(f"{'='*80}")

    results = {
        'bm25_weight': bm25_weight,
        'vector_weight': 1 - bm25_weight,
        'queries': [],
        'metrics': {}
    }

    all_relevance_scores = []
    all_top1_scores = []
    all_top3_avg_scores = []

    query_count = 0

    for query_type in ['keyword', 'semantic', 'mixed']:
        for query in test_queries.get(query_type, []):
            query_count += 1
            print(f"\n[{query_count}] 查询: {query} (类型: {query_type})")

            # 生成查询向量
            query_emb = embedding_client.get_embeddings([query])[0]

            # 混合检索
            search_results = vector_store.hybrid_search(
                query_content_embedding=query_emb,
                query_text=query,
                top_k=5,
                bm25_weight=bm25_weight,
                vector_weight=1-bm25_weight
            )

            if not search_results:
                continue

            # 评估Top-3结果
            query_result = {
                'query': query,
                'type': query_type,
                'results': []
            }

            for rank, result in enumerate(search_results[:3], 1):
                content = result['metadata'].get('content_text', '')[:500]

                # 使用LLM评估语义相关性
                if use_llm:
                    llm_eval = evaluate_result_relevance_with_llm(query, content, query_type)
                    relevance_score = llm_eval['relevance_score']
                    reasoning = llm_eval['reasoning']
                else:
                    # 不使用LLM时，用混合分数代替
                    relevance_score = result['score'] * 10
                    reasoning = "未使用LLM评估"

                query_result['results'].append({
                    'rank': rank,
                    'hybrid_score': result['score'],
                    'bm25_score': result['bm25_score'],
                    'vector_score': result['vector_score'],
                    'relevance_score': relevance_score,
                    'reasoning': reasoning,
                    'content_preview': content[:200]
                })

                if rank == 1:
                    all_top1_scores.append(relevance_score)

                all_relevance_scores.append(relevance_score)

                print(f"  Rank {rank}: 语义相关性={relevance_score}/10, 混合分={result['score']:.3f}")
                print(f"    理由: {reasoning}")

            # 计算Top3平均分
            top3_scores = [r['relevance_score'] for r in query_result['results'][:3]]
            if top3_scores:
                all_top3_avg_scores.append(sum(top3_scores) / len(top3_scores))

            results['queries'].append(query_result)

    # 计算指标
    if all_relevance_scores:
        results['metrics'] = {
            'avg_relevance_all': sum(all_relevance_scores) / len(all_relevance_scores),
            'avg_relevance_top1': sum(all_top1_scores) / len(all_top1_scores) if all_top1_scores else 0,
            'avg_relevance_top3': sum(all_top3_avg_scores) / len(all_top3_avg_scores) if all_top3_avg_scores else 0,
            'total_evaluations': len(all_relevance_scores)
        }

        print(f"\n{'='*40}")
        print(f"指标汇总:")
        print(f"  平均语义相关性(所有): {results['metrics']['avg_relevance_all']:.2f}/10")
        print(f"  平均语义相关性(Top1): {results['metrics']['avg_relevance_top1']:.2f}/10")
        print(f"  平均语义相关性(Top3): {results['metrics']['avg_relevance_top3']:.2f}/10")
        print(f"  评估数量: {results['metrics']['total_evaluations']}")

    return results

def optimize_weights_with_llm(
    conv_files: list,
    weight_candidates: list = [0.3, 0.5, 0.7, 0.9],
    output_file: str = "llm_evaluation_results.json",
    use_llm: bool = True
):
    """使用LLM评估找到最佳权重配比"""

    print("="*80)
    print("基于LLM的语义相关性评估 - 权重优化")
    print("="*80)

    # 初始化
    embedding_client = GoogleEmbeddingClient()

    all_results = {
        'conversations': [],
        'weight_comparison': defaultdict(lambda: {
            'total_relevance': 0,
            'total_top1': 0,
            'total_top3': 0,
            'count': 0
        })
    }

    # 为每个对话测试
    for conv_file in conv_files:
        print(f"\n{'='*80}")
        print(f"处理对话: {conv_file.name}")
        print(f"{'='*80}")

        # 1. 加载或生成向量库
        pkl_file = conv_file.parent / f"{conv_file.stem}_dual.pkl"

        if not pkl_file.exists():
            print(f"[INFO] 生成双向量...")
            from test_embedding_simple import VectorKnowledgeBasePipeline
            pipeline = VectorKnowledgeBasePipeline()
            pipeline.process_conversation(conv_file)
            pipeline.vector_store.save(str(pkl_file))

        # 2. 加载向量库
        print(f"[INFO] 加载向量库...")
        vector_store = HybridVectorStore(dimension=768)
        vector_store.load(str(pkl_file))
        vector_store.build_bm25_index()

        # 3. 生成测试查询
        print(f"[INFO] 生成测试查询...")
        from optimize_weights import generate_test_queries_from_conversation
        test_queries = generate_test_queries_from_conversation(conv_file)

        print(f"[INFO] 测试查询数量:")
        print(f"  - 关键词: {len(test_queries['keyword'])}")
        print(f"  - 语义: {len(test_queries['semantic'])}")
        print(f"  - 混合: {len(test_queries['mixed'])}")

        # 4. 测试不同权重
        conv_results = {
            'conversation': test_queries['conversation'],
            'file': str(conv_file),
            'weight_tests': []
        }

        for bm25_w in weight_candidates:
            test_result = evaluate_weight_with_llm(
                vector_store, embedding_client, test_queries, bm25_w, use_llm
            )

            conv_results['weight_tests'].append(test_result)

            # 累积统计
            metrics = test_result['metrics']
            if metrics:
                all_results['weight_comparison'][bm25_w]['total_relevance'] += metrics['avg_relevance_all']
                all_results['weight_comparison'][bm25_w]['total_top1'] += metrics['avg_relevance_top1']
                all_results['weight_comparison'][bm25_w]['total_top3'] += metrics['avg_relevance_top3']
                all_results['weight_comparison'][bm25_w]['count'] += 1

        all_results['conversations'].append(conv_results)

    # 5. 汇总最佳权重
    print(f"\n{'='*80}")
    print("权重优化结果汇总（基于LLM语义相关性评估）")
    print(f"{'='*80}")

    best_weight = None
    best_score = -1

    print(f"\n{'权重配比':<20} {'平均相关性(全部)':<20} {'平均相关性(Top1)':<20} {'平均相关性(Top3)':<20}")
    print("-" * 80)

    for bm25_w in sorted(weight_candidates):
        stats = all_results['weight_comparison'][bm25_w]
        if stats['count'] > 0:
            avg_all = stats['total_relevance'] / stats['count']
            avg_top1 = stats['total_top1'] / stats['count']
            avg_top3 = stats['total_top3'] / stats['count']

            print(f"BM25:{bm25_w:.1f} Vec:{1-bm25_w:.1f}    {avg_all:.2f}/10              {avg_top1:.2f}/10              {avg_top3:.2f}/10")

            # 使用Top1平均分作为主要指标
            if avg_top1 > best_score:
                best_score = avg_top1
                best_weight = bm25_w

    all_results['best_weight'] = {
        'bm25': best_weight,
        'vector': 1 - best_weight,
        'avg_relevance_top1': best_score
    }

    print(f"\n{'='*80}")
    print(f"🎯 最佳权重配比: BM25:{best_weight:.1f} Vector:{1-best_weight:.1f}")
    print(f"   平均语义相关性(Top1): {best_score:.2f}/10")
    print(f"{'='*80}")

    # 6. 保存结果
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n[INFO] 详细结果已保存到: {output_file}")

    return all_results

def main():
    """主函数"""

    # 检查API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("[ERROR] 请设置 ANTHROPIC_API_KEY 环境变量")
        print("[INFO] 可以在 .env 文件中添加: ANTHROPIC_API_KEY=your_key")
        return

    # 选择测试对话（与之前相同）
    test_conversations = [
        Path("chat_data_filtered/alex_li/alex_li.json"),
        Path("chat_data_filtered/周仕达/周仕达.json"),
        Path("chat_data_filtered/黄心怡/黄心怡.json"),
        Path("chat_data_filtered/阡陌/阡陌.json"),
    ]

    # 检查文件
    valid_conversations = [c for c in test_conversations if c.exists()]

    if not valid_conversations:
        print("[ERROR] 未找到测试对话文件")
        return

    print(f"[INFO] 将测试 {len(valid_conversations)} 个对话")
    for conv in valid_conversations:
        print(f"  - {conv.parent.name}")

    # 权重候选（减少到4个以节省API调用）
    weight_candidates = [0.3, 0.5, 0.7, 0.9]

    print(f"\n[INFO] 将测试 {len(weight_candidates)} 种权重配比")
    print(f"[INFO] 使用Claude API进行语义相关性评估")
    print(f"[WARNING] 这将消耗一定的API配额，预计评估次数: {len(valid_conversations)} * {len(weight_candidates)} * ~25查询 * 3结果 = ~{len(valid_conversations) * len(weight_candidates) * 25 * 3} 次API调用")

    # 运行优化
    results = optimize_weights_with_llm(
        valid_conversations,
        weight_candidates=weight_candidates,
        use_llm=True
    )

if __name__ == "__main__":
    load_dotenv()
    main()
