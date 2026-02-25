#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
权重优化：找到BM25和向量的最佳配比
"""
import sys
sys.path.insert(0, '.')
from test_hybrid_search import *
import json
from pathlib import Path
from collections import defaultdict

def generate_test_queries_from_conversation(conv_file: Path, sample_size: int = 20):
    """
    从对话中自动生成测试查询

    策略：
    1. 关键词查询：提取高频词作为查询
    2. 实体查询：提取人名、地点等
    3. 短语查询：提取2-3个词的短语
    """
    with open(conv_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    messages = data['messages']
    conv_name = data['meta']['name']

    # 统计词频
    from collections import Counter
    import jieba

    word_counter = Counter()
    phrases = []

    for msg in messages:
        content = msg.get('content', '')
        if not content or len(content) < 2:
            continue

        # 分词并统计
        words = [w for w in jieba.cut(content) if len(w) > 1]
        word_counter.update(words)

        # 提取短语（2-4个字）
        for i in range(len(content) - 1):
            phrase = content[i:i+2]
            if len(phrase) == 2 and phrase.strip():
                phrases.append(phrase)

    # 生成测试查询
    queries = {
        'keyword': [],  # 关键词查询
        'semantic': [], # 语义查询
        'mixed': []     # 混合查询
    }

    # 1. 高频关键词（排除停用词）
    stopwords = {'的', '了', '我', '你', '是', '在', '有', '个', '这', '那',
                 '就', '不', '说', '都', '也', '和', '好', '吧', '啊', '呢'}

    for word, count in word_counter.most_common(50):
        if word not in stopwords and len(word) >= 2:
            queries['keyword'].append(word)

    # 2. 常见短语
    phrase_counter = Counter(phrases)
    for phrase, count in phrase_counter.most_common(30):
        if count >= 2:  # 至少出现2次
            queries['semantic'].append(phrase)

    # 3. 随机采样完整句子（作为语义查询）
    import random
    sampled_messages = random.sample(
        [m for m in messages if m.get('content') and len(m['content']) > 10],
        min(10, len(messages))
    )
    for msg in sampled_messages:
        content = msg['content'][:30]  # 取前30字
        queries['mixed'].append(content)

    # 限制数量
    return {
        'conversation': conv_name,
        'file': str(conv_file),
        'keyword': queries['keyword'][:10],
        'semantic': queries['semantic'][:10],
        'mixed': queries['mixed'][:5]
    }

def test_weight_configuration(
    vector_store: HybridVectorStore,
    embedding_client,
    test_queries: dict,
    bm25_weight: float
) -> dict:
    """测试单个权重配置"""

    results = {
        'bm25_weight': bm25_weight,
        'vector_weight': 1 - bm25_weight,
        'queries': [],
        'metrics': {}
    }

    all_scores_diff = []

    for query_type in ['keyword', 'semantic', 'mixed']:
        for query in test_queries.get(query_type, []):
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

            if search_results:
                top1_score = search_results[0]['score']
                top3_score = search_results[2]['score'] if len(search_results) >= 3 else 0
                score_diff = top1_score - top3_score
                all_scores_diff.append(score_diff)

                results['queries'].append({
                    'query': query,
                    'type': query_type,
                    'top1_score': top1_score,
                    'top3_score': top3_score,
                    'score_diff': score_diff,
                    'bm25_score': search_results[0]['bm25_score'],
                    'vector_score': search_results[0]['vector_score']
                })

    # 计算指标
    if all_scores_diff:
        results['metrics'] = {
            'avg_score_diff': sum(all_scores_diff) / len(all_scores_diff),
            'min_score_diff': min(all_scores_diff),
            'max_score_diff': max(all_scores_diff),
            'total_queries': len(all_scores_diff)
        }

    return results

def optimize_weights_for_conversations(conv_files: list, output_file: str = "weight_optimization_results.json"):
    """为多个对话优化权重"""

    print("="*80)
    print("权重优化：寻找BM25和向量的最佳配比")
    print("="*80)

    # 初始化
    embedding_client = GoogleEmbeddingClient()

    # 权重候选
    weight_candidates = [0.5, 0.6, 0.7, 0.8, 0.9]

    all_results = {
        'conversations': [],
        'weight_comparison': defaultdict(lambda: {'total_score_diff': 0, 'count': 0})
    }

    # 为每个对话测试
    for conv_file in conv_files:
        print(f"\n{'='*80}")
        print(f"处理对话: {conv_file.name}")
        print(f"{'='*80}")

        # 1. 生成embedding（如果不存在）
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
        test_queries = generate_test_queries_from_conversation(conv_file)

        print(f"[INFO] 测试查询数量:")
        print(f"  - 关键词: {len(test_queries['keyword'])}")
        print(f"  - 语义: {len(test_queries['semantic'])}")
        print(f"  - 混合: {len(test_queries['mixed'])}")

        # 4. 测试不同权重
        conv_results = {
            'conversation': test_queries['conversation'],
            'file': str(conv_file),
            'test_queries': test_queries,
            'weight_tests': []
        }

        for bm25_w in weight_candidates:
            print(f"\n[INFO] 测试权重配比 BM25:{bm25_w:.1f} Vector:{1-bm25_w:.1f}")

            test_result = test_weight_configuration(
                vector_store, embedding_client, test_queries, bm25_w
            )

            conv_results['weight_tests'].append(test_result)

            # 累积统计
            if 'avg_score_diff' in test_result['metrics']:
                all_results['weight_comparison'][bm25_w]['total_score_diff'] += test_result['metrics']['avg_score_diff']
                all_results['weight_comparison'][bm25_w]['count'] += 1

                print(f"  平均分数区分度: {test_result['metrics']['avg_score_diff']:.3f}")
                print(f"  查询数量: {test_result['metrics']['total_queries']}")

        all_results['conversations'].append(conv_results)

    # 5. 汇总最佳权重
    print(f"\n{'='*80}")
    print("权重优化结果汇总")
    print(f"{'='*80}")

    best_weight = None
    best_score = -1

    for bm25_w in weight_candidates:
        stats = all_results['weight_comparison'][bm25_w]
        if stats['count'] > 0:
            avg_diff = stats['total_score_diff'] / stats['count']
            print(f"BM25:{bm25_w:.1f} Vector:{1-bm25_w:.1f} -> 平均分数区分度: {avg_diff:.3f}")

            if avg_diff > best_score:
                best_score = avg_diff
                best_weight = bm25_w

    all_results['best_weight'] = {
        'bm25': best_weight,
        'vector': 1 - best_weight,
        'score': best_score
    }

    print(f"\n🎯 最佳权重配比: BM25:{best_weight:.1f} Vector:{1-best_weight:.1f}")
    print(f"   平均分数区分度: {best_score:.3f}")

    # 6. 保存结果
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n[INFO] 详细结果已保存到: {output_file}")

    return all_results

def main():
    # 选择测试对话（1000-2000条消息，类型多样化）
    test_conversations = [
        Path("chat_data_filtered/alex_li/alex_li.json"),      # 工作/技术 1069条
        Path("chat_data_filtered/周仕达/周仕达.json"),         # 教育/学习 1008条
        Path("chat_data_filtered/黄心怡/黄心怡.json"),         # 工作讨论 1032条
        Path("chat_data_filtered/阡陌/阡陌.json"),             # 日常生活 1080条
    ]

    # 检查文件是否存在
    valid_conversations = [c for c in test_conversations if c.exists()]

    if not valid_conversations:
        print("[ERROR] 未找到测试对话文件")
        return

    print(f"[INFO] 将测试 {len(valid_conversations)} 个对话")
    for conv in valid_conversations:
        print(f"  - {conv.parent.name}")

    # 运行优化
    results = optimize_weights_for_conversations(valid_conversations)

if __name__ == "__main__":
    load_dotenv()
    main()
