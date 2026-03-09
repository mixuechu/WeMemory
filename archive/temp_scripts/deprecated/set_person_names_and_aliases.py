#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""设置Person实体的正式名称和别名"""

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
CONVERSATION = '吉月'

def merge_person(session, source_name, target_name, conv_name):
    """合并Person实体"""
    # 检查源节点是否存在
    exists = session.run("""
        MATCH (p:Person {name: $name, conversation_name: $conv})
        RETURN count(p) as cnt
    """, name=source_name, conv=conv_name).single()['cnt']

    if exists == 0:
        print(f"  ⊘ {source_name} 不存在，跳过合并")
        return False

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

    # 删除源节点
    session.run("""
        MATCH (s:Person {name: $source, conversation_name: $conv})
        DETACH DELETE s
    """, source=source_name, conv=conv_name)

    print(f"  ✓ {source_name} → {target_name}")
    return True

def rename_person(session, old_name, new_name, conv_name):
    """重命名Person实体"""
    session.run("""
        MATCH (p:Person {name: $old_name, conversation_name: $conv})
        SET p.name = $new_name
    """, old_name=old_name, new_name=new_name, conv=conv_name)
    print(f"  ✓ 改名: {old_name} → {new_name}")

def set_aliases(session, person_name, aliases, conv_name):
    """设置Person的aliases"""
    session.run("""
        MATCH (p:Person {name: $name, conversation_name: $conv})
        SET p.aliases = $aliases
    """, name=person_name, aliases=aliases, conv=conv_name)
    print(f"  ✓ 设置aliases: {aliases}")

def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    print("=" * 80)
    print("设置Person实体的正式名称和别名")
    print("=" * 80)

    with driver.session() as session:
        # ===== 组1：吉月 → 王露颖 =====
        print("\n【组1】吉月 → 王露颖")
        merge_person(session, "露露", "吉月", CONVERSATION)
        merge_person(session, "王露颖", "吉月", CONVERSATION)
        rename_person(session, "吉月", "王露颖", CONVERSATION)
        set_aliases(session, "王露颖", ["lu", "露露", "露", "吉月"], CONVERSATION)

        # ===== 组2：吉月的妈妈 → 薇薇阿姨 =====
        print("\n【组2】吉月的妈妈 → 薇薇阿姨")
        rename_person(session, "吉月的妈妈", "薇薇阿姨", CONVERSATION)
        set_aliases(session, "薇薇阿姨", ["weiwei", "薇薇露露", "吉月的妈妈"], CONVERSATION)

        # ===== 组3：吉月的弟弟 → 王建宇 =====
        print("\n【组3】吉月的弟弟 → 王建宇")
        merge_person(session, "王建宇", "吉月的弟弟", CONVERSATION)
        rename_person(session, "吉月的弟弟", "王建宇", CONVERSATION)
        set_aliases(session, "王建宇", ["JY", "建宇", "jianyu", "吉月的弟弟"], CONVERSATION)

        # ===== 组4：Ted → 王柏童 =====
        print("\n【组4】Ted → 王柏童")
        rename_person(session, "Ted", "王柏童", CONVERSATION)
        set_aliases(session, "王柏童", ["Ted"], CONVERSATION)

        # ===== 组5：锤子 → 王紫璇 =====
        print("\n【组5】锤子 → 王紫璇")
        merge_person(session, "紫萱", "锤子", CONVERSATION)
        rename_person(session, "锤子", "王紫璇", CONVERSATION)
        set_aliases(session, "王紫璇", ["锤子", "紫萱"], CONVERSATION)

        print("\n" + "=" * 80)
        print("完成！所有实体已设置正式名称和别名")
        print("=" * 80)

        # 验证
        print("\n【验证】最终结果：")
        names = ["王露颖", "薇薇阿姨", "王建宇", "王柏童", "王紫璇"]
        for name in names:
            result = session.run("""
                MATCH (p:Person {name: $name, conversation_name: $conv})
                RETURN p.name as name, p.aliases as aliases
            """, name=name, conv=CONVERSATION)

            record = result.single()
            if record:
                print(f"  ✓ {record['name']}: {record['aliases']}")

    driver.close()

if __name__ == '__main__':
    main()
