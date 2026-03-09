#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理泛指/描述性Person节点（无具体姓名的节点）"""

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

# 定义泛指词模式
GENERIC_PATTERNS = [
    # 占位符
    '某', 'Unnamed', '第三方', '未知', '匿名', '无名',
    # 代词
    '她', '他', '你', '我', '他们', '她们', '人家', '别人', '有人', '谁', '那个',
    # 关系型占位符
    '朋友A', '朋友B', '朋友C', '朋友D', '朋友E',
    '同学A', '同学B', '同学C',
    '室友A', '室友B',
    '女性A', '男性A', '女士A', '男士A',
    # 纯描述性
    '某女性', '某男性', '某女士', '某男士', '某人',
    '不明', '神秘', '匿名',
    # 英文占位符
    'Person A', 'Person B', 'Someone', 'Somebody',
]

def is_generic_name(name):
    """判断是否是泛指/描述性名字"""
    # 检查是否包含泛指关键词
    for pattern in GENERIC_PATTERNS:
        if pattern in name:
            return True

    # 检查是否是纯代词
    if name in ['她', '他', '你', '我', '他们', '她们', '人家', '别人', '有人', '谁']:
        return True

    # 检查是否是"XX的YY"格式且YY是泛指词
    generic_suffixes = [
        '朋友', '同学', '同事', '室友', '女朋友', '男朋友',
        '妈妈', '爸爸', '姐姐', '妹妹', '哥哥', '弟弟',
        '老婆', '老公', '女儿', '儿子',
        '老师', '医生', '律师', '司机', '保姆'
    ]

    for suffix in generic_suffixes:
        # XX的朋友A/B/C
        if name.endswith(f'{suffix}A') or name.endswith(f'{suffix}B') or name.endswith(f'{suffix}C'):
            return True

    return False

def find_generic_persons(session):
    """找出所有泛指节点"""
    result = session.run('''
        MATCH (p:Person)
        OPTIONAL MATCH (p)-[r]-()
        WITH p, count(r) as rel_count
        RETURN p.name as name, p.conversation_name as conv, rel_count
        ORDER BY rel_count DESC
    ''')

    generic_nodes = []
    for record in result:
        name = record['name']
        if is_generic_name(name):
            generic_nodes.append({
                'name': name,
                'conv': record['conv'],
                'rel_count': record['rel_count']
            })

    return generic_nodes

def delete_person(session, name, conv, dry_run=False):
    """删除Person节点"""
    if dry_run:
        return

    # 删除所有相关关系和节点
    session.run('''
        MATCH (p:Person {name: $name, conversation_name: $conv})
        DETACH DELETE p
    ''', name=name, conv=conv)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='清理泛指/描述性Person节点')
    parser.add_argument('--dry-run', action='store_true', help='模拟运行，不实际删除')
    args = parser.parse_args()

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    print("=" * 80)
    print("清理泛指/描述性Person节点")
    print("=" * 80)

    with driver.session() as session:
        # 查找前统计
        before_count = session.run('MATCH (p:Person) RETURN count(p) as total').single()['total']
        print(f"\n清理前: {before_count}个Person节点")

        # 找出泛指节点
        generic_nodes = find_generic_persons(session)

        print(f"\n找到 {len(generic_nodes)} 个泛指/描述性节点:")
        print("-" * 80)

        for i, node in enumerate(generic_nodes, 1):
            print(f"{i}. {node['name']} ({node['conv']}) - {node['rel_count']}个关系")

        # 删除
        if args.dry_run:
            print(f"\n[DRY RUN] 将删除 {len(generic_nodes)} 个节点")
        else:
            print(f"\n正在删除 {len(generic_nodes)} 个节点...")
            for node in generic_nodes:
                delete_person(session, node['name'], node['conv'], dry_run=False)
                print(f"  已删除: {node['name']}")

            # 查找后统计
            after_count = session.run('MATCH (p:Person) RETURN count(p) as total').single()['total']
            print(f"\n清理后: {after_count}个Person节点")
            print(f"已删除: {before_count - after_count}个节点")

    driver.close()
    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
