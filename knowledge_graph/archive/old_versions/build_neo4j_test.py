#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从JY和吉月的提取结果构建Neo4j图谱"""

import json
import sys
import io
from pathlib import Path
from neo4j import GraphDatabase
from collections import defaultdict

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Neo4j连接配置（请修改密码）
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password123"

# 提取目录
JY_DIR = Path("../extractions/test_jy_only")
JIYUE_DIR = Path("../extractions/test_jiyue_only")


def clear_database(driver):
    """清空数据库"""
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        print("✅ 数据库已清空")


def create_indexes(driver):
    """创建索引"""
    with driver.session() as session:
        # Person索引 - 使用(name, conversation_name)组合
        session.run("CREATE INDEX person_composite IF NOT EXISTS FOR (p:Person) ON (p.name, p.conversation_name)")
        session.run("CREATE INDEX topic_name IF NOT EXISTS FOR (t:Topic) ON (t.name)")
        session.run("CREATE INDEX org_name IF NOT EXISTS FOR (o:Organization) ON (o.name)")
        session.run("CREATE INDEX event_id IF NOT EXISTS FOR (e:Event) ON (e.event_id)")
        print("✅ 索引已创建")


def load_extractions(directories):
    """加载所有提取文件"""
    all_files = []
    for directory in directories:
        if directory.exists():
            files = list(directory.glob("session_*.json"))
            all_files.extend(files)
            print(f"  {directory.name}: {len(files)} 文件")
    return all_files


def build_graph(driver, extraction_files):
    """构建图谱"""
    print(f"\n开始构建图谱...")
    print(f"总文件数: {len(extraction_files)}")

    stats = {
        'people': 0,
        'topics': 0,
        'organizations': 0,
        'events': 0,
        'locations': 0,
        'relationships': 0,
        'failed': 0,
    }

    for idx, f in enumerate(extraction_files):
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)

        if not data.get('success'):
            stats['failed'] += 1
            continue

        conv_name = data['conversation']['conversation_name']
        session_id = data['conversation']['session_id']
        entities = data['entities']

        with driver.session() as session:
            # 1. 创建People节点
            # 使用(name, conversation_name)作为唯一标识
            for person in entities.get('people', []):
                session.run("""
                    MERGE (p:Person {name: $name, conversation_name: $conv_name})
                    SET p.is_user = $is_user,
                        p.relationship_to_user = $relationship,
                        p.occupation = $occupation,
                        p.company = $company,
                        p.personality = $personality
                """,
                    name=person['name'],
                    conv_name=conv_name,
                    is_user=person.get('is_user', False),
                    relationship=person.get('relationship_to_user'),
                    occupation=person.get('occupation'),
                    company=person.get('company'),
                    personality=person.get('personality', [])
                )
                stats['people'] += 1

            # 2. 创建Topic节点（全局唯一，不区分conversation）
            for topic in entities.get('topics', []):
                session.run("""
                    MERGE (t:Topic {name: $name})
                    SET t.type = $type
                """,
                    name=topic['name'],
                    type=topic.get('type')
                )
                stats['topics'] += 1

            # 3. 创建Organization节点（全局唯一）
            for org in entities.get('organizations', []):
                session.run("""
                    MERGE (o:Organization {name: $name})
                    SET o.type = $type,
                        o.industry = $industry
                """,
                    name=org['name'],
                    type=org.get('type'),
                    industry=org.get('industry')
                )
                stats['organizations'] += 1

            # 4. 创建Location节点（全局唯一）
            for loc in entities.get('locations', []):
                session.run("""
                    MERGE (l:Location {name: $name})
                    SET l.type = $type,
                        l.parent_location = $parent,
                        l.notes = $notes
                """,
                    name=loc['name'],
                    type=loc.get('type'),
                    parent=loc.get('parent_location'),
                    notes=loc.get('notes')
                )
                stats['locations'] += 1

            # 5. 创建Event节点（每个event唯一）
            for event in entities.get('events', []):
                event_id = f"{session_id}_{event['name']}"
                session.run("""
                    CREATE (e:Event {
                        event_id: $event_id,
                        name: $name,
                        type: $type,
                        description: $description,
                        conversation_name: $conv_name,
                        time_reference: $time_ref,
                        inferred_time: $inferred_time
                    })
                """,
                    event_id=event_id,
                    name=event['name'],
                    type=event.get('type'),
                    description=event.get('description'),
                    conv_name=conv_name,
                    time_ref=event.get('time_reference'),
                    inferred_time=event.get('inferred_time')
                )
                stats['events'] += 1

            # 6. 创建关系
            for rel in entities.get('relationships', []):
                rel_type = rel['type']
                source = rel['source']
                target = rel['target']
                source_type = rel.get('source_type', 'Person')
                target_type = rel.get('target_type', 'Person')

                # 根据实体类型构建查询
                try:
                    if source_type == 'Person' and target_type == 'Person':
                        # Person -> Person
                        session.run(f"""
                            MATCH (s:Person {{name: $source, conversation_name: $conv_name}})
                            MATCH (t:Person {{name: $target, conversation_name: $conv_name}})
                            MERGE (s)-[r:{rel_type}]->(t)
                            SET r.confidence = $confidence
                        """,
                            source=source,
                            target=target,
                            conv_name=conv_name,
                            confidence=rel.get('confidence', 0.9)
                        )
                    elif source_type == 'Person' and target_type == 'Topic':
                        # Person -> Topic
                        session.run(f"""
                            MATCH (s:Person {{name: $source, conversation_name: $conv_name}})
                            MATCH (t:Topic {{name: $target}})
                            MERGE (s)-[r:{rel_type}]->(t)
                            SET r.confidence = $confidence
                        """,
                            source=source,
                            target=target,
                            conv_name=conv_name,
                            confidence=rel.get('confidence', 0.9)
                        )
                    elif source_type == 'Person' and target_type == 'Organization':
                        # Person -> Organization
                        session.run(f"""
                            MATCH (s:Person {{name: $source, conversation_name: $conv_name}})
                            MATCH (t:Organization {{name: $target}})
                            MERGE (s)-[r:{rel_type}]->(t)
                            SET r.confidence = $confidence
                        """,
                            source=source,
                            target=target,
                            conv_name=conv_name,
                            confidence=rel.get('confidence', 0.9)
                        )
                    elif source_type == 'Person' and target_type == 'Location':
                        # Person -> Location
                        session.run(f"""
                            MATCH (s:Person {{name: $source, conversation_name: $conv_name}})
                            MATCH (t:Location {{name: $target}})
                            MERGE (s)-[r:{rel_type}]->(t)
                            SET r.confidence = $confidence
                        """,
                            source=source,
                            target=target,
                            conv_name=conv_name,
                            confidence=rel.get('confidence', 0.9)
                        )

                    stats['relationships'] += 1
                except Exception as e:
                    # 跳过失败的关系
                    pass

        if (idx + 1) % 100 == 0:
            print(f"  进度: {idx + 1}/{len(extraction_files)}")

    print(f"\n✅ 图谱构建完成")
    print(f"  Person节点: {stats['people']}")
    print(f"  Topic节点: {stats['topics']}")
    print(f"  Organization节点: {stats['organizations']}")
    print(f"  Location节点: {stats['locations']}")
    print(f"  Event节点: {stats['events']}")
    print(f"  关系数: {stats['relationships']}")
    print(f"  失败文件: {stats['failed']}")


def test_queries(driver):
    """测试查询"""
    print("\n" + "=" * 80)
    print("测试查询")
    print("=" * 80)

    with driver.session() as session:
        # 查询1: 节点统计
        print("\n【查询1】节点统计:")
        print("-" * 80)
        result = session.run("""
            MATCH (n)
            RETURN labels(n)[0] as type, count(n) as count
            ORDER BY count DESC
        """)
        for record in result:
            print(f"  {record['type']}: {record['count']}")

        # 查询2: 去重验证 - Person节点中同名实体
        print("\n【查询2】去重验证 - Person实体统计:")
        print("-" * 80)
        result = session.run("""
            MATCH (p:Person)
            RETURN p.name as name, p.conversation_name as conv, count(*) as cnt
            ORDER BY name
            LIMIT 10
        """)
        for record in result:
            print(f"  {record['name']} (对话:{record['conv']}): {record['cnt']}个节点")

        # 查询3: 米雪川讨论过的主题
        print("\n【查询3】米雪川讨论过的主题 (Top 10):")
        print("-" * 80)
        result = session.run("""
            MATCH (p:Person {name: '米雪川'})-[:DISCUSSED_TOPIC]->(t:Topic)
            RETURN DISTINCT t.name as topic, count(*) as mentions
            ORDER BY mentions DESC
            LIMIT 10
        """)
        for record in result:
            print(f"  {record['topic']}: {record['mentions']} 次")

        # 查询4: 吉月的家人
        print("\n【查询4】吉月的家人:")
        print("-" * 80)
        result = session.run("""
            MATCH (j:Person {conversation_name: '吉月'})-[:FAMILY_OF]->(f:Person)
            WHERE j.name = '吉月'
            RETURN DISTINCT f.name as family_member
        """)
        family_members = [record['family_member'] for record in result]
        if family_members:
            for member in family_members:
                print(f"  - {member}")
        else:
            print("  (未找到)")

        # 查询5: 跨用户连接（如果JY和吉月有共同认识的人）
        print("\n【查询5】JY和吉月的共同联系:")
        print("-" * 80)
        result = session.run("""
            MATCH (jy:Person {conversation_name: 'JY'})-[:KNOWS]->(common:Person)
            MATCH (jiyue:Person {conversation_name: '吉月'})-[:KNOWS]->(common)
            RETURN DISTINCT common.name as common_person
            LIMIT 5
        """)
        common_people = [record['common_person'] for record in result]
        if common_people:
            for person in common_people:
                print(f"  - {person}")
        else:
            print("  (暂无共同联系)")

        # 查询6: 最常讨论的主题
        print("\n【查询6】最常讨论的主题 (Top 10):")
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
    print("从JY和吉月提取结果构建Neo4j图谱")
    print("=" * 80)

    # 连接Neo4j
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        print(f"\n✅ 已连接到Neo4j: {NEO4J_URI}")
    except Exception as e:
        print(f"\n❌ 无法连接到Neo4j: {e}")
        print("请确保:")
        print("  1. Neo4j已启动")
        print("  2. 修改脚本中的NEO4J_PASSWORD")
        return

    try:
        # 加载提取文件
        print("\n加载提取文件:")
        extraction_files = load_extractions([JY_DIR, JIYUE_DIR])

        if not extraction_files:
            print("❌ 没有找到提取文件")
            return

        # 清空数据库
        print("\n清空数据库...")
        clear_database(driver)

        # 创建索引
        print("\n创建索引...")
        create_indexes(driver)

        # 构建图谱
        build_graph(driver, extraction_files)

        # 测试查询
        test_queries(driver)

        print("\n" + "=" * 80)
        print("✅ 全部完成")
        print("=" * 80)
        print("\n💡 你可以打开Neo4j Browser查看图谱:")
        print("   http://localhost:7474")

    finally:
        driver.close()


if __name__ == '__main__':
    main()
