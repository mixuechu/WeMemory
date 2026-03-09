#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
步骤2：生成Person合并建议并输出Excel
"""
import pickle
import pandas as pd
from pathlib import Path
from collections import defaultdict, Counter
import re

print("=" * 80)
print("生成Person合并建议")
print("=" * 80)

# 1. 加载数据
print("\n加载数据...")
with open('person_database.pkl', 'rb') as f:
    db = pickle.load(f)

persons = db['persons']
person_index = db['person_index']
conversation_persons = db['conversation_persons']

print(f"  Person实例: {len(persons):,}")
print(f"  唯一人名: {len(person_index):,}")

# 2. 分析合并候选
print("\n分析合并候选...")

merge_suggestions = []

def get_base_name(name):
    """提取基础名字（去除关系词）"""
    # 匹配 "XXX的YYY" 模式
    match = re.match(r'(.+)的(.+)', name)
    if match:
        return match.group(1), match.group(2)
    return None, name

def should_merge(name1, name2, instances1, instances2):
    """判断两个人名是否应该合并"""
    # 提取出现的对话
    convs1 = set(p['conversation'] for idx in instances1 for p in [persons[idx]])
    convs2 = set(p['conversation'] for idx in instances2 for p in [persons[idx]])

    base1_person, base1_rel = get_base_name(name1)
    base2_person, base2_rel = get_base_name(name2)

    # 规则1: 同一对话内，一个是简称一个是全称
    # 例如："妈" 和 "米雪川的妈妈" 在同一对话中
    common_convs = convs1 & convs2
    if common_convs:
        # 检查是否有关系词
        if base1_person and not base2_person:
            # name1是"XXX的YYY"，name2是"YYY"
            if base1_rel == name2:
                return {
                    'confidence': 'high',
                    'reason': f'同对话内关系词匹配 ({list(common_convs)[:3]})',
                    'type': 'same_conversation_relation'
                }
        elif base2_person and not base1_person:
            # name2是"XXX的YYY"，name1是"YYY"
            if base2_rel == name1:
                return {
                    'confidence': 'high',
                    'reason': f'同对话内关系词匹配 ({list(common_convs)[:3]})',
                    'type': 'same_conversation_relation'
                }

    # 规则2: 跨对话，都明确标注同一个人
    # 例如：所有"米雪川的妈妈"
    if base1_person and base2_person and base1_person == base2_person and base1_rel == base2_rel:
        return {
            'confidence': 'high',
            'reason': f'都明确指向同一人: {base1_person}的{base1_rel}',
            'type': 'explicit_same_person'
        }

    # 规则3: 名字非常相似（编辑距离小）
    if abs(len(name1) - len(name2)) <= 2:
        # 简单的相似度检查
        common_chars = set(name1) & set(name2)
        if len(common_chars) >= min(len(name1), len(name2)) * 0.7:
            if convs1 & convs2:  # 有共同对话
                return {
                    'confidence': 'medium',
                    'reason': f'名字相似且在共同对话中出现',
                    'type': 'similar_name_same_conv'
                }

    return None

# 3. 遍历所有人名对，寻找合并候选
print("  识别合并组...")
processed_pairs = set()
merge_id = 0

for name1 in list(person_index.keys()):
    for name2 in list(person_index.keys()):
        if name1 >= name2:  # 避免重复比较
            continue

        pair_key = tuple(sorted([name1, name2]))
        if pair_key in processed_pairs:
            continue

        processed_pairs.add(pair_key)

        instances1 = person_index[name1]
        instances2 = person_index[name2]

        result = should_merge(name1, name2, instances1, instances2)

        if result:
            # 收集详细信息
            variants = []

            for name, instances in [(name1, instances1), (name2, instances2)]:
                convs = Counter(persons[idx]['conversation'] for idx in instances)
                aliases = set()
                for idx in instances:
                    aliases.update(persons[idx]['aliases'])

                variants.append({
                    'name': name,
                    'count': len(instances),
                    'conversations': list(convs.keys())[:5],  # 最多5个
                    'conv_count': len(convs),
                    'aliases': list(aliases)[:5]  # 最多5个
                })

            merge_id += 1
            merge_suggestions.append({
                'merge_id': merge_id,
                'suggested_name': variants[0]['name'] if variants[0]['count'] >= variants[1]['count'] else variants[1]['name'],
                'confidence': result['confidence'],
                'reason': result['reason'],
                'type': result['type'],
                'variants': variants,
                'total_instances': sum(v['count'] for v in variants)
            })

print(f"  找到合并建议: {len(merge_suggestions)}")

# 4. 生成Excel
print("\n生成Excel...")

rows = []
for suggestion in merge_suggestions:
    # 准备一行数据
    variants_info = []
    for v in suggestion['variants']:
        conv_str = ', '.join(v['conversations'][:3])
        if v['conv_count'] > 3:
            conv_str += f" +{v['conv_count']-3}个"
        alias_str = ', '.join(v['aliases'][:3]) if v['aliases'] else '-'
        variants_info.append(f"{v['name']} (出现{v['count']}次, 对话:{conv_str}, 别名:{alias_str})")

    rows.append({
        'ID': suggestion['merge_id'],
        '置信度': suggestion['confidence'],
        '建议合并名称': suggestion['suggested_name'],
        '包含的变体': '\n'.join(variants_info),
        '总出现次数': suggestion['total_instances'],
        '合并原因': suggestion['reason'],
        '决定': ''  # 用户填写 approve/reject
    })

df = pd.DataFrame(rows)

# 按置信度和出现次数排序
confidence_order = {'high': 0, 'medium': 1, 'low': 2}
df['_conf_order'] = df['置信度'].map(confidence_order)
df = df.sort_values(['_conf_order', '总出现次数'], ascending=[True, False])
df = df.drop('_conf_order', axis=1)

# 保存Excel
output_file = 'person_merge_suggestions.xlsx'

# 分sheet保存
with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    # 全部数据
    df.to_excel(writer, sheet_name='全部建议', index=False)

    # 按置信度分sheet
    for conf in ['high', 'medium', 'low']:
        df_conf = df[df['置信度'] == conf]
        if len(df_conf) > 0:
            sheet_name = {'high': '高置信度', 'medium': '中等置信度', 'low': '低置信度'}[conf]
            df_conf.to_excel(writer, sheet_name=sheet_name, index=False)

print(f"\n完成！")
print(f"  合并建议总数: {len(df)}")
print(f"    高置信度: {len(df[df['置信度']=='high'])}")
print(f"    中等置信度: {len(df[df['置信度']=='medium'])}")
print(f"    低置信度: {len(df[df['置信度']=='low'])}")
print(f"\n保存到: {output_file}")
print("\n请在Excel中审核，在'决定'列填写 approve 或 reject")
print("=" * 80)
