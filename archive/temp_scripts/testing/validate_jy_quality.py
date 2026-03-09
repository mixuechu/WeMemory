#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证JY提取质量"""

import json
import sys
import io
from pathlib import Path
from collections import Counter

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

EXTRACTION_DIR = Path("../extractions/test_jy_only")

def main():
    files = list(EXTRACTION_DIR.glob("session_*.json"))

    print("=" * 80)
    print("JY提取质量验证")
    print("=" * 80)
    print()

    # 统计
    stats = {
        'success': 0,
        'failed': 0,
        'total_entities': {'people': 0, 'organizations': 0, 'topics': 0, 'events': 0, 'locations': 0},
        'total_relationships': 0
    }

    topic_names = Counter()
    event_types = Counter()

    # 检查问题
    issues = {
        'no_entities': [],
        'missing_user': [],
        'has_conversation_id': []  # 检查是否还有conversation_id字段
    }

    for f in files:
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)

            if not data.get('success'):
                stats['failed'] += 1
                continue

            stats['success'] += 1
            entities = data['entities']

            # 统计实体
            for key in stats['total_entities']:
                count = len(entities.get(key, []))
                stats['total_entities'][key] += count

            stats['total_relationships'] += len(entities.get('relationships', []))

            # 检查是否有conversation_id字段
            for person in entities.get('people', []):
                if 'conversation_id' in person:
                    issues['has_conversation_id'].append({
                        'file': f.name,
                        'person': person['name'],
                        'conversation_id': person.get('conversation_id')
                    })

            # 检查是否完全没有实体
            total_entities = sum(len(entities.get(key, [])) for key in ['people', 'organizations', 'topics', 'events', 'locations'])
            if total_entities == 0:
                issues['no_entities'].append(f.name)

            # 检查是否缺少米雪川（如果米雪川在participants中）
            participants = data['conversation']['participants']
            has_mixuechuan = any('米雪川' in p for p in participants)
            people_names = [p['name'] for p in entities.get('people', [])]
            has_user = any('米雪川' in name for name in people_names)

            if has_mixuechuan and not has_user:
                issues['missing_user'].append(f.name)

            # 统计topics和events
            for topic in entities.get('topics', []):
                topic_names[topic['name']] += 1

            for event in entities.get('events', []):
                event_types[event['type']] += 1

    # 输出统计
    print(f"总文件数: {len(files)}")
    print(f"成功: {stats['success']}")
    print(f"失败: {stats['failed']}")
    print()

    print("平均实体数 (每个session):")
    print("-" * 80)
    for key, value in stats['total_entities'].items():
        print(f"  {key:15s}: {value/stats['success']:.1f}")
    print(f"  {'relationships':15s}: {stats['total_relationships']/stats['success']:.1f}")
    print()

    # 检查问题
    print("=" * 80)
    print("问题检查:")
    print("=" * 80)

    print("\n【1】是否还有conversation_id字段？")
    print("-" * 80)
    if issues['has_conversation_id']:
        print(f"❌ 发现 {len(issues['has_conversation_id'])} 个实体仍有conversation_id字段:")
        for item in issues['has_conversation_id'][:5]:
            print(f"  {item['file']}: {item['person']} - conversation_id={item['conversation_id']}")
    else:
        print("✅ 无问题 - 所有实体都没有conversation_id字段")

    print("\n【2】是否有空提取？")
    print("-" * 80)
    if issues['no_entities']:
        print(f"❌ 发现 {len(issues['no_entities'])} 个空提取:")
        for item in issues['no_entities']:
            print(f"  {item}")
    else:
        print("✅ 无问题")

    print("\n【3】是否缺少米雪川？")
    print("-" * 80)
    if issues['missing_user']:
        print(f"❌ 发现 {len(issues['missing_user'])} 个缺失:")
        for item in issues['missing_user']:
            print(f"  {item}")
    else:
        print("✅ 无问题")

    # Topic和Event分布
    print("\n" + "=" * 80)
    print("Topic 分布 (Top 15):")
    print("-" * 80)
    for topic, count in topic_names.most_common(15):
        print(f"  {topic}: {count}")

    print("\nEvent 类型分布:")
    print("-" * 80)
    for etype, count in event_types.most_common(10):
        print(f"  {etype}: {count}")

    # 随机展示3个提取结果
    print("\n" + "=" * 80)
    print("样本展示 (前3个):")
    print("=" * 80)
    for f in sorted(files)[:3]:
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)
            entities = data['entities']

            print(f"\n文件: {f.name}")
            print(f"  消息数: {data['conversation']['message_count']}")
            print(f"  People: {len(entities.get('people', []))}")
            print(f"  Topics: {len(entities.get('topics', []))}")
            print(f"  Events: {len(entities.get('events', []))}")
            print(f"  Relationships: {len(entities.get('relationships', []))}")

            # 显示人物
            people = entities.get('people', [])
            if people:
                print(f"  人物列表:")
                for p in people[:3]:
                    print(f"    - {p['name']} (is_user: {p.get('is_user', False)})")

    print("\n" + "=" * 80)
    print("✅ 质量验证完成")
    print("=" * 80)

if __name__ == '__main__':
    main()
