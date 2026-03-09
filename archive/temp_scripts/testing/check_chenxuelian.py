#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查"陈雪莲"这个人名的详细信息
"""
import json
import sys
from pathlib import Path
from collections import Counter

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

output_dir = Path('../extractions/batch_20260227_001822')
json_files = list(output_dir.glob('session_*.json'))

target_name = "陈雪莲"

# 统计信息
conversations_with_target = set()
aliases_found = set()
sample_contexts = []

print(f"查找人名: {target_name}")
print("=" * 80)

for json_file in json_files:
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        conv_info = data.get('conversation', {})
        conv_name = conv_info.get('conversation_name', 'Unknown')

        entities = data.get('entities', {})
        if 'people' in entities:
            for person in entities['people']:
                person_name = person.get('name', '').strip()

                if person_name == target_name:
                    conversations_with_target.add(conv_name)

                    # 收集别名
                    if person.get('aliases'):
                        aliases_found.update(person.get('aliases'))

                    # 收集一些样本
                    if len(sample_contexts) < 5:
                        sample_contexts.append({
                            'conversation': conv_name,
                            'description': person.get('description', 'N/A'),
                            'file': json_file.name
                        })
    except:
        pass

print(f"\n统计结果:")
print(f"  出现在对话数: {len(conversations_with_target)}")
print(f"  别名数量: {len(aliases_found)}")

if aliases_found:
    print(f"\n  发现的别名:")
    for alias in list(aliases_found)[:20]:
        print(f"    - {alias}")

print(f"\n出现的对话 (前20个):")
for conv in list(conversations_with_target)[:20]:
    print(f"  - {conv}")

if len(conversations_with_target) > 20:
    print(f"  ... 还有 {len(conversations_with_target) - 20} 个对话")

print(f"\n样本描述:")
for i, ctx in enumerate(sample_contexts, 1):
    print(f"\n{i}. 对话: {ctx['conversation']}")
    print(f"   描述: {ctx['description']}")
    print(f"   文件: {ctx['file']}")

# 额外：检查是否某个对话名本身就包含"陈雪莲"
print(f"\n" + "=" * 80)
print(f"检查对话名称:")
matching_conv_names = [conv for conv in conversations_with_target if target_name in conv]
if matching_conv_names:
    print(f"  有 {len(matching_conv_names)} 个对话名包含'{target_name}':")
    for conv in matching_conv_names[:10]:
        print(f"    - {conv}")
else:
    print(f"  没有对话名包含'{target_name}'")

print("\n" + "=" * 80)
