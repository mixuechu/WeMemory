#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查Person最多的几个对话的详细信息
"""
import json
from pathlib import Path
from collections import defaultdict

# 加载所有提取文件
output_dir = Path('../extractions/batch_20260227_001822')
json_files = list(output_dir.glob('session_*.json'))

# 按对话统计Person
conv_persons = defaultdict(set)
conv_details = {}

for json_file in json_files:
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        conv_info = data.get('conversation', {})
        conv_name = conv_info.get('conversation_name', 'Unknown')

        # 保存对话详情
        if conv_name not in conv_details:
            conv_details[conv_name] = {
                'type': conv_info.get('conversation_type', 'unknown'),
                'first_time': conv_info.get('conversation_time', 'unknown'),
                'batch_count': 0,
                'message_count': 0
            }

        conv_details[conv_name]['batch_count'] += 1
        conv_details[conv_name]['message_count'] += conv_info.get('message_count', 0)

        entities = data.get('entities', {})
        if 'people' in entities:
            for person in entities['people']:
                person_name = person.get('name', '').strip()
                if person_name:
                    conv_persons[conv_name].add(person_name)
    except Exception as e:
        pass

# 按Person数排序
conv_person_list = [(conv, len(persons)) for conv, persons in conv_persons.items()]
conv_person_list.sort(key=lambda x: x[1], reverse=True)

print("=" * 80)
print("Person数量最多的对话 (TOP 20)")
print("=" * 80)

for i, (conv_name, person_count) in enumerate(conv_person_list[:20], 1):
    details = conv_details.get(conv_name, {})
    print(f"\n{i}. {conv_name}")
    print(f"   唯一Person数: {person_count}")
    print(f"   对话类型: {details.get('type', 'unknown')}")
    print(f"   最早时间: {details.get('first_time', 'unknown')}")
    print(f"   batch数: {details.get('batch_count', 0)}")
    print(f"   消息数: {details.get('message_count', 0)}")

    # 显示部分人名
    persons = list(conv_persons[conv_name])[:10]
    print(f"   人名示例: {', '.join(persons[:5])}")

print("\n" + "=" * 80)
