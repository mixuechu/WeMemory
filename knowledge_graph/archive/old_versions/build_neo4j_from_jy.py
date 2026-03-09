#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从JY提取结果构建Neo4j图并测试"""

import json
import sys
import io
from pathlib import Path
from neo4j import GraphDatabase

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Neo4j连接配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your_password"  # 需要替换

EXTRACTION_DIR = Path("../extractions/test_jy_only")


def clear_database(driver):
    """清空数据库"""
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        print("✅ 数据库已清空")


def create_indexes(driver):
    """创建索引"""
    with driver.session() as session:
        # Person索引
        session.run("CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name)")
        session.run("CREATE INDEX person_conv IF NOT EXISTS FOR (p:Person) ON (p.conversation_name)")

        # Topic索引
        session.run("CREATE INDEX topic_name IF NOT EXISTS FOR (t:Topic) ON (t.name)")

        print("✅ 索引已创建")


def build_graph(driver):
    """构建图谱"""
    files = list(EXTRACTION_DIR.glob("session_*.json"))

    print(f"\n开始构建图谱...")
    print(f"总文件数: {len(files)}")

    stats = {
        'people': 0,
        'topics': 0,
        'events': 0,
        'relationships': 0
    }

    for idx, f in enumerate(files):
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)

        if not data.get('success'):
            continue

        conv_name = data['conversation']['conversation_name']
        entities = data['entities']

        with driver.session() as session:
            # 创建People节点（使用conversation_name作为唯一标识）
            for person in entities.get('people', []):
                session.run("""
                    MERGE (p:Person {name: $name, conversation_name: $conv_name})
                    SET p.is_user = $is_user,
                        p.relationship_to_user = $relationship
                """,
                    name=person['name'],
                    conv_name=conv_name,
                    is_user=person.get('is_user', False),
                    relationship=person.get('relationship_to_user')
                )
                stats['people'] += 1

            # 创建Topic节点
            for topic in entities.get('topics', []):
                session.run("""
                    MERGE (t:Topic {name: $name})
                    SET t.type = $type
                """,
                    name=topic['name'],
                    type=topic.get('type')
                )
                stats['topics'] += 1

            # 创建Event节点
            for event in entities.get('events', []):
                session.run("""
                    CREATE (e:Event {
                        name: $name,
                        type: $type,
                        description: $description,
                        conversation_name: $conv_name
                    })
                """,
                    name=event['name'],
                    type=event.get('type'),
                    description=event.get('description'),
                    conv_name=conv_name
                )
                stats['events'] += 1

            # 创建关系
            for rel in entities.get('relationships', []):
                rel_type = rel['type']
                source = rel['source']
                target = rel['target']
                source_type = rel.get('source_type', 'Person')
                target_type = rel.get('target_type', 'Person')

                # 根据实体类型构建查询
                if source_type == 'Person' and target_type == 'Person':
                    session.run(f"""
                        MATCH (s:Person {{name: $source, conversation_name: $conv_name}})
                        MATCH (t:Person {{name: $target, conversation_name: $conv_name}})
                        MERGE (s)-[r:{rel_type}]->(t)
                    """,
                        source=source,
                        target=target,
                        conv_name=conv_name
                    )
                elif source_type == 'Person' and target_type == 'Topic':
                    session.run(f"""
                        MATCH (s:Person {{name: $source, conversation_name: $conv_name}})
                        MATCH (t:Topic {{name: $target}})
                        MERGE (s)-[r:{rel_type}]->(t)
                    """,
                        source=source,
                        target=target,
                        conv_name=conv_name
                    )

                stats['relationships'] += 1

        if (idx + 1) % 10 == 0:
            print(f"  进度: {idx + 1}/{len(files)}")

    print(f"\n✅ 图谱构建完成")
    print(f"  People节点: {stats['people']}")
    print(f"  Topic节点: {stats['topics']}")
    print(f"  Event节点: {stats['events']}")
    print(f"  关系数: {stats['relationships']}")


def test_queries(driver):
    """测试查询"""
    print("\n" + "=" * 80)
    print("测试查询")
    print("=" * 80)

    with driver.session() as session:
        # 查询1: 统计节点数
        print("\n【查询1】节点统计:")
        print("-" * 80)
        result = session.run("""
            MATCH (n)
            RETURN labels(n)[0] as type, count(n) as count
            ORDER BY count DESC
        """)
        for record in result:
            print(f"  {record['type']}: {record['count']}")

        # 查询2: 米雪川讨论过的主题
        print("\n【查询2】米雪川讨论过的主题:")
        print("-" * 80)
        result = session.run("""
            MATCH (p:Person {name: '米雪川'})-[:DISCUSSED_TOPIC]->(t:Topic)
            RETURN DISTINCT t.name as topic
            ORDER BY topic
            LIMIT 10
        """)
        for record in result:
            print(f"  - {record['topic']}")

        # 查询3: JY在不同对话中被提取了多少次？（测试去重）
        print("\n【查询3】JY实体去重测试:")
        print("-" * 80)
        result = session.run("""
            MATCH (p:Person {name: 'JY'})
            RETURN p.conversation_name as conv, count(*) as count
        """)
        records = list(result)
        print(f"  JY作为实体出现: {len(records)} 次")
        print(f"  说明: JY在每个对话中都是独立的Person节点")
        print(f"  (因为用conversation_name区分，'JY'在对话'JY'中是唯一的)")

        # 查询4: 米雪川和JY讨论过什么？
        print("\n【查询4】米雪川和JY讨论过的主题:")
        print("-" * 80)
        result = session.run("""
            MATCH (m:Person {name: '米雪川'})-[:DISCUSSED_WITH]->(j:Person {name: 'JY'})
            RETURN DISTINCT j.conversation_name as conv
            LIMIT 5
        """)
        for record in result:
            print(f"  对话: {record['conv']}")

        # 查询5: 最常讨论的主题
        print("\n【查询5】最常讨论的主题 (Top 10):")
        print("-" * 80)
        result = session.run("""
            MATCH (p:Person)-[:DISCUSSED_TOPIC]->(t:Topic)
            RETURN t.name as topic, count(*) as mentions
            ORDER BY mentions DESC
            LIMIT 10
        """)
        for record in result:
            print(f"  {record['topic']}: {record['mentions']} 次")


def main():
    """主函数"""
    print("=" * 80)
    print("从JY提取结果构建Neo4j图谱")
    print("=" * 80)

    # 连接Neo4j
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        print(f"\n✅ 已连接到Neo4j: {NEO4J_URI}")
    except Exception as e:
        print(f"\n❌ 无法连接到Neo4j: {e}")
        print("请确保:")
        print("  1. Neo4j已启动")
        print("  2. 修改脚本中的NEO4J_PASSWORD")
        return

    try:
        # 清空数据库
        clear_database(driver)

        # 创建索引
        create_indexes(driver)

        # 构建图谱
        build_graph(driver)

        # 测试查询
        test_queries(driver)

        print("\n" + "=" * 80)
        print("✅ 全部完成")
        print("=" * 80)

    finally:
        driver.close()


if __name__ == '__main__':
    main()
