#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""列出和吉月有关系的所有Person实体"""

import sys
import io
from neo4j import GraphDatabase

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

NEO4J_URI = 'bolt://localhost:7687'
NEO4J_USER = 'neo4j'
NEO4J_PASSWORD = 'password123'

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("=" * 80)
print("和吉月有关系的Person实体列表")
print("=" * 80)

with driver.session() as session:
    result = session.run("""
        MATCH (jy:Person {name: '吉月', conversation_name: '吉月'})-[r]-(other:Person)
        WITH other, count(r) as rel_count, collect(DISTINCT type(r)) as rel_types
        RETURN other.name as name, rel_count, rel_types
        ORDER BY rel_count DESC
    """)

    persons = list(result)

    print(f"\n总计: {len(persons)} 个Person实体与吉月有关系\n")
    print(f"{'序号':<6} {'姓名':<30} {'关系数':<10} {'关系类型'}")
    print("-" * 80)

    for i, p in enumerate(persons, 1):
        name = p['name']
        rel_count = p['rel_count']
        rel_types = ', '.join(p['rel_types'][:3])  # 最多显示3个关系类型
        if len(p['rel_types']) > 3:
            rel_types += f" (+{len(p['rel_types']) - 3}种)"

        print(f"{i:<6} {name:<30} {rel_count:<10} {rel_types}")

driver.close()

print("\n" + "=" * 80)
print("提示: 如果需要合并某些Person，请记录下序号或姓名")
print("=" * 80)
