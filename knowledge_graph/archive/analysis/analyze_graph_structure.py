#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析图谱结构（不需要Neo4j）"""

import json
import sys
import io
from pathlib import Path
from collections import defaultdict, Counter

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

JY_DIR = Path("../extractions/test_jy_only")
JIYUE_DIR = Path("../extractions/test_jiyue_only")


def analyze_graph_structure():
    """分析图谱结构"""
    print("=" * 80)
    print("图谱结构分析")
    print("=" * 80)
    print()

    # 加载所有文件
    all_files = []
    for directory in [JY_DIR, JIYUE_DIR]:
        if directory.exists():
            files = list(directory.glob("session_*.json"))
            all_files.extend(files)
            print(f"加载 {directory.name}: {len(files)} 文件")

    # 统计
    stats = {
        'people': defaultdict(set),  # name -> set of conversation_names
        'topics': Counter(),
        'organizations': Counter(),
        'locations': Counter(),
        'events': 0,
        'relationships': Counter(),  # relationship type -> count
    }

    for f in all_files:
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)

        if not data.get('success'):
            continue

        conv_name = data['conversation']['conversation_name']
        entities = data['entities']

        # People - 记录(name, conversation_name)组合
        for person in entities.get('people', []):
            stats['people'][person['name']].add(conv_name)

        # Topics
        for topic in entities.get('topics', []):
            stats['topics'][topic['name']] += 1

        # Organizations
        for org in entities.get('organizations', []):
            stats['organizations'][org['name']] += 1

        # Locations
        for loc in entities.get('locations', []):
            stats['locations'][loc['name']] += 1

        # Events
        stats['events'] += len(entities.get('events', []))

        # Relationships
        for rel in entities.get('relationships', []):
            stats['relationships'][rel['type']] += 1

    # 输出分析
    print("\n" + "=" * 80)
    print("节点统计")
    print("=" * 80)

    # People去重分析
    unique_people = len(stats['people'])
    total_people_nodes = sum(len(convs) for convs in stats['people'].values())
    print(f"\nPerson:")
    print(f"  唯一人名: {unique_people}")
    print(f"  总节点数: {total_people_nodes}")
    print(f"  说明: 同一个人名在不同对话中算作独立节点")

    print(f"\nTopic: {len(stats['topics'])} 个唯一主题")
    print(f"Organization: {len(stats['organizations'])} 个")
    print(f"Location: {len(stats['locations'])} 个")
    print(f"Event: {stats['events']} 个")

    # 检查重名
    print("\n" + "=" * 80)
    print("重名检查（同一个名字在多个对话中出现）")
    print("=" * 80)

    duplicates = {name: convs for name, convs in stats['people'].items() if len(convs) > 1}
    print(f"\n跨对话重名: {len(duplicates)} 个")
    print("\n示例（前10个）:")
    for name, convs in list(duplicates.items())[:10]:
        print(f"  {name}: 出现在 {len(convs)} 个对话 - {list(convs)}")

    # 家人实体规范化检查
    print("\n" + "=" * 80)
    print("家人实体命名检查")
    print("=" * 80)

    family_keywords = ['弟弟', '妈妈', '爸爸', '姐姐', '哥哥', '妹妹']
    family_entities = [name for name in stats['people'].keys()
                       if any(kw in name for kw in family_keywords)]

    normalized = [name for name in family_entities if '的' in name]
    not_normalized = [name for name in family_entities if '的' not in name]

    print(f"\n家人实体总数: {len(family_entities)}")
    print(f"  ✅ 已规范化 (XX的XX): {len(normalized)}")
    print(f"  ⚠️  未规范化: {len(not_normalized)}")

    if not_normalized:
        print("\n未规范化示例:")
        for name in not_normalized[:5]:
            convs = stats['people'][name]
            print(f"  {name} - 出现在: {list(convs)}")

    # 关系类型统计
    print("\n" + "=" * 80)
    print("关系类型统计")
    print("=" * 80)
    for rel_type, count in stats['relationships'].most_common(15):
        print(f"  {rel_type}: {count}")

    # 热门Topics
    print("\n" + "=" * 80)
    print("热门Topics (Top 20)")
    print("=" * 80)
    for topic, count in stats['topics'].most_common(20):
        print(f"  {topic}: {count} 次")

    # 跨用户连接检查
    print("\n" + "=" * 80)
    print("跨用户连接分析")
    print("=" * 80)

    # 检查是否有人名同时出现在JY和吉月的对话中
    jy_people = {name for name, convs in stats['people'].items() if 'JY' in convs}
    jiyue_people = {name for name, convs in stats['people'].items() if '吉月' in convs}
    common_names = jy_people & jiyue_people

    print(f"\nJY对话中的人名: {len(jy_people)}")
    print(f"吉月对话中的人名: {len(jiyue_people)}")
    print(f"共同出现的人名: {len(common_names)}")

    if common_names:
        print("\n共同人名示例:")
        for name in list(common_names)[:10]:
            print(f"  - {name}")

    print("\n" + "=" * 80)
    print("✅ 分析完成")
    print("=" * 80)


if __name__ == '__main__':
    analyze_graph_structure()
