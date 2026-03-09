#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import io
from neo4j import GraphDatabase

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password123'))

with driver.session() as session:
    # 统计各个conversation的节点数
    result = session.run('''
        MATCH (p:Person)
        RETURN p.conversation_name as conversation, count(*) as person_count
        ORDER BY person_count DESC
    ''')

    print('各对话的Person节点数：')
    print('=' * 50)
    for record in result:
        print(f'{record["conversation"]}: {record["person_count"]}个')

    print()
    print('总计：')
    result = session.run('MATCH (p:Person) RETURN count(DISTINCT p.conversation_name) as conv_count')
    for record in result:
        print(f'  不同对话数: {record["conv_count"]}个')

    result = session.run('MATCH (p:Person) RETURN count(p) as total')
    for record in result:
        print(f'  总Person节点: {record["total"]}个')

driver.close()
