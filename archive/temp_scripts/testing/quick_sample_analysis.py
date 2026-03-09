#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速抽样分析 - 只分析5000个文件
"""
import json
from pathlib import Path
from collections import Counter

output_dir = Path('../extractions/batch_20260227_001822')
all_files = list(output_dir.glob('session_*.json'))

# 抽样5000个文件
import random
random.seed(42)
sample_files = random.sample(all_files, min(5000, len(all_files)))

print(f"总文件数: {len(all_files):,}")
print(f"抽样: {len(sample_files):,}")
print("开始分析...")

person_names = Counter()
person_to_convs = {}

for i, json_file in enumerate(sample_files):
    if i % 1000 == 0:
        print(f"  {i}/{len(sample_files)}")

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        conv_name = data.get('conversation', {}).get('conversation_name', 'Unknown')
        entities = data.get('entities', {})

        if 'people' in entities:
            for person in entities['people']:
                name = person.get('name', '').strip()
                if name:
                    person_names[name] += 1
                    if name not in person_to_convs:
                        person_to_convs[name] = set()
                    person_to_convs[name].add(conv_name)
    except:
        pass

print("\n生成报告...")

# TOP 30人名
report = {
    'sample_size': len(sample_files),
    'unique_names': len(person_names),
    'top_30_names': []
}

for name, count in person_names.most_common(30):
    convs = person_to_convs.get(name, set())
    report['top_30_names'].append({
        'name': name,
        'count': count,
        'conversation_count': len(convs),
        'sample_conversations': list(convs)[:3]
    })

# 保存
with open('quick_analysis.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"\n完成！报告保存到: quick_analysis.json")
print(f"唯一人名数: {len(person_names):,}")
print(f"\nTOP 10:")
for name, count in person_names.most_common(10):
    print(f"  {name}: {count}次")
