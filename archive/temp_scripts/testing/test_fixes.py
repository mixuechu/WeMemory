#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试修复后的代码"""

import sys
import io

# 先导入，避免stdout冲突
from build_neo4j_graph import Neo4jGraphBuilder

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def test_event_person_relationship():
    """测试Event-Person自动关系创建"""
    print("=" * 80)
    print("测试Event-Person自动关系创建")
    print("=" * 80)

    builder = Neo4jGraphBuilder(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password123"
    )

    # 测试数据
    test_conv = "测试对话"

    # 1. 创建Person
    print("\n1. 创建测试Person...")
    person1 = {
        'name': '测试人物A',
        'is_user': False,
        'aliases': ['A'],
        'confidence': 1.0
    }
    person2 = {
        'name': '测试人物B',
        'is_user': False,
        'aliases': ['B'],
        'confidence': 1.0
    }

    builder.create_person(person1, test_conv)
    builder.create_person(person2, test_conv)
    print("  ✅ 创建了2个Person")

    # 2. 创建Event（带participants）
    print("\n2. 创建测试Event（带participants）...")
    event = {
        'name': '测试聚会',
        'type': '聚会',
        'description': '测试人物A和B的聚会',
        'participants': ['测试人物A', '测试人物B'],
        'time_reference': 'past',
        'confidence': 1.0
    }

    event_id = builder.create_event(event, test_conv)
    print(f"  ✅ 创建Event: {event_id}")

    # 3. 验证关系
    print("\n3. 验证PARTICIPATED_IN关系...")
    with builder.driver.session() as session:
        result = session.run("""
            MATCH (p:Person)-[r:PARTICIPATED_IN]->(e:Event {event_id: $event_id, conversation_name: $conv})
            RETURN p.name as person, e.name as event
        """, event_id=event_id, conv=test_conv)

        relationships = list(result)
        print(f"  找到 {len(relationships)} 个关系:")
        for rel in relationships:
            print(f"    - {rel['person']} -> {rel['event']}")

    # 4. 清理测试数据
    print("\n4. 清理测试数据...")
    with builder.driver.session() as session:
        session.run("""
            MATCH (n {conversation_name: $conv})
            DETACH DELETE n
        """, conv=test_conv)
    print("  ✅ 测试数据已清理")

    builder.close()

    if len(relationships) == 2:
        print("\n" + "=" * 80)
        print("✅ 测试通过！Event-Person关系自动创建成功！")
        print("=" * 80)
        return True
    else:
        print("\n" + "=" * 80)
        print(f"❌ 测试失败！期望2个关系，实际{len(relationships)}个")
        print("=" * 80)
        return False


def test_conversation_name_fields():
    """测试所有节点都有conversation_name字段"""
    print("\n" + "=" * 80)
    print("测试conversation_name字段")
    print("=" * 80)

    builder = Neo4jGraphBuilder(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password123"
    )

    test_conv = "测试对话2"

    # 创建各类节点
    print("\n1. 创建测试节点...")
    builder.create_person({'name': '测试人物C', 'confidence': 1.0}, test_conv)
    builder.create_organization({'name': '测试公司', 'type': '公司', 'confidence': 1.0}, test_conv)
    builder.create_topic({'name': '测试主题', 'type': '技术', 'confidence': 1.0}, test_conv)
    builder.create_location({'name': '测试地点', 'type': '城市', 'confidence': 1.0}, test_conv)
    builder.create_event({
        'name': '测试事件',
        'type': '会议',
        'participants': [],
        'confidence': 1.0
    }, test_conv)

    # 验证所有节点都有conversation_name
    print("\n2. 验证conversation_name字段...")
    with builder.driver.session() as session:
        for label in ['Person', 'Organization', 'Topic', 'Location', 'Event']:
            result = session.run(f"""
                MATCH (n:{label} {{conversation_name: $conv}})
                RETURN count(n) as cnt
            """, conv=test_conv)
            count = result.single()['cnt']
            print(f"  {label}: {count}个节点 ✅" if count > 0 else f"  {label}: 未找到节点 ❌")

    # 清理
    print("\n3. 清理测试数据...")
    with builder.driver.session() as session:
        session.run("""
            MATCH (n {conversation_name: $conv})
            DETACH DELETE n
        """, conv=test_conv)

    builder.close()
    print("\n✅ conversation_name字段测试完成")


if __name__ == '__main__':
    print("\n🧪 开始测试修复...")
    print()

    # 测试1：Event-Person自动关系
    success1 = test_event_person_relationship()

    # 测试2：conversation_name字段
    test_conversation_name_fields()

    print("\n" + "=" * 80)
    if success1:
        print("🎉 所有测试通过！修复成功！")
    else:
        print("⚠️ 部分测试失败，请检查")
    print("=" * 80)
