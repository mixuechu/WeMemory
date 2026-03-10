#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从提取的JSON构建Neo4j知识图谱"""

import os
import sys
import json
from pathlib import Path
from neo4j import GraphDatabase

# 设置UTF-8编码（Windows兼容）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Neo4j连接配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password123"

DEBUG_DIR = Path("knowledge_graph/debug")


class Neo4jGraphBuilder:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def clear_database(self):
        """清空数据库"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("✅ Database cleared")

    def create_person(self, person_data, conversation_name):
        """创建Person节点"""
        query = """
        MERGE (p:Person {name: $name, conversation_name: $conv})
        SET p.is_user = $is_user,
            p.relationship_to_user = $relationship_to_user,
            p.occupation = $occupation,
            p.company = $company,
            p.aliases = $aliases,
            p.confidence = $confidence,
            p.conversation_name = $conv
        RETURN p
        """
        with self.driver.session() as session:
            session.run(
                query,
                name=person_data['name'],
                conv=conversation_name,
                is_user=person_data.get('is_user', False),
                relationship_to_user=person_data.get('relationship_to_user'),
                occupation=person_data.get('occupation'),
                company=person_data.get('company'),
                aliases=person_data.get('aliases', []),
                confidence=person_data.get('confidence', 0.0)
            )

    def create_organization(self, org_data, conversation_name):
        """创建Organization节点"""
        query = """
        MERGE (o:Organization {name: $name, conversation_name: $conv})
        SET o.type = $type,
            o.industry = $industry,
            o.confidence = $confidence,
            o.conversation_name = $conv
        RETURN o
        """
        with self.driver.session() as session:
            session.run(
                query,
                name=org_data['name'],
                conv=conversation_name,
                type=org_data.get('type'),
                industry=org_data.get('industry'),
                confidence=org_data.get('confidence', 0.0)
            )

    def create_topic(self, topic_data, conversation_name):
        """创建Topic节点"""
        query = """
        MERGE (t:Topic {name: $name, conversation_name: $conv})
        SET t.type = $type,
            t.keywords = $keywords,
            t.confidence = $confidence,
            t.conversation_name = $conv
        RETURN t
        """
        with self.driver.session() as session:
            session.run(
                query,
                name=topic_data['name'],
                conv=conversation_name,
                type=topic_data.get('type'),
                keywords=topic_data.get('keywords', []),
                confidence=topic_data.get('confidence', 0.0)
            )

    def create_location(self, location_data, conversation_name):
        """创建Location节点"""
        query = """
        MERGE (l:Location {name: $name, conversation_name: $conv})
        SET l.type = $type,
            l.parent_location = $parent_location,
            l.confidence = $confidence,
            l.conversation_name = $conv
        RETURN l
        """
        with self.driver.session() as session:
            session.run(
                query,
                name=location_data['name'],
                conv=conversation_name,
                type=location_data.get('type'),
                parent_location=location_data.get('parent_location'),
                confidence=location_data.get('confidence', 0.0)
            )

    def create_event(self, event_data, conversation_name):
        """创建Event节点并自动创建PARTICIPATED_IN关系"""
        event_name = event_data['name']
        participants = event_data.get('participants', [])

        # 生成event_id（如果没有的话）
        import hashlib
        event_id = event_data.get('event_id')
        if not event_id:
            event_id = hashlib.md5(f"{conversation_name}_{event_name}".encode()).hexdigest()[:16] + f"_{event_name}"

        # 1. 创建Event节点
        query = """
        MERGE (e:Event {event_id: $event_id, conversation_name: $conv})
        SET e.name = $name,
            e.type = $type,
            e.description = $description,
            e.time_reference = $time_reference,
            e.time_description = $time_description,
            e.inferred_time = $inferred_time,
            e.time_precision = $time_precision,
            e.participants = $participants,
            e.location = $location,
            e.confidence = $confidence,
            e.conversation_name = $conv
        RETURN e
        """
        with self.driver.session() as session:
            session.run(
                query,
                event_id=event_id,
                conv=conversation_name,
                name=event_name,
                type=event_data.get('type'),
                description=event_data.get('description'),
                time_reference=event_data.get('time_reference'),
                time_description=event_data.get('time_description'),
                inferred_time=event_data.get('inferred_time'),
                time_precision=event_data.get('time_precision'),
                participants=participants,
                location=event_data.get('location'),
                confidence=event_data.get('confidence', 0.0)
            )

            # 2. 自动为每个participant创建PARTICIPATED_IN关系
            created_relationships = 0
            for participant in participants:
                try:
                    session.run("""
                        MATCH (p:Person {name: $person, conversation_name: $conv})
                        MATCH (e:Event {event_id: $event_id, conversation_name: $conv})
                        MERGE (p)-[r:PARTICIPATED_IN]->(e)
                        SET r.confidence = 0.9
                    """, person=participant, event_id=event_id, conv=conversation_name)
                    created_relationships += 1
                except Exception as e:
                    # Person可能还不存在，稍后会创建
                    pass

            if created_relationships > 0:
                print(f"      ✓ 自动创建 {created_relationships} 个 PARTICIPATED_IN 关系")

        return event_id

    def create_relationship(self, rel_data):
        """创建关系"""
        rel_type = rel_data['type']
        source = rel_data['source']
        target = rel_data['target']
        source_type = rel_data.get('source_type', 'Person')
        target_type = rel_data.get('target_type', 'Person')
        properties = rel_data.get('properties', {})

        # 构建Cypher查询
        query = f"""
        MATCH (source:{source_type} {{name: $source}})
        MATCH (target:{target_type} {{name: $target}})
        MERGE (source)-[r:{rel_type}]->(target)
        SET r.confidence = $confidence,
            r.context = $context
        RETURN r
        """

        # 添加properties到关系
        if properties:
            for key, value in properties.items():
                query = query.replace("RETURN r", f"SET r.{key} = ${key}\nRETURN r")

        with self.driver.session() as session:
            params = {
                'source': source,
                'target': target,
                'confidence': rel_data.get('confidence', 0.0),
                'context': rel_data.get('context', '')
            }
            params.update(properties)

            try:
                session.run(query, **params)
            except Exception as e:
                print(f"  ⚠️ Failed to create relationship: {rel_type} from {source} to {target}")
                print(f"     Error: {e}")

    def load_extraction_file(self, filepath):
        """加载提取结果文件并构建图谱"""
        print(f"\n📂 Loading: {filepath.name}")

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not data.get('success'):
            print(f"  ❌ Extraction failed, skipping")
            return

        entities = data['entities']
        conv_name = data['conversation']['conversation_name']

        print(f"  Conversation: {conv_name}")

        # 创建节点
        print(f"  Creating nodes...")

        # People
        for person in entities.get('people', []):
            self.create_person(person, conv_name)
        print(f"    ✅ {len(entities.get('people', []))} People")

        # Organizations
        for org in entities.get('organizations', []):
            self.create_organization(org, conv_name)
        print(f"    ✅ {len(entities.get('organizations', []))} Organizations")

        # Topics
        for topic in entities.get('topics', []):
            self.create_topic(topic, conv_name)
        print(f"    ✅ {len(entities.get('topics', []))} Topics")

        # Locations
        for location in entities.get('locations', []):
            self.create_location(location, conv_name)
        print(f"    ✅ {len(entities.get('locations', []))} Locations")

        # Events
        for event in entities.get('events', []):
            self.create_event(event, conv_name)
        print(f"    ✅ {len(entities.get('events', []))} Events")

        # 创建关系
        print(f"  Creating relationships...")
        relationships = entities.get('relationships', [])
        success_count = 0
        for rel in relationships:
            try:
                self.create_relationship(rel)
                success_count += 1
            except:
                pass
        print(f"    ✅ {success_count}/{len(relationships)} Relationships")


def run_test_queries(driver):
    """运行测试查询"""
    print("\n" + "=" * 80)
    print("🔍 Running Test Queries")
    print("=" * 80)

    queries = [
        {
            "name": "Q1: 谁在西安发改委工作？",
            "cypher": """
                MATCH (p:Person)-[:WORKS_AT]->(o:Organization {name: '西安发改委'})
                RETURN p.name AS person, p.occupation AS occupation
            """
        },
        {
            "name": "Q2: 谁在国税局工作？",
            "cypher": """
                MATCH (p:Person)-[:WORKS_AT]->(o:Organization {name: '国税局'})
                RETURN p.name AS person
            """
        },
        {
            "name": "Q3: 谁在水资委工作？",
            "cypher": """
                MATCH (p:Person)-[:WORKS_AT]->(o:Organization {name: '水资委'})
                RETURN p.name AS person
            """
        },
        {
            "name": "Q4: 米雪川认识哪些人？",
            "cypher": """
                MATCH (米雪川:Person {name: '米雪川'})-[:KNOWS]->(friend:Person)
                RETURN friend.name AS friend
            """
        },
        {
            "name": "Q5: 北葵向暖认识哪些人？",
            "cypher": """
                MATCH (北葵向暖:Person {name: '北葵向暖'})-[:KNOWS]->(person:Person)
                RETURN person.name AS person
            """
        },
        {
            "name": "Q6: 米雪川讨论过哪些主题？",
            "cypher": """
                MATCH (米雪川:Person {name: '米雪川'})-[:DISCUSSED_TOPIC]->(topic:Topic)
                RETURN topic.name AS topic
            """
        },
        {
            "name": "Q7: 谁和谁有家人关系？",
            "cypher": """
                MATCH (p1:Person)-[:FAMILY_OF]->(p2:Person)
                RETURN p1.name AS person1, p2.name AS person2
            """
        },
        {
            "name": "Q8: 所有人物及其别名",
            "cypher": """
                MATCH (p:Person)
                WHERE size(p.aliases) > 0
                RETURN p.name AS name, p.aliases AS aliases
            """
        },
        {
            "name": "Q9: 2016年有哪些事件？",
            "cypher": """
                MATCH (e:Event)
                WHERE e.inferred_time STARTS WITH '2016'
                RETURN e.name AS event, e.inferred_time AS time
            """
        },
        {
            "name": "Q10: 所有组织列表",
            "cypher": """
                MATCH (o:Organization)
                RETURN o.name AS organization, o.type AS type, o.industry AS industry
            """
        }
    ]

    with driver.session() as session:
        for i, query_info in enumerate(queries, 1):
            print(f"\n{query_info['name']}")
            print("-" * 80)

            try:
                result = session.run(query_info['cypher'])
                records = list(result)

                if records:
                    for record in records:
                        print(f"  {dict(record)}")
                    print(f"  (共 {len(records)} 条结果)")
                else:
                    print("  ❌ 无结果")
            except Exception as e:
                print(f"  ❌ 查询失败: {e}")


def main():
    print("=" * 80)
    print("🏗️ Building Neo4j Knowledge Graph")
    print("=" * 80)

    # 连接Neo4j
    print(f"\n📡 Connecting to Neo4j: {NEO4J_URI}")
    builder = Neo4jGraphBuilder(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    try:
        # 清空数据库
        builder.clear_database()

        # 加载提取结果文件
        extraction_files = list(DEBUG_DIR.glob("test_*.json"))
        print(f"\n📁 Found {len(extraction_files)} extraction files")

        for filepath in extraction_files:
            builder.load_extraction_file(filepath)

        # 统计
        print("\n" + "=" * 80)
        print("📊 Graph Statistics")
        print("=" * 80)

        with builder.driver.session() as session:
            # 节点统计
            node_stats = session.run("""
                MATCH (n)
                RETURN labels(n)[0] AS label, count(*) AS count
                ORDER BY count DESC
            """)

            print("\nNodes:")
            total_nodes = 0
            for record in node_stats:
                label = record['label']
                count = record['count']
                total_nodes += count
                print(f"  - {label}: {count}")
            print(f"  Total: {total_nodes}")

            # 关系统计
            rel_stats = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) AS type, count(*) AS count
                ORDER BY count DESC
            """)

            print("\nRelationships:")
            total_rels = 0
            for record in rel_stats:
                rel_type = record['type']
                count = record['count']
                total_rels += count
                print(f"  - {rel_type}: {count}")
            print(f"  Total: {total_rels}")

        # 运行测试查询
        run_test_queries(builder.driver)

        print("\n" + "=" * 80)
        print("✅ Graph building complete!")
        print("=" * 80)
        print(f"\n💡 Neo4j Browser: http://localhost:7474")
        print(f"   Username: {NEO4J_USER}")
        print(f"   Password: {NEO4J_PASSWORD}")

    finally:
        builder.close()


if __name__ == '__main__':
    main()
