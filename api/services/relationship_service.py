#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心关系查询服务

提供轻量级的人物关系查询，作为个人助理的Tool使用。
不需要全量注入到prompt，按需检索，节省token成本。
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from functools import lru_cache


class RelationshipService:
    """核心关系查询服务"""

    def __init__(self, data_path: str):
        """
        初始化关系服务

        Args:
            data_path: 关系数据文件路径
        """
        self.data_path = Path(data_path)
        self.data = self._load_data()
        self.person_index = self._build_person_index()
        self.alias_map = self._build_alias_map()

        print(f"✓ 关系服务初始化完成")
        print(f"  - 核心人物: {len(self.person_index)}人")
        print(f"  - 核心关系: {self.data['statistics']['total_relationships_kept']}条")

    def _load_data(self) -> Dict:
        """加载关系数据"""
        with open(self.data_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _build_person_index(self) -> Dict[str, Dict]:
        """构建人物索引"""
        index = {}
        for person in self.data['persons']:
            index[person['name']] = person
        return index

    def _build_alias_map(self) -> Dict[str, str]:
        """构建别名映射（简单版本，后续可扩展）"""
        alias_map = {}

        # 直接名字映射
        for name in self.person_index.keys():
            alias_map[name.lower()] = name

        return alias_map

    def search_person(self, query: str) -> Optional[str]:
        """
        搜索人物（支持模糊匹配）

        Args:
            query: 查询字符串

        Returns:
            匹配的标准名字，未找到返回None
        """
        query_lower = query.lower().strip()

        # 精确匹配
        if query_lower in self.alias_map:
            return self.alias_map[query_lower]

        # 模糊匹配（包含）
        for alias, standard_name in self.alias_map.items():
            if query_lower in alias or alias in query_lower:
                return standard_name

        return None

    def get_person_relationships(
        self,
        person_name: str,
        include_profile: bool = True
    ) -> Optional[Dict]:
        """
        获取某人的所有关系

        Args:
            person_name: 人物名字
            include_profile: 是否包含人物简介

        Returns:
            人物关系信息，未找到返回None
        """
        # 先尝试搜索
        standard_name = self.search_person(person_name)
        if not standard_name:
            return None

        person = self.person_index.get(standard_name)
        if not person:
            return None

        result = {
            "name": person['name'],
            "relationships": []
        }

        if include_profile and 'profile' in person:
            result['profile'] = person['profile']

        # 提取关系
        for rel in person.get('relationships', []):
            result['relationships'].append({
                "text": rel['text'],
                "type": rel['metadata']['relation_type'],
                "subject": rel['metadata']['subject'],
                "object": rel['metadata']['object']
            })

        return result

    def get_related_people(
        self,
        person_name: str,
        relation_types: Optional[List[str]] = None
    ) -> List[str]:
        """
        获取与某人有关系的所有人

        Args:
            person_name: 人物名字
            relation_types: 关系类型过滤（如['HAS_SPOUSE', 'HAS_CHILD']）

        Returns:
            相关人物列表
        """
        person_data = self.get_person_relationships(person_name, include_profile=False)
        if not person_data:
            return []

        related = set()
        for rel in person_data['relationships']:
            # 类型过滤
            if relation_types and rel['type'] not in relation_types:
                continue

            # 提取相关人物（subject或object，排除自己）
            if rel['subject'] != person_data['name']:
                related.add(rel['subject'])
            if rel['object'] != person_data['name']:
                related.add(rel['object'])

        return sorted(list(related))

    def query_relationships(
        self,
        query: str,
        max_results: int = 10
    ) -> Dict:
        """
        查询关系（智能查询，支持多种模式）

        Args:
            query: 查询字符串，如"赵萌"、"赵萌的配偶"、"谁是米雪川的妻子"
            max_results: 最大结果数

        Returns:
            查询结果
        """
        query_lower = query.lower()

        # 特殊处理：米雪川的配偶/老婆/妻子（反向查询）
        if '米雪川' in query and any(keyword in query_lower for keyword in ['配偶', '老婆', '妻子', 'spouse', 'wife']):
            # 在所有人物中查找配偶是米雪川的人
            for person in self.data['persons']:
                for rel in person.get('relationships', []):
                    if (rel['metadata'].get('relation_type') in ['HAS_SPOUSE', 'IS_SPOUSE_OF'] and
                        '米雪川' in rel['metadata'].get('object', '') or '米雪川' in rel['metadata'].get('subject', '')):
                        # 找到了！返回这个人的信息
                        person_data = self.get_person_relationships(person['name'])
                        return {
                            "success": True,
                            "query": query,
                            "person": person_data['name'],
                            "profile": person_data.get('profile'),
                            "relationships": person_data['relationships'][:max_results],
                            "total_count": len(person_data['relationships'])
                        }

        # 提取人名（简单版本，后续可用NER）
        words = query.split()

        # 尝试找到查询中的人名
        found_person = None
        for word in words:
            person = self.search_person(word)
            if person:
                found_person = person
                break

        if not found_person:
            return {
                "success": False,
                "message": f"未找到相关人物: {query}"
            }

        # 获取该人物的关系
        person_data = self.get_person_relationships(found_person)

        return {
            "success": True,
            "query": query,
            "person": person_data['name'],
            "profile": person_data.get('profile'),
            "relationships": person_data['relationships'][:max_results],
            "total_count": len(person_data['relationships'])
        }

    def get_family_tree(self, person_name: str) -> Dict:
        """
        获取家族树（配偶、父母、孩子、兄弟姐妹）

        Args:
            person_name: 人物名字

        Returns:
            家族关系树
        """
        family_types = [
            'HAS_SPOUSE',
            'HAS_PARENT',
            'HAS_CHILD',
            'HAS_SIBLING'
        ]

        person_data = self.get_person_relationships(person_name)
        if not person_data:
            return {
                "success": False,
                "message": f"未找到人物: {person_name}"
            }

        family = {
            "spouse": [],
            "parents": [],
            "children": [],
            "siblings": []
        }

        for rel in person_data['relationships']:
            rel_type = rel['type']

            if rel_type == 'HAS_SPOUSE':
                partner = rel['object'] if rel['subject'] == person_data['name'] else rel['subject']
                family['spouse'].append(partner)

            elif rel_type == 'HAS_PARENT':
                parent = rel['object'] if rel['subject'] == person_data['name'] else rel['subject']
                family['parents'].append(parent)

            elif rel_type == 'HAS_CHILD':
                child = rel['object'] if rel['subject'] == person_data['name'] else rel['subject']
                family['children'].append(child)

            elif rel_type == 'HAS_SIBLING':
                sibling = rel['object'] if rel['subject'] == person_data['name'] else rel['subject']
                family['siblings'].append(sibling)

        return {
            "success": True,
            "person": person_data['name'],
            "family": family
        }

    @lru_cache(maxsize=100)
    def get_stats(self) -> Dict:
        """获取关系数据统计"""
        return {
            "total_persons": len(self.person_index),
            "total_relationships": self.data['statistics']['total_relationships_kept'],
            "reviewed_persons": self.data['statistics']['reviewed_persons'],
            "export_time": self.data['export_time']
        }
