#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查Neo4j中有哪些对话"""

from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password123'))

with driver.session() as session:
    # 获取所有不同的conversation_name
    result = session.run('''
        MATCH (n)
        WHERE n.conversation_name IS NOT NULL
        RETURN DISTINCT n.conversation_name as conv
        ORDER BY conv
    ''')

    conversations = [r['conv'] for r in result]

    print(f"Neo4j中的对话数: {len(conversations)}")
    print("")
    for conv in conversations:
        # 统计每个对话的节点数
        result = session.run('''
            MATCH (n {conversation_name: $conv})
            RETURN labels(n)[0] as label, count(*) as count
        ''', conv=conv)

        stats = {r['label']: r['count'] for r in result}
        total = sum(stats.values())

        print(f"{conv}:")
        print(f"  总节点: {total}")
        for label, count in sorted(stats.items()):
            print(f"    {label}: {count}")
        print("")

driver.close()
