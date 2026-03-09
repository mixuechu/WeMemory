#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""监控提取进度和质量"""

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

OUTPUT_DIR = Path("extractions")


def analyze_extractions():
    """分析提取结果"""
    print("=" * 80)
    print("📊 提取结果分析")
    print("=" * 80)

    # 加载所有提取结果
    files = list(OUTPUT_DIR.glob("session_*.json"))
    total_files = len(files)

    if total_files == 0:
        print("\n⚠️ 未找到提取结果文件")
        return

    print(f"\n📁 找到 {total_files:,} 个提取文件\n")

    # 统计
    stats = {
        'total': total_files,
        'success': 0,
        'failed': 0,
        'total_cost': 0.0,
        'total_duration': 0.0,
        'entity_counts': defaultdict(int),
        'relationship_counts': defaultdict(int),
        'errors': defaultdict(int)
    }

    entity_stats = {
        'people': [],
        'organizations': [],
        'topics': [],
        'events': [],
        'locations': [],
        'relationships': []
    }

    # 遍历所有文件
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                result = json.load(f)

            if result.get('success'):
                stats['success'] += 1

                # 成本和时间
                metadata = result.get('extraction_metadata', {})
                stats['total_cost'] += metadata.get('cost', 0)
                stats['total_duration'] += metadata.get('duration_seconds', 0)

                # 实体统计
                entities = result.get('entities', {})
                if entities:
                    for entity_type in ['people', 'organizations', 'topics', 'events', 'locations', 'relationships']:
                        count = len(entities.get(entity_type, []))
                        stats['entity_counts'][entity_type] += count
                        entity_stats[entity_type].append(count)
            else:
                stats['failed'] += 1
                error = result.get('error', 'Unknown error')
                stats['errors'][error] += 1

        except Exception as e:
            stats['failed'] += 1
            stats['errors'][f'文件读取错误: {str(e)}'] += 1

    # 打印统计
    print("📈 总体统计:")
    print(f"  - 成功: {stats['success']:,} ({stats['success']/stats['total']*100:.1f}%)")
    print(f"  - 失败: {stats['failed']:,} ({stats['failed']/stats['total']*100:.1f}%)")
    print(f"  - 总成本: ${stats['total_cost']:.2f}")
    print(f"  - 总耗时: {stats['total_duration']/3600:.2f} 小时")
    print(f"  - 平均成本: ${stats['total_cost']/stats['success']:.6f} /条" if stats['success'] > 0 else "")

    print("\n🎯 实体统计:")
    for entity_type, counts in entity_stats.items():
        if counts:
            total = sum(counts)
            avg = total / len(counts)
            print(f"  - {entity_type:15s}: 总计 {total:,} 个, 平均 {avg:.1f} 个/对话")

    if stats['failed'] > 0:
        print("\n❌ 错误统计:")
        for error, count in sorted(stats['errors'].items(), key=lambda x: x[1], reverse=True):
            print(f"  - {error}: {count} 次")

    # 质量检查
    print("\n🔍 质量检查:")

    # 检查空提取
    empty_extractions = sum(1 for counts in entity_stats['people'] if counts == 0)
    print(f"  - 未提取到人物的对话: {empty_extractions} ({empty_extractions/stats['success']*100:.1f}%)" if stats['success'] > 0 else "")

    # 检查高质量提取（总实体 > 10）
    high_quality = 0
    for i in range(len(entity_stats['people'])):
        total_entities = sum([
            entity_stats['people'][i],
            entity_stats['topics'][i],
            entity_stats['events'][i],
            entity_stats['locations'][i]
        ])
        if total_entities > 10:
            high_quality += 1

    print(f"  - 高质量提取（>10实体）: {high_quality} ({high_quality/stats['success']*100:.1f}%)" if stats['success'] > 0 else "")

    print("\n" + "=" * 80)


def list_failed_extractions():
    """列出失败的提取"""
    print("\n" + "=" * 80)
    print("❌ 失败的提取记录")
    print("=" * 80 + "\n")

    files = list(OUTPUT_DIR.glob("session_*.json"))
    failed_count = 0

    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                result = json.load(f)

            if not result.get('success'):
                failed_count += 1
                conv_name = result['conversation']['conversation_name']
                error = result.get('error', 'Unknown')
                print(f"{failed_count}. {conv_name}")
                print(f"   文件: {filepath.name}")
                print(f"   错误: {error}\n")

        except Exception as e:
            print(f"⚠️ 无法读取文件: {filepath.name}")
            print(f"   错误: {str(e)}\n")

    if failed_count == 0:
        print("✅ 没有失败的提取记录")

    print("=" * 80)


def sample_extractions(count: int = 5):
    """随机查看几个提取结果"""
    import random

    print("\n" + "=" * 80)
    print(f"🔍 随机查看 {count} 个提取结果")
    print("=" * 80 + "\n")

    files = list(OUTPUT_DIR.glob("session_*.json"))
    if not files:
        print("⚠️ 未找到提取结果文件")
        return

    samples = random.sample(files, min(count, len(files)))

    for i, filepath in enumerate(samples, 1):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                result = json.load(f)

            conv = result['conversation']
            entities = result.get('entities', {})

            print(f"样本 {i}: {conv['conversation_name']}")
            print(f"  时间: {conv.get('year', '?')}-{conv.get('month', '?')}")
            print(f"  类型: {conv.get('conversation_type', '?')}")
            print(f"  状态: {'✅ 成功' if result.get('success') else '❌ 失败'}")

            if entities:
                print(f"  实体:")
                print(f"    - People: {len(entities.get('people', []))}")
                print(f"    - Organizations: {len(entities.get('organizations', []))}")
                print(f"    - Topics: {len(entities.get('topics', []))}")
                print(f"    - Events: {len(entities.get('events', []))}")
                print(f"    - Locations: {len(entities.get('locations', []))}")
                print(f"    - Relationships: {len(entities.get('relationships', []))}")

                # 显示几个人物
                people = entities.get('people', [])
                if people:
                    print(f"  人物示例:")
                    for person in people[:3]:
                        print(f"    - {person.get('name', '?')} ({person.get('relationship_to_user', '?')})")

                # 显示几个主题
                topics = entities.get('topics', [])
                if topics:
                    print(f"  主题示例:")
                    for topic in topics[:3]:
                        print(f"    - {topic.get('name', '?')} [{topic.get('type', '?')}]")

            metadata = result.get('extraction_metadata', {})
            if metadata:
                print(f"  性能:")
                print(f"    - 耗时: {metadata.get('duration_seconds', 0):.1f}秒")
                print(f"    - 成本: ${metadata.get('cost', 0):.6f}")

            print()

        except Exception as e:
            print(f"⚠️ 无法读取文件: {filepath.name}")
            print(f"   错误: {str(e)}\n")

    print("=" * 80)


if __name__ == '__main__':
    # 分析所有提取结果
    analyze_extractions()

    # 列出失败的提取
    list_failed_extractions()

    # 随机查看几个样本
    sample_extractions(count=5)
