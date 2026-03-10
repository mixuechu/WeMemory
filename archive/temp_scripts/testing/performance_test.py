#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 性能测试

测试内容：
1. 启动时间
2. 内存占用
3. 查询性能
4. 查询质量
"""
import sys
import os
import time
import json
import psutil
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from api.services.recall_service import RecallService


def format_bytes(bytes_val):
    """格式化字节数"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} TB"


def test_startup_and_memory():
    """测试启动时间和内存占用"""
    print("=" * 70)
    print("测试 1: 启动时间和内存占用")
    print("=" * 70)

    # 记录启动前内存
    process = psutil.Process()
    mem_before = process.memory_info().rss

    print(f"\n启动前内存: {format_bytes(mem_before)}")
    print("开始加载向量库...")

    # 计时
    start_time = time.time()

    # 初始化服务
    service = RecallService("vector_stores/conversations_complete.pkl")

    load_time = time.time() - start_time

    # 记录启动后内存
    mem_after = process.memory_info().rss
    mem_increase = mem_after - mem_before

    print(f"\n✓ 加载完成！")
    print(f"  启动时间: {load_time:.2f} 秒")
    print(f"  启动后内存: {format_bytes(mem_after)}")
    print(f"  内存增量: {format_bytes(mem_increase)}")
    print(f"  向量库大小: {len(service.vector_store.metadata):,} 个记忆")

    return service, {
        'startup_time': load_time,
        'memory_before': mem_before,
        'memory_after': mem_after,
        'memory_increase': mem_increase
    }


def test_query_performance(service):
    """测试查询性能"""
    print("\n" + "=" * 70)
    print("测试 2: 查询性能")
    print("=" * 70)

    test_queries = [
        "我跟alex聊过AI相关的话题吗",
        "关于AWS权限的讨论",
        "alex让我不要做前端",
        "我们讨论过部署的问题",
        "alex提到leo那边的工作"
    ]

    results = []
    total_time = 0

    for i, query in enumerate(test_queries, 1):
        print(f"\n[{i}/{len(test_queries)}] 查询: '{query}'")

        start_time = time.time()
        result = service.recall(query, top_k=5)
        query_time = (time.time() - start_time) * 1000  # 转换为毫秒

        total_time += query_time

        print(f"  处理时间: {query_time:.1f}ms")
        print(f"  联想策略: {result['recall_strategy']}")
        print(f"  找到记忆: {result['total_count']} 个")

        if result['memories']:
            top_result = result['memories'][0]
            print(f"  最相关:")
            print(f"    - 相关度: {top_result['relevance_score']:.3f}")
            print(f"    - 原因: {top_result['recall_reason']}")
            print(f"    - 对话: {top_result['conversation_name']}")

        results.append({
            'query': query,
            'time_ms': query_time,
            'count': result['total_count'],
            'top_score': result['memories'][0]['relevance_score'] if result['memories'] else 0
        })

    avg_time = total_time / len(test_queries)

    print("\n" + "-" * 70)
    print("性能统计:")
    print(f"  总查询数: {len(test_queries)}")
    print(f"  总耗时: {total_time:.1f}ms")
    print(f"  平均耗时: {avg_time:.1f}ms")
    print(f"  最快查询: {min(r['time_ms'] for r in results):.1f}ms")
    print(f"  最慢查询: {max(r['time_ms'] for r in results):.1f}ms")

    return results


def test_query_quality(service):
    """测试查询质量"""
    print("\n" + "=" * 70)
    print("测试 3: 查询质量（使用评测测试集）")
    print("=" * 70)

    # 加载测试查询
    test_file = Path("evaluation/queries/meaningful_test_queries.json")
    if not test_file.exists():
        print("\n[WARNING] 测试集文件不存在，跳过质量测试")
        return []

    with open(test_file, 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    queries = test_data['test_queries']
    print(f"\n加载了 {len(queries)} 个测试查询")

    quality_results = []

    for i, test_case in enumerate(queries[:10], 1):  # 只测试前10个
        query = test_case['query']
        expected_keywords = test_case['expected_keywords']

        print(f"\n[{i}/10] 查询: '{query}'")
        print(f"  期望关键词: {', '.join(expected_keywords)}")

        result = service.recall(query, top_k=3)

        if not result['memories']:
            print(f"  ✗ 无结果")
            quality_results.append({
                'query': query,
                'found': False,
                'relevance': 0,
                'keyword_match': 0
            })
            continue

        # 检查关键词匹配
        top_result = result['memories'][0]
        content = top_result['content'].lower()

        matched_keywords = [kw for kw in expected_keywords if kw.lower() in content]
        match_rate = len(matched_keywords) / len(expected_keywords)

        print(f"  ✓ 最相关结果:")
        print(f"    - 相关度: {top_result['relevance_score']:.3f}")
        print(f"    - 关键词匹配: {len(matched_keywords)}/{len(expected_keywords)} ({match_rate*100:.0f}%)")
        print(f"    - 匹配的关键词: {', '.join(matched_keywords) if matched_keywords else '无'}")
        print(f"    - 内容片段: {content[:100]}...")

        quality_results.append({
            'query': query,
            'found': True,
            'relevance': top_result['relevance_score'],
            'keyword_match': match_rate
        })

    # 统计
    if quality_results:
        found_count = sum(1 for r in quality_results if r['found'])
        avg_relevance = sum(r['relevance'] for r in quality_results) / len(quality_results)
        avg_keyword_match = sum(r['keyword_match'] for r in quality_results) / len(quality_results)

        print("\n" + "-" * 70)
        print("质量统计:")
        print(f"  测试查询数: {len(quality_results)}")
        print(f"  找到结果: {found_count}/{len(quality_results)} ({found_count/len(quality_results)*100:.0f}%)")
        print(f"  平均相关度: {avg_relevance:.3f}")
        print(f"  平均关键词匹配率: {avg_keyword_match*100:.1f}%")

    return quality_results


def test_cache_performance(service):
    """测试缓存性能"""
    print("\n" + "=" * 70)
    print("测试 4: 缓存性能")
    print("=" * 70)

    query = "关于AI项目的讨论"

    # 第一次查询（无缓存）
    print(f"\n查询: '{query}'")
    print("第一次（无缓存）...")
    start_time = time.time()
    result1 = service.recall(query, top_k=5)
    time1 = (time.time() - start_time) * 1000

    print(f"  耗时: {time1:.1f}ms")

    # 第二次查询（有缓存）
    print("第二次（有缓存）...")
    start_time = time.time()
    result2 = service.recall(query, top_k=5)
    time2 = (time.time() - start_time) * 1000

    print(f"  耗时: {time2:.1f}ms")

    speedup = time1 / time2 if time2 > 0 else 0
    print(f"\n缓存加速: {speedup:.1f}x")

    return {
        'first_query_ms': time1,
        'cached_query_ms': time2,
        'speedup': speedup
    }


def test_concurrent_load(service):
    """测试并发负载（简单模拟）"""
    print("\n" + "=" * 70)
    print("测试 5: 并发负载模拟")
    print("=" * 70)

    queries = [
        "AI相关讨论",
        "AWS权限",
        "前端后端",
        "部署问题",
        "项目进展"
    ] * 4  # 20个查询

    print(f"\n连续执行 {len(queries)} 个查询...")

    start_time = time.time()

    for i, query in enumerate(queries, 1):
        result = service.recall(query, top_k=3)
        if i % 5 == 0:
            elapsed = (time.time() - start_time) * 1000
            print(f"  完成 {i}/{len(queries)} 个查询，耗时: {elapsed:.0f}ms")

    total_time = (time.time() - start_time) * 1000
    avg_time = total_time / len(queries)
    qps = 1000 / avg_time  # queries per second

    print(f"\n负载测试结果:")
    print(f"  总查询数: {len(queries)}")
    print(f"  总耗时: {total_time:.0f}ms")
    print(f"  平均耗时: {avg_time:.1f}ms")
    print(f"  吞吐量: {qps:.1f} queries/second")

    return {
        'total_queries': len(queries),
        'total_time_ms': total_time,
        'avg_time_ms': avg_time,
        'qps': qps
    }


def main():
    """主测试流程"""
    print("\n" + "=" * 70)
    print("WeMemory API 性能测试")
    print("=" * 70)

    try:
        # 测试 1: 启动和内存
        service, startup_stats = test_startup_and_memory()

        # 测试 2: 查询性能
        perf_results = test_query_performance(service)

        # 测试 3: 查询质量
        quality_results = test_query_quality(service)

        # 测试 4: 缓存性能
        cache_stats = test_cache_performance(service)

        # 测试 5: 并发负载
        load_stats = test_concurrent_load(service)

        # 汇总报告
        print("\n" + "=" * 70)
        print("测试总结")
        print("=" * 70)

        print(f"\n【启动性能】")
        print(f"  启动时间: {startup_stats['startup_time']:.2f} 秒")
        print(f"  内存占用: {format_bytes(startup_stats['memory_increase'])}")

        print(f"\n【查询性能】")
        if perf_results:
            avg_perf = sum(r['time_ms'] for r in perf_results) / len(perf_results)
            print(f"  平均查询时间: {avg_perf:.1f}ms")
            print(f"  平均相关度: {sum(r['top_score'] for r in perf_results) / len(perf_results):.3f}")

        print(f"\n【查询质量】")
        if quality_results:
            found = sum(1 for r in quality_results if r['found'])
            avg_rel = sum(r['relevance'] for r in quality_results) / len(quality_results)
            avg_match = sum(r['keyword_match'] for r in quality_results) / len(quality_results)
            print(f"  召回率: {found}/{len(quality_results)} ({found/len(quality_results)*100:.0f}%)")
            print(f"  平均相关度: {avg_rel:.3f}")
            print(f"  关键词匹配: {avg_match*100:.1f}%")

        print(f"\n【缓存性能】")
        print(f"  首次查询: {cache_stats['first_query_ms']:.1f}ms")
        print(f"  缓存查询: {cache_stats['cached_query_ms']:.1f}ms")
        print(f"  加速比: {cache_stats['speedup']:.1f}x")

        print(f"\n【并发性能】")
        print(f"  吞吐量: {load_stats['qps']:.1f} queries/second")
        print(f"  平均延迟: {load_stats['avg_time_ms']:.1f}ms")

        print("\n" + "=" * 70)
        print("✓ 所有测试完成！")
        print("=" * 70)

    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
