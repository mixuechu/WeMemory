#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""执行手工确认的Person实体合并"""

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

# 定义要合并的组（高确定性 + 中等确定性）
MERGE_GROUPS = [
    # 高确定性
    {"target": "Hunter", "sources": ["hunter", "hunyer", "hjnter"]},
    {"target": "Joshua", "sources": ["joshua", "joshau", "koshua"]},
    {"target": "Linda", "sources": ["linda"]},
    {"target": "Daniel", "sources": ["daniel", "丹尼尔", "denial"]},
    {"target": "Thomas", "sources": ["thomas", "托马斯"]},
    {"target": "Kelvin", "sources": ["kelvin", "elvin", "Elvin"]},
    {"target": "Stella", "sources": ["stella"]},
    {"target": "Ted", "sources": ["ted"]},
    {"target": "Vanessa", "sources": ["vanessa"]},
    {"target": "Sherry", "sources": ["sherry"]},
    {"target": "Hun", "sources": ["hun"]},
    {"target": "Roy", "sources": ["roy"]},
    {"target": "Miranda", "sources": ["miranda"]},
    {"target": "Hannah", "sources": ["hannah"]},
    {"target": "Maureen", "sources": ["maureen", "marien", "marine"]},

    # 中等确定性
    {"target": "王建宇", "sources": ["王健宇", "jianyu", "建宇"]},
    {"target": "刘彦", "sources": ["刘yan", "liuyan", "yan", "Yan", "yanny"]},
    {"target": "沫沫", "sources": ["momo"]},
    {"target": "西卡", "sources": ["xika", "xiia"]},
    {"target": "紫萱", "sources": ["zixuan"]},
    {"target": "史雄飞", "sources": ["雄飞"]},
    {"target": "宝丹", "sources": ["宝单", "宝蛋", "爆弹"]},
    {"target": "静", "sources": ["jing"]},
]

CONVERSATION = "吉月"

def merge_person(session, source_name, target_name, conv_name):
    """合并两个Person实体"""
    # 获取所有关系类型
    rel_types = session.run("""
        MATCH (s:Person {name: $source, conversation_name: $conv})-[r]-()
        RETURN DISTINCT type(r) as rel_type
    """, source=source_name, conv=conv_name)

    for record in rel_types:
        rel_type = record['rel_type']

        # 转移出边
        session.run(f"""
            MATCH (s:Person {{name: $source, conversation_name: $conv}})-[r:{rel_type}]->(other)
            MATCH (t:Person {{name: $target, conversation_name: $conv}})
            WHERE NOT (t)-[:{rel_type}]->(other)
            MERGE (t)-[r2:{rel_type}]->(other)
            SET r2 = properties(r)
            DELETE r
        """, source=source_name, target=target_name, conv=conv_name)

        # 转移入边
        session.run(f"""
            MATCH (other)-[r:{rel_type}]->(s:Person {{name: $source, conversation_name: $conv}})
            MATCH (t:Person {{name: $target, conversation_name: $conv}})
            WHERE NOT (other)-[:{rel_type}]->(t)
            MERGE (other)-[r2:{rel_type}]->(t)
            SET r2 = properties(r)
            DELETE r
        """, source=source_name, target=target_name, conv=conv_name)

    # 删除源节点（使用DETACH DELETE确保删除所有关系）
    session.run("""
        MATCH (s:Person {name: $source, conversation_name: $conv})
        DETACH DELETE s
    """, source=source_name, conv=conv_name)

def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    print("=" * 80)
    print("执行手工确认的Person实体合并")
    print("=" * 80)

    with driver.session() as session:
        # 统计前
        before = session.run(
            'MATCH (p:Person {conversation_name: $conv}) RETURN count(p) as total',
            conv=CONVERSATION
        ).single()['total']

        print(f"\n合并前: {before}个Person节点")
        print(f"\n开始合并 {len(MERGE_GROUPS)} 组实体...")
        print("-" * 80)

        merge_count = 0
        for i, group in enumerate(MERGE_GROUPS, 1):
            target = group['target']
            sources = group['sources']

            print(f"\n[{i}/{len(MERGE_GROUPS)}] {target}组:")

            for source in sources:
                # 检查源节点是否存在
                exists = session.run("""
                    MATCH (p:Person {name: $name, conversation_name: $conv})
                    RETURN count(p) as cnt
                """, name=source, conv=CONVERSATION).single()['cnt']

                if exists > 0:
                    merge_person(session, source, target, CONVERSATION)
                    print(f"  ✓ {source} → {target}")
                    merge_count += 1
                else:
                    print(f"  ⊘ {source} (不存在，跳过)")

        # 统计后
        after = session.run(
            'MATCH (p:Person {conversation_name: $conv}) RETURN count(p) as total',
            conv=CONVERSATION
        ).single()['total']

        print("\n" + "=" * 80)
        print(f"合并完成！")
        print(f"  合并前: {before}个节点")
        print(f"  合并后: {after}个节点")
        print(f"  减少: {before - after}个节点")
        print(f"  执行: {merge_count}次合并操作")
        print("=" * 80)

    driver.close()

if __name__ == '__main__':
    main()
