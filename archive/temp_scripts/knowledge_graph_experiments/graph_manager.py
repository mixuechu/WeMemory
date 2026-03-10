#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知识图谱管理工具 - 实体合并、删除、别名管理"""

import sys
import io
import json
from pathlib import Path
from neo4j import GraphDatabase
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Neo4j连接配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password123"


class GraphManager:
    """知识图谱管理器"""

    def __init__(self, uri: str = NEO4J_URI, user: str = NEO4J_USER, password: str = NEO4J_PASSWORD):
        """初始化连接"""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.driver.verify_connectivity()
        print(f"✅ 已连接到Neo4j: {uri}")

    def close(self):
        """关闭连接"""
        self.driver.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ==================== 1. Person实体合并 ====================

    def merge_persons(self, source_name: str, source_conv: str,
                     target_name: str, target_conv: str,
                     dry_run: bool = False) -> Dict:
        """合并两个Person实体

        将source合并到target：
        1. 将source的所有关系转移到target
        2. 合并aliases
        3. 删除source节点

        Args:
            source_name: 源节点姓名
            source_conv: 源节点对话名称
            target_name: 目标节点姓名
            target_conv: 目标节点对话名称
            dry_run: 如果为True，只返回影响范围，不实际执行

        Returns:
            合并结果统计
        """
        with self.driver.session() as session:
            # 1. 检查两个节点是否存在
            result = session.run("""
                MATCH (s:Person {name: $source_name, conversation_name: $source_conv})
                MATCH (t:Person {name: $target_name, conversation_name: $target_conv})
                RETURN s, t
            """, source_name=source_name, source_conv=source_conv,
                target_name=target_name, target_conv=target_conv)

            record = result.single()
            if not record:
                return {"error": "找不到源节点或目标节点"}

            source = record['s']
            target = record['t']

            # 2. 统计影响范围
            rel_count = session.run("""
                MATCH (s:Person {name: $source_name, conversation_name: $source_conv})-[r]-()
                RETURN count(r) as count
            """, source_name=source_name, source_conv=source_conv).single()['count']

            stats = {
                'source': f"{source_name} ({source_conv})",
                'target': f"{target_name} ({target_conv})",
                'relationships_to_transfer': rel_count,
                'source_aliases': source.get('aliases', []),
                'target_aliases_before': target.get('aliases', []),
            }

            if dry_run:
                stats['dry_run'] = True
                return stats

            # 3. 合并aliases
            source_aliases = source.get('aliases', [])
            target_aliases = target.get('aliases', [])

            # 添加source的name作为target的alias
            merged_aliases = list(set(target_aliases + source_aliases + [source_name]))

            session.run("""
                MATCH (t:Person {name: $target_name, conversation_name: $target_conv})
                SET t.aliases = $aliases
            """, target_name=target_name, target_conv=target_conv, aliases=merged_aliases)

            # 4. 转移所有关系（按关系类型分别处理）
            # 获取所有关系类型
            rel_types = session.run("""
                MATCH (s:Person {name: $source_name, conversation_name: $source_conv})-[r]-()
                RETURN DISTINCT type(r) as rel_type
            """, source_name=source_name, source_conv=source_conv)

            for record in rel_types:
                rel_type = record['rel_type']

                # 转移出边
                session.run(f"""
                    MATCH (s:Person {{name: $source_name, conversation_name: $source_conv}})-[r:{rel_type}]->(other)
                    MATCH (t:Person {{name: $target_name, conversation_name: $target_conv}})
                    WHERE NOT (t)-[:{rel_type}]->(other)
                    MERGE (t)-[r2:{rel_type}]->(other)
                    SET r2 = properties(r)
                    DELETE r
                """, source_name=source_name, source_conv=source_conv,
                    target_name=target_name, target_conv=target_conv)

                # 转移入边
                session.run(f"""
                    MATCH (other)-[r:{rel_type}]->(s:Person {{name: $source_name, conversation_name: $source_conv}})
                    MATCH (t:Person {{name: $target_name, conversation_name: $target_conv}})
                    WHERE NOT (other)-[:{rel_type}]->(t)
                    MERGE (other)-[r2:{rel_type}]->(t)
                    SET r2 = properties(r)
                    DELETE r
                """, source_name=source_name, source_conv=source_conv,
                    target_name=target_name, target_conv=target_conv)

            # 5. 删除source节点
            session.run("""
                MATCH (s:Person {name: $source_name, conversation_name: $source_conv})
                DELETE s
            """, source_name=source_name, source_conv=source_conv)

            stats['target_aliases_after'] = merged_aliases
            stats['success'] = True

            return stats

    # ==================== 2. Person实体删除 ====================

    def delete_person(self, name: str, conversation_name: str, dry_run: bool = False) -> Dict:
        """删除Person实体及其所有关系

        Args:
            name: 节点姓名
            conversation_name: 对话名称
            dry_run: 如果为True，只返回影响范围，不实际执行

        Returns:
            删除结果统计
        """
        with self.driver.session() as session:
            # 1. 检查节点是否存在
            result = session.run("""
                MATCH (p:Person {name: $name, conversation_name: $conv})
                RETURN p
            """, name=name, conv=conversation_name)

            if not result.single():
                return {"error": f"找不到节点: {name} ({conversation_name})"}

            # 2. 统计影响范围
            rel_count = session.run("""
                MATCH (p:Person {name: $name, conversation_name: $conv})-[r]-()
                RETURN count(r) as count
            """, name=name, conv=conversation_name).single()['count']

            stats = {
                'name': name,
                'conversation_name': conversation_name,
                'relationships_to_delete': rel_count,
            }

            if dry_run:
                stats['dry_run'] = True
                return stats

            # 3. 删除节点及其关系
            session.run("""
                MATCH (p:Person {name: $name, conversation_name: $conv})
                DETACH DELETE p
            """, name=name, conv=conversation_name)

            stats['success'] = True
            return stats

    def batch_delete_persons(self, persons: List[Tuple[str, str]], dry_run: bool = False) -> Dict:
        """批量删除Person实体

        Args:
            persons: [(name, conversation_name), ...] 列表
            dry_run: 如果为True，只返回影响范围，不实际执行

        Returns:
            批量删除结果统计
        """
        results = []
        for name, conv in persons:
            result = self.delete_person(name, conv, dry_run=dry_run)
            results.append(result)

        total_deleted = sum(1 for r in results if r.get('success'))
        total_rels_deleted = sum(r.get('relationships_to_delete', 0) for r in results)

        return {
            'total_persons': len(persons),
            'deleted': total_deleted,
            'total_relationships_deleted': total_rels_deleted,
            'details': results,
            'dry_run': dry_run
        }

    # ==================== 3. 别名管理 ====================

    def add_alias(self, name: str, conversation_name: str, alias: str) -> Dict:
        """为Person添加别名

        Args:
            name: 节点姓名
            conversation_name: 对话名称
            alias: 要添加的别名

        Returns:
            操作结果
        """
        with self.driver.session() as session:
            # 检查节点是否存在
            result = session.run("""
                MATCH (p:Person {name: $name, conversation_name: $conv})
                RETURN p.aliases as current_aliases
            """, name=name, conv=conversation_name)

            record = result.single()
            if not record:
                return {"error": f"找不到节点: {name} ({conversation_name})"}

            current_aliases = record['current_aliases'] or []

            if alias in current_aliases:
                return {
                    'name': name,
                    'conversation_name': conversation_name,
                    'message': f'别名 "{alias}" 已存在',
                    'aliases': current_aliases
                }

            # 添加新别名
            new_aliases = current_aliases + [alias]
            session.run("""
                MATCH (p:Person {name: $name, conversation_name: $conv})
                SET p.aliases = $aliases
            """, name=name, conv=conversation_name, aliases=new_aliases)

            return {
                'name': name,
                'conversation_name': conversation_name,
                'added_alias': alias,
                'aliases_before': current_aliases,
                'aliases_after': new_aliases,
                'success': True
            }

    def set_aliases(self, name: str, conversation_name: str, aliases: List[str]) -> Dict:
        """设置Person的别名列表（覆盖现有）

        Args:
            name: 节点姓名
            conversation_name: 对话名称
            aliases: 别名列表

        Returns:
            操作结果
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Person {name: $name, conversation_name: $conv})
                SET p.aliases = $aliases
                RETURN p.aliases as new_aliases
            """, name=name, conv=conversation_name, aliases=aliases)

            record = result.single()
            if not record:
                return {"error": f"找不到节点: {name} ({conversation_name})"}

            return {
                'name': name,
                'conversation_name': conversation_name,
                'aliases': record['new_aliases'],
                'success': True
            }

    # ==================== 4. 查找重复实体 ====================

    def find_duplicate_persons(self, similarity_threshold: float = 0.85) -> List[Dict]:
        """查找可能重复的Person实体

        检测规则：
        1. 同一conversation中，名字相似度高的
        2. 大小写不同但其他相同的
        3. 名字包含关系的（如：Hunter / hunter）

        Args:
            similarity_threshold: 相似度阈值（0-1）

        Returns:
            可能重复的实体对列表
        """
        with self.driver.session() as session:
            # 获取所有Person节点
            result = session.run("""
                MATCH (p:Person)
                RETURN p.name as name, p.conversation_name as conv
                ORDER BY conv, name
            """)

            persons = [(r['name'], r['conv']) for r in result]

        duplicates = []

        # 分组：按conversation分组
        from collections import defaultdict
        conv_groups = defaultdict(list)
        for name, conv in persons:
            conv_groups[conv].append(name)

        # 在每个conversation内查找重复
        for conv, names in conv_groups.items():
            for i, name1 in enumerate(names):
                for name2 in names[i+1:]:
                    # 规则1: 大小写不同
                    if name1.lower() == name2.lower():
                        duplicates.append({
                            'person1': (name1, conv),
                            'person2': (name2, conv),
                            'reason': '大小写不同',
                            'similarity': 1.0,
                            'suggestion': f'合并为: {name1 if name1[0].isupper() else name2}'
                        })
                        continue

                    # 规则2: 相似度高
                    similarity = SequenceMatcher(None, name1, name2).ratio()
                    if similarity >= similarity_threshold:
                        duplicates.append({
                            'person1': (name1, conv),
                            'person2': (name2, conv),
                            'reason': f'名字相似度: {similarity:.2%}',
                            'similarity': similarity,
                            'suggestion': '人工判断'
                        })

        return duplicates

    # ==================== 5. 查找孤立/无用节点 ====================

    def find_isolated_persons(self) -> List[Dict]:
        """查找孤立的Person节点（没有任何关系）

        Returns:
            孤立节点列表
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Person)
                WHERE NOT (p)-[]-()
                RETURN p.name as name, p.conversation_name as conv, p.aliases as aliases
                ORDER BY conv, name
            """)

            return [{
                'name': r['name'],
                'conversation_name': r['conv'],
                'aliases': r['aliases'],
                'reason': '无任何关系'
            } for r in result]

    def find_low_value_persons(self) -> List[Dict]:
        """查找低价值Person节点

        规则：
        1. 纯数字ID（如：10、13、168）
        2. 模糊描述（如：00年女生、94年女生）
        3. 只有1-2个关系的节点

        Returns:
            低价值节点列表
        """
        with self.driver.session() as session:
            # 规则1: 纯数字ID
            result1 = session.run("""
                MATCH (p:Person)
                WHERE p.name =~ '^[0-9]+$'
                OPTIONAL MATCH (p)-[r]-()
                RETURN p.name as name, p.conversation_name as conv,
                       count(r) as rel_count
                ORDER BY conv, name
            """)

            low_value = [{
                'name': r['name'],
                'conversation_name': r['conv'],
                'relationships': r['rel_count'],
                'reason': '纯数字ID'
            } for r in result1]

            # 规则2: 模糊描述（包含"年"、"女生"、"男生"等）
            result2 = session.run("""
                MATCH (p:Person)
                WHERE p.name =~ '.*[年岁].*[女男].*' OR p.name =~ '.*女生.*' OR p.name =~ '.*男生.*'
                OPTIONAL MATCH (p)-[r]-()
                RETURN p.name as name, p.conversation_name as conv,
                       count(r) as rel_count
                ORDER BY conv, name
            """)

            low_value.extend([{
                'name': r['name'],
                'conversation_name': r['conv'],
                'relationships': r['rel_count'],
                'reason': '模糊描述'
            } for r in result2])

            # 规则3: 关系数<=2
            result3 = session.run("""
                MATCH (p:Person)-[r]-()
                WITH p, count(r) as rel_count
                WHERE rel_count <= 2
                RETURN p.name as name, p.conversation_name as conv,
                       rel_count
                ORDER BY rel_count, conv, name
            """)

            low_value.extend([{
                'name': r['name'],
                'conversation_name': r['conv'],
                'relationships': r['rel_count'],
                'reason': f'关系数少({r["rel_count"]}个)'
            } for r in result3])

            return low_value

    # ==================== 6. 批量操作 ====================

    def execute_batch_operations(self, operations_file: str, dry_run: bool = False) -> Dict:
        """从JSON文件批量执行操作

        JSON格式：
        {
            "merges": [
                {
                    "source": ["name1", "conv1"],
                    "target": ["name2", "conv2"]
                }
            ],
            "deletes": [
                ["name", "conv"]
            ],
            "aliases": [
                {
                    "person": ["name", "conv"],
                    "add": ["alias1", "alias2"]
                }
            ]
        }

        Args:
            operations_file: 操作文件路径
            dry_run: 如果为True，只返回影响范围，不实际执行

        Returns:
            批量操作结果
        """
        with open(operations_file, 'r', encoding='utf-8') as f:
            ops = json.load(f)

        results = {
            'merges': [],
            'deletes': [],
            'aliases': [],
            'dry_run': dry_run
        }

        # 执行合并
        for merge_op in ops.get('merges', []):
            src = merge_op['source']
            tgt = merge_op['target']
            result = self.merge_persons(src[0], src[1], tgt[0], tgt[1], dry_run=dry_run)
            results['merges'].append(result)

        # 执行删除
        for delete_op in ops.get('deletes', []):
            result = self.delete_person(delete_op[0], delete_op[1], dry_run=dry_run)
            results['deletes'].append(result)

        # 执行别名添加
        for alias_op in ops.get('aliases', []):
            person = alias_op['person']
            for alias in alias_op.get('add', []):
                result = self.add_alias(person[0], person[1], alias)
                results['aliases'].append(result)

        return results


# ==================== 辅助函数 ====================

def print_duplicates(duplicates: List[Dict]):
    """打印重复实体"""
    print(f"\n找到 {len(duplicates)} 对可能重复的实体：")
    print("=" * 80)
    for i, dup in enumerate(duplicates, 1):
        p1 = dup['person1']
        p2 = dup['person2']
        print(f"\n{i}. {dup['reason']}")
        print(f"   实体1: {p1[0]} ({p1[1]})")
        print(f"   实体2: {p2[0]} ({p2[1]})")
        print(f"   建议: {dup['suggestion']}")


def print_isolated_persons(isolated: List[Dict]):
    """打印孤立节点"""
    print(f"\n找到 {len(isolated)} 个孤立节点：")
    print("=" * 80)
    for person in isolated:
        print(f"  {person['name']} ({person['conversation_name']}) - {person['reason']}")


def print_low_value_persons(low_value: List[Dict]):
    """打印低价值节点"""
    print(f"\n找到 {len(low_value)} 个低价值节点：")
    print("=" * 80)
    for person in low_value:
        print(f"  {person['name']} ({person['conversation_name']}) - {person['reason']} - {person['relationships']}个关系")


# ==================== 使用示例 ====================

if __name__ == '__main__':
    with GraphManager() as gm:
        print("\n" + "=" * 80)
        print("知识图谱管理工具")
        print("=" * 80)

        # 示例1: 查找重复实体
        print("\n【1】查找重复实体...")
        duplicates = gm.find_duplicate_persons()
        print_duplicates(duplicates)

        # 示例2: 查找孤立节点
        print("\n【2】查找孤立节点...")
        isolated = gm.find_isolated_persons()
        print_isolated_persons(isolated)

        # 示例3: 查找低价值节点
        print("\n【3】查找低价值节点...")
        low_value = gm.find_low_value_persons()
        print_low_value_persons(low_value)

        print("\n" + "=" * 80)
        print("✅ 分析完成")
        print("=" * 80)
