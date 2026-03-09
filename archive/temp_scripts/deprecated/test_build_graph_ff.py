#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试构建图：从JSON到Neo4j"""

import sys
from pathlib import Path
from build_neo4j_graph import Neo4jGraphBuilder

print("=" * 80)
print("测试构建图：从JSON到Neo4j（FF对话）")
print("=" * 80)

# 连接Neo4j
builder = Neo4jGraphBuilder('bolt://localhost:7687', 'neo4j', 'password123')

# 清理FF对话的旧数据
print("\n清理旧数据...")
with builder.driver.session() as session:
    result = session.run('MATCH (n {conversation_name: $conv}) DETACH DELETE n', conv='FF')
    print(f"✓ 已清理FF对话的旧数据")

# 加载提取文件
json_file = Path("extraction_output/session_test_extraction_ff.json")
print(f"\n加载提取文件: {json_file}")
builder.load_extraction_file(json_file)

# 验证结果
print("\n" + "=" * 80)
print("验证构建结果")
print("=" * 80)

with builder.driver.session() as session:
    # 1. Person节点
    result = session.run('''
        MATCH (p:Person {conversation_name: $conv})
        RETURN p.name as name, p.conversation_name as conv
    ''', conv='FF')
    people = list(result)
    print(f"\n✅ Person节点: {len(people)}个")
    for p in people:
        has_conv = "✓" if p['conv'] else "✗"
        print(f"  [{has_conv} conv] {p['name']}")

    # 2. Event节点
    result = session.run('''
        MATCH (e:Event {conversation_name: $conv})
        RETURN e.name as name, e.event_id as event_id, e.conversation_name as conv
    ''', conv='FF')
    events = list(result)
    print(f"\n✅ Event节点: {len(events)}个")
    for e in events:
        has_id = "✓" if e['event_id'] else "✗"
        has_conv = "✓" if e['conv'] else "✗"
        print(f"  [{has_id} event_id] [{has_conv} conv] {e['name']}")

    # 3. PARTICIPATED_IN关系（自动创建）
    result = session.run('''
        MATCH (p:Person {conversation_name: $conv})-[r:PARTICIPATED_IN]->(e:Event {conversation_name: $conv})
        RETURN p.name as person, e.name as event
    ''', conv='FF')
    relations = list(result)
    print(f"\n✅ PARTICIPATED_IN关系（自动创建）: {len(relations)}个")
    for r in relations:
        print(f"  - {r['person']} → {r['event']}")

    # 4. 其他关系（从relationships数组）
    result = session.run('''
        MATCH (p1:Person {conversation_name: $conv})-[r:KNOWS|DISCUSSED_WITH]->(p2:Person {conversation_name: $conv})
        RETURN type(r) as rel_type, p1.name as source, p2.name as target
    ''', conv='FF')
    other_rels = list(result)
    print(f"\n✅ 其他关系: {len(other_rels)}个")
    rel_counts = {}
    for r in other_rels:
        rel_type = r['rel_type']
        rel_counts[rel_type] = rel_counts.get(rel_type, 0) + 1
    for rel_type, count in rel_counts.items():
        print(f"  - {rel_type}: {count}个")

# 最终验证
print("\n" + "=" * 80)
print("修复验证")
print("=" * 80)

all_events_have_id = all(e['event_id'] for e in events)
all_events_have_conv = all(e['conv'] for e in events)
all_people_have_conv = all(p['conv'] for p in people)
expected_participated_in = 8  # 4个Event × 2个participants
actual_participated_in = len(relations)

print(f"\n检查1: Event节点字段")
print(f"  - event_id字段: {'✅' if all_events_have_id else '❌'}")
print(f"  - conversation_name字段: {'✅' if all_events_have_conv else '❌'}")

print(f"\n检查2: Person节点字段")
print(f"  - conversation_name字段: {'✅' if all_people_have_conv else '❌'}")

print(f"\n检查3: PARTICIPATED_IN自动创建")
print(f"  - 预期关系数: {expected_participated_in}个")
print(f"  - 实际关系数: {actual_participated_in}个")
print(f"  - 状态: {'✅ 完全匹配' if actual_participated_in == expected_participated_in else '❌ 不匹配'}")

all_checks_passed = (
    all_events_have_id and
    all_events_have_conv and
    all_people_have_conv and
    actual_participated_in == expected_participated_in
)

print("\n" + "=" * 80)
if all_checks_passed:
    print("🎉 所有检查通过！构建图流程正常工作")
    print("  ✅ Event有event_id和conversation_name")
    print("  ✅ Person有conversation_name")
    print("  ✅ PARTICIPATED_IN关系自动创建")
else:
    print("⚠️ 部分检查未通过")
print("=" * 80)

# 保留数据供查看（不清理）
print(f"\n💡 FF对话的图数据已保留，可以在Neo4j Browser中查看")
print(f"   查询示例: MATCH (n {{conversation_name: 'FF'}}) RETURN n")

builder.close()
