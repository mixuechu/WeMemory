#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""展示图谱清理前后对比"""

import sys
import io
import json
from neo4j import GraphDatabase

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Neo4j连接
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password123'))

print("=" * 80)
print("图谱清理前后对比分析")
print("=" * 80)

with driver.session() as session:
    # 当前统计
    result = session.run('MATCH (p:Person) RETURN count(p) as total')
    current_total = result.single()['total']

    result = session.run('''
        MATCH (p:Person)
        RETURN p.conversation_name as conv, count(p) as count
        ORDER BY count DESC
    ''')
    conv_stats = {r['conv']: r['count'] for r in result}

    # 孤立节点检查
    result = session.run('MATCH (p:Person) WHERE NOT (p)-[]-() RETURN count(p) as isolated')
    isolated = result.single()['isolated']

    # 关系最多的人
    result = session.run('''
        MATCH (p:Person)
        OPTIONAL MATCH (p)-[r]-()
        WITH p, count(r) as rel_count
        WHERE rel_count > 0
        RETURN p.name as name, p.conversation_name as conv, rel_count
        ORDER BY rel_count DESC
        LIMIT 10
    ''')
    top_persons = list(result)

print("\n【当前图谱状态】")
print(f"  总Person节点数: {current_total}")
print(f"  孤立节点数: {isolated}")
print(f"\n  按对话分组:")
for conv, count in conv_stats.items():
    print(f"    {conv}: {count}个")

print(f"\n  关系最多的前10个人物:")
for i, p in enumerate(top_persons, 1):
    print(f"    {i}. {p['name']} ({p['conv']}) - {p['rel_count']}个关系")

# 读取清理记录
import glob
cleanup_files = sorted(glob.glob('cleanup_results_*.json'))
if cleanup_files:
    latest_file = cleanup_files[-1]
    print(f"\n\n【最近一次清理操作】")
    print(f"  文件: {latest_file}")

    with open(latest_file, 'r', encoding='utf-8') as f:
        cleanup_data = json.load(f)

    auto_merges = len(cleanup_data.get('auto_merges', []))
    llm_merges = len(cleanup_data.get('llm_merges', []))
    auto_deletes = len(cleanup_data.get('auto_deletes', []))
    llm_deletes = len(cleanup_data.get('llm_deletes', []))

    total_merges = auto_merges + llm_merges
    total_deletes = auto_deletes + llm_deletes

    print(f"\n  合并操作: {total_merges}次")
    print(f"    - 自动合并（大小写）: {auto_merges}")
    print(f"    - LLM智能合并: {llm_merges}")

    print(f"\n  删除操作: {total_deletes}次")
    print(f"    - 自动删除（孤立节点）: {auto_deletes}")
    print(f"    - LLM智能删除: {llm_deletes}")

    # 估算清理前的节点数
    before_total = current_total + total_merges + total_deletes
    reduction = total_merges + total_deletes
    reduction_pct = (reduction / before_total) * 100

    print(f"\n【清理前后对比】")
    print(f"  清理前: {before_total}个节点")
    print(f"  清理后: {current_total}个节点")
    print(f"  减少: {reduction}个节点 ({reduction_pct:.1f}%)")

    # 展示部分LLM合并案例
    if llm_merges > 0:
        print(f"\n【LLM智能合并案例】（前10个）")
        for i, merge in enumerate(cleanup_data['llm_merges'][:10], 1):
            source = merge['source'][0]
            target = merge['target'][0]
            reason = merge.get('reason', '')
            conf = merge.get('confidence', 0)
            print(f"  {i}. {source} → {target}")
            print(f"     理由: {reason} (置信度: {conf})")

driver.close()

print("\n" + "=" * 80)
print("提示: 在Neo4j浏览器中运行以下查询可视化图谱:")
print("  http://localhost:7474")
print("\n查询示例:")
print("  1. MATCH (p:Person)-[r]-(o) RETURN p,r,o LIMIT 100")
print("  2. MATCH (p:Person {name: 'Hunter'})-[r]-(o) RETURN p,r,o")
print("=" * 80)
