#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
步骤1：收集所有Person实体数据
输出：person_database.pkl - 包含所有person的完整信息
"""
import json
import pickle
from pathlib import Path
from collections import defaultdict

print("=" * 80)
print("收集所有Person实体数据")
print("=" * 80)

output_dir = Path('../extractions/batch_20260227_001822')
json_files = list(output_dir.glob('session_*.json'))

print(f"\n总文件数: {len(json_files):,}")
print("开始收集...\n")

# 数据结构
person_database = {
    'persons': [],  # 所有person实例
    'person_index': defaultdict(list),  # 按name索引
    'conversation_persons': defaultdict(set)  # 按对话索引
}

processed = 0
for i, json_file in enumerate(json_files):
    if i % 5000 == 0:
        print(f"  进度: {i}/{len(json_files)} ({i/len(json_files)*100:.1f}%)")

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        conv_info = data.get('conversation', {})
        conv_name = conv_info.get('conversation_name', 'Unknown')

        entities = data.get('entities', {})
        if 'people' in entities:
            for person in entities['people']:
                name = person.get('name', '').strip()
                if not name:
                    continue

                # 创建person记录
                person_record = {
                    'name': name,
                    'conversation': conv_name,
                    'aliases': person.get('aliases', []),
                    'description': person.get('description', ''),
                    'source_file': json_file.name
                }

                # 添加到数据库
                person_database['persons'].append(person_record)
                person_database['person_index'][name].append(len(person_database['persons']) - 1)
                person_database['conversation_persons'][conv_name].add(name)

        processed += 1

    except Exception as e:
        pass

# 转换set为list以便序列化
person_database['conversation_persons'] = {
    k: list(v) for k, v in person_database['conversation_persons'].items()
}

# 保存
output_file = Path('person_database.pkl')
with open(output_file, 'wb') as f:
    pickle.dump(person_database, f)

print(f"\n完成！")
print(f"  处理文件: {processed:,}")
print(f"  Person实例总数: {len(person_database['persons']):,}")
print(f"  唯一人名数: {len(person_database['person_index']):,}")
print(f"  涉及对话数: {len(person_database['conversation_persons'])}")
print(f"\n保存到: {output_file}")
print("=" * 80)
