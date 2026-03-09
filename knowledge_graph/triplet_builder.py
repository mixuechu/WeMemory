#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成最终版本的自然语言三元组（包含优化的searchable_text）
"""
import json
import os

with open('entity_alias_map.json', 'r', encoding='utf-8') as f:
    alias_map = json.load(f)

with open('natural_language_triplets_enhanced.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

records = data['records']

print("=" * 80)
print("生成最终版自然语言三元组")
print("=" * 80)

# 完整的关系类型语义映射
RELATION_SEMANTICS = {
    # 家庭关系
    'HAS_PARENT': '父母,亲子,家人,家庭',
    'HAS_CHILD': '孩子,亲子,家人,家庭',
    'HAS_SPOUSE': '配偶,夫妻,老公老婆,家人,家庭',
    'HAS_GRANDPARENT': '爷爷奶奶,外公外婆,祖辈,家人,家庭',
    'HAS_GRANDCHILD': '孙子孙女,外孙,后辈,家人,家庭',
    'HAS_SIBLING': '兄弟姐妹,手足,家人,家庭',
    'HAS_COUSIN': '表兄弟,堂兄弟,亲戚,家庭',
    'HAS_AUNT': '姑姑,姨妈,阿姨,亲戚,家庭',
    'HAS_UNCLE': '叔叔,伯伯,舅舅,亲戚,家庭',
    'HAS_NEPHEW': '侄子侄女,外甥,亲戚,家庭',
    'HAS_RELATIVE': '亲戚,家人,家庭',
    'HAS_PARENT_SIBLING': '叔伯姑舅姨,亲戚,家庭',

    # 工作关系
    'WORKS_AT': '工作,公司,职场,事业',
    'WORKS_AS': '职业,职位,工作,事业',
    'WORKS_WITH': '同事,合作,工作,职场',
    'WORKED_AT': '曾经工作,前公司,职场',

    # 地点关系
    'LOCATED_AT': '地点,位置,所在地',

    # 社交关系
    'FRIENDS_WITH': '朋友,社交',
    'HAS_PARTNER': '伴侣,恋人,情侣',
    'HAS_EX_PARTNER': '前任,前男女友',
    'KNOWS': '认识,熟人',
}

for record in records:
    text = record['text']
    record_type = record['type']
    metadata = record['metadata']

    enhancements = []

    if record_type == 'relationship':
        relation_type = metadata.get('relation_type', '')
        subject = metadata.get('subject', '')
        obj = metadata.get('object', '')

        # 添加语义标签
        if relation_type in RELATION_SEMANTICS:
            semantics = RELATION_SEMANTICS[relation_type]
            enhancements.append(f"语义标签:{semantics}")

        # 添加主客体
        entities = [e for e in [subject, obj] if e]
        if entities:
            enhancements.append(f"涉及实体:{','.join(entities)}")

        # 添加别名
        for entity in entities:
            aliases = set(alias_map.get(entity, []))
            if len(aliases) > 1:
                other = [a for a in aliases if a != entity][:3]
                if other:
                    enhancements.append(f"{entity}别名:{','.join(other)}")

    elif record_type == 'event':
        event_type = metadata.get('event_type', '')
        time_desc = metadata.get('time_description', '')
        participants = metadata.get('participants', [])

        if event_type:
            enhancements.append(f"事件类型:{event_type}")
        if time_desc:
            enhancements.append(f"时间:{time_desc}")

        # 参与者别名
        for p in participants[:5]:
            aliases = set(alias_map.get(p, []))
            if len(aliases) > 1:
                other = [a for a in aliases if a != p][:3]
                if other:
                    enhancements.append(f"{p}别名:{','.join(other)}")

    # 生成searchable_text
    if enhancements:
        searchable_text = f"{text} [{'; '.join(enhancements)}]"
    else:
        searchable_text = text

    record['searchable_text'] = searchable_text

print(f"\n处理完成: {len(records)} 条记录")

# 示例展示
import random
random.seed(42)

print("\n关系三元组示例（前5个）:")
rels = [r for r in records if r['type'] == 'relationship'][:5]
for r in rels:
    print(f"\n原文: {r['text']}")
    print(f"增强: {r['searchable_text'][:200]}")

print("\n事件描述示例（前5个）:")
events = [r for r in records if r['type'] == 'event'][:5]
for r in events:
    print(f"\n原文: {r['text'][:80]}")
    print(f"增强: {r['searchable_text'][:200]}")

# 保存
output_file = 'natural_language_triplets_final.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

file_size = os.path.getsize(output_file) / (1024 * 1024)
print(f"\n✓ 保存到: {output_file} ({file_size:.2f} MB)")
print("=" * 80)
