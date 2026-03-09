#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查Event统计"""

import sys
import io
from neo4j import GraphDatabase

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password123'))

with driver.session() as session:
    # 检查王露颖参与的Event数
    result = session.run('''
        MATCH (p:Person {name: "王露颖"})-[:PARTICIPATED_IN]->(e:Event)
        RETURN count(e) as cnt
    ''')
    wly_count = result.single()['cnt']
    print(f'王露颖参与的Event数: {wly_count}')

    # 检查米雪川是否存在
    result = session.run('''
        MATCH (p:Person)
        WHERE p.name CONTAINS "米雪川" OR p.name CONTAINS "mixuechuan"
        RETURN p.name as name, p.aliases as aliases
    ''')
    print(f'\n米雪川相关Person:')
    found = False
    for record in result:
        print(f'  - {record["name"]}: {record["aliases"]}')
        found = True
    if not found:
        print('  未找到米雪川相关Person')

    # 检查吉月对话中所有Person参与Event情况
    result = session.run('''
        MATCH (p:Person {conversation_name: "吉月"})-[:PARTICIPATED_IN]->(e:Event)
        WITH p, count(e) as event_count
        WHERE event_count > 10
        RETURN p.name as name, p.aliases as aliases, event_count
        ORDER BY event_count DESC
        LIMIT 30
    ''')
    print(f'\n吉月对话中参与Event最多的Person（>10个）:')
    for record in result:
        print(f'  - {record["name"]}: {record["event_count"]}个Event, aliases={record["aliases"]}')

    # 检查米雪川和王露颖共同参与的Event
    result = session.run('''
        MATCH (p1:Person)-[:PARTICIPATED_IN]->(e:Event)<-[:PARTICIPATED_IN]-(p2:Person {name: "王露颖"})
        WHERE p1.name CONTAINS "米" OR p1.name CONTAINS "川" OR p1.name CONTAINS "xue"
        RETURN p1.name, count(e) as shared_events
        ORDER BY shared_events DESC
    ''')
    print(f'\n和王露颖共同参与Event的Person（名字包含米/川/xue）:')
    for record in result:
        print(f'  - {record["p1.name"]}: {record["shared_events"]}个共同Event')

driver.close()
