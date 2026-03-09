#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""融合四个文件：两批合并建议 + 两个审批结果 → 每个对话的合并后Person列表"""
import json
import pickle
from pathlib import Path

print("=== 开始融合 Person 实体 ===\n")

# 1. 加载 person_database.pkl
print("1. 加载 person_database.pkl...")
with open('person_database.pkl', 'rb') as f:
    db = pickle.load(f)
persons = db['persons']
person_index = db['person_index']
conversation_persons = db['conversation_persons']
print(f"   [OK] 加载完成：{len(persons)} 个 Person 实例")

# 2. 加载第一版数据
print("\n2. 加载第一版数据...")

# 2.1 第一版合并建议（从提取的JSON加载）
try:
    with open('first_batch_merge_suggestions.json', 'r', encoding='utf-8') as f:
        first_batch_data = json.load(f)
    print(f"   [OK] 第一版建议：{len(first_batch_data)} 个对话")
except FileNotFoundError:
    first_batch_data = None
    print("   ! 警告：找不到first_batch_merge_suggestions.json")

# 2.2 第一版审批结果
with open('c:/Users/A/Downloads/手过第一版.json', 'r', encoding='utf-8') as f:
    first_batch_decisions = json.load(f)
print(f"   [OK] 第一版审批：{len(first_batch_decisions['decisions'])} 个决策")

# 3. 加载补充版数据
print("\n3. 加载补充版数据...")

# 3.1 补充版合并建议
with open('all_191_results.json', 'r', encoding='utf-8') as f:
    supplement_data = json.load(f)
print(f"   [OK] 补充版建议：{len(supplement_data)} 个对话")

# 3.2 补充版审批结果
with open('c:/Users/A/Downloads/手过补充版.json', 'r', encoding='utf-8') as f:
    supplement_decisions = json.load(f)
print(f"   [OK] 补充版审批：{supplement_decisions['total_decisions']} 个决策")
print(f"     - 批准：{len(supplement_decisions['approved'])}")
print(f"     - 拒绝：{supplement_decisions['rejected_count']}")

# 4. 处理第一版数据
print("\n4. 处理第一版合并...")
first_batch_merged = {}

if first_batch_data:
    # 如果有完整数据，按照标准流程处理
    for conv_idx, conv_data in enumerate(first_batch_data):
        conv_name = conv_data['conversation']
        first_batch_merged[conv_name] = {}

        for group_idx, group in enumerate(conv_data['merge_groups']):
            key = f"{conv_idx}-{group_idx}"
            decision = first_batch_decisions['decisions'].get(key, {})

            if decision.get('decision') == 'approve':
                final_name = decision.get('final_name', group['suggested_name'])
                variants = group.get('variants', [])

                # 查找所有person_ids
                person_ids = []
                for variant in variants:
                    ids = person_index.get(variant, [])
                    # 只要属于这个对话的
                    for pid in ids:
                        if persons[pid]['conversation'] == conv_name:
                            person_ids.append(pid)

                if person_ids:
                    first_batch_merged[conv_name][final_name] = {
                        'final_name': final_name,
                        'person_ids': person_ids,
                        'original_names': variants,
                        'total_instances': len(person_ids)
                    }

    print(f"   [OK] 第一版：处理 {len(first_batch_merged)} 个对话")
else:
    # 没有完整数据，只能基于审批结果反推
    print("   ! 第一版数据不完整，跳过（如需要请提供完整数据源）")

# 5. 处理补充版数据
print("\n5. 处理补充版合并...")
supplement_merged = {}

# 构建补充版的决策映射（conversation -> approved merges）
approved_by_conv = {}
for item in supplement_decisions['approved']:
    conv = item['conversation']
    if conv not in approved_by_conv:
        approved_by_conv[conv] = []
    approved_by_conv[conv].append(item)

# 处理每个对话
for conv_data in supplement_data:
    conv_name = conv_data['conversation']
    supplement_merged[conv_name] = {}

    # 获取该对话的批准合并
    approved_merges = approved_by_conv.get(conv_name, [])

    for merge in approved_merges:
        final_name = merge['final_name']
        variants = merge['variants']

        # 查找所有person_ids
        person_ids = []
        for variant in variants:
            ids = person_index.get(variant, [])
            for pid in ids:
                if persons[pid]['conversation'] == conv_name:
                    person_ids.append(pid)

        if person_ids:
            supplement_merged[conv_name][final_name] = {
                'final_name': final_name,
                'person_ids': person_ids,
                'original_names': variants,
                'total_instances': len(person_ids)
            }

print(f"   [OK] 补充版：处理 {len(supplement_merged)} 个对话")

# 6. 合并所有结果
print("\n6. 合并所有结果...")
all_merged = {}

# 合并第一版
for conv, entities in first_batch_merged.items():
    if conv not in all_merged:
        all_merged[conv] = {}
    all_merged[conv].update(entities)

# 合并补充版
for conv, entities in supplement_merged.items():
    if conv not in all_merged:
        all_merged[conv] = {}
    all_merged[conv].update(entities)

print(f"   [OK] 合并完成：{len(all_merged)} 个对话")

# 7. 添加未合并的Person（保持原样）
print("\n7. 为每个对话添加未合并的 Person...")
for conv_name in conversation_persons:
    if conv_name not in all_merged:
        all_merged[conv_name] = {}

    # 获取该对话所有Person的名字
    all_person_names = conversation_persons[conv_name]

    # 找出已合并的person_ids
    merged_person_ids = set()
    for entity in all_merged[conv_name].values():
        merged_person_ids.update(entity['person_ids'])

    # 添加未合并的Person
    for person_name in all_person_names:
        # 检查这个名字的所有实例
        ids = person_index.get(person_name, [])
        for pid in ids:
            if persons[pid]['conversation'] == conv_name and pid not in merged_person_ids:
                # 这个Person未被合并，单独保留
                if person_name not in all_merged[conv_name]:
                    all_merged[conv_name][person_name] = {
                        'final_name': person_name,
                        'person_ids': [pid],
                        'original_names': [person_name],
                        'total_instances': 1
                    }
                else:
                    # 可能有多个实例
                    all_merged[conv_name][person_name]['person_ids'].append(pid)
                    all_merged[conv_name][person_name]['total_instances'] += 1

print(f"   [OK] 完成：所有对话都包含完整的Person列表")

# 8. 统计
print("\n=== 统计信息 ===")
total_conversations = len(all_merged)
total_entities = sum(len(entities) for entities in all_merged.values())
total_person_ids = sum(
    sum(len(e['person_ids']) for e in entities.values())
    for entities in all_merged.values()
)
merged_entities = sum(
    sum(1 for e in entities.values() if len(e['person_ids']) > 1)
    for entities in all_merged.values()
)

print(f"对话总数: {total_conversations}")
print(f"合并后实体总数: {total_entities}")
print(f"原始Person实例数: {total_person_ids}")
print(f"被合并的实体数: {merged_entities}")
print(f"平均每个对话: {total_entities / total_conversations:.1f} 个实体")

# 9. 保存结果
output_file = 'merged_entities_by_conversation.json'
print(f"\n9. 保存结果到 {output_file}...")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_merged, f, ensure_ascii=False, indent=2)

import os
file_size = os.path.getsize(output_file) / 1024 / 1024
print(f"   [OK] 保存完成！文件大小: {file_size:.2f} MB")

print("\n=== 融合完成！===")
print(f"\n输出文件: {output_file}")
print(f"包含 {total_conversations} 个对话的完整Person实体映射")
print(f"每个实体都有person_ids，可追溯到原始extraction文件中的events/relationships")
