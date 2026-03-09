#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试batch_extract函数"""

import sys
import io
import os
import json
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 加载环境变量
load_dotenv(dotenv_path='../.env')

# Neo4j配置
NEO4J_URI = 'bolt://localhost:7687'
NEO4J_USER = 'neo4j'
NEO4J_PASSWORD = 'password123'

def get_all_persons_in_conversation(session, conversation_name):
    """获取某个对话中的所有Person名称"""
    result = session.run("""
        MATCH (p:Person {conversation_name: $conv})
        RETURN p.name as name, p.aliases as aliases
    """, conv=conversation_name)

    persons = {}
    for record in result:
        name = record['name']
        aliases = record.get('aliases', []) or []
        persons[name] = aliases

    return persons

def test_person_list_format(persons_dict):
    """测试Person列表格式"""
    person_lines = []
    for name, aliases in list(persons_dict.items())[:20]:
        if aliases and len(aliases) > 0:
            alias_str = ', '.join(aliases)
            person_lines.append(f'- {name} (别名: {alias_str})')
        else:
            person_lines.append(f'- {name}')

    print("Person列表格式预览（前20个）:")
    print('\n'.join(person_lines))

def main():
    print("=" * 80)
    print("测试修改后的batch_extract逻辑")
    print("=" * 80)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        # 测试吉月对话
        print("\n获取吉月对话的Person...")
        persons = get_all_persons_in_conversation(session, "吉月")
        print(f"总Person数: {len(persons)}")

        # 测试格式化
        test_person_list_format(persons)

        # 检查王露颖的aliases
        print(f"\n王露颖的aliases: {persons.get('王露颖', 'NOT FOUND')}")
        print(f"米雪川的aliases: {persons.get('米雪川', 'NOT FOUND')}")

    driver.close()
    print("\n✅ 测试完成")

if __name__ == '__main__':
    main()
