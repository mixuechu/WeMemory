#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查关系词的提取情况
"""
import json
from pathlib import Path
from collections import defaultdict
import random

output_dir = Path('../extractions/batch_20260227_001822')
all_files = list(output_dir.glob('session_*.json'))

# 抽样1000个文件
random.seed(42)
sample_files = random.sample(all_files, min(1000, len(all_files)))

# 关注的关系词
relationship_keywords = ['妈', '妈妈', '爸', '爸爸', '老婆', '老公', '儿子', '女儿', '哥哥', '姐姐', '弟弟', '妹妹']

# 收集数据
relationship_examples = defaultdict(list)

print(f"分析样本文件: {len(sample_files)}")
print("查找关系词的提取方式...\n")

for json_file in sample_files:
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        conv_name = data.get('conversation', {}).get('conversation_name', 'Unknown')
        entities = data.get('entities', {})

        if 'people' in entities:
            for person in entities['people']:
                name = person.get('name', '').strip()

                # 检查是否包含关系词
                for keyword in relationship_keywords:
                    if keyword in name:
                        relationship_examples[keyword].append({
                            'name': name,
                            'conversation': conv_name,
                            'description': person.get('description', ''),
                            'aliases': person.get('aliases', [])
                        })
                        # 每个关键词只收集前5个例子
                        if len(relationship_examples[keyword]) >= 5:
                            break

                # 如果收集够了就跳出
                if all(len(examples) >= 5 for examples in relationship_examples.values()):
                    break
    except:
        pass

# 生成报告
report = {}

for keyword, examples in relationship_examples.items():
    if examples:
        report[keyword] = examples

# 保存到JSON
with open('relationship_extraction_examples.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print("=" * 80)
print("关系词提取示例分析")
print("=" * 80)

for keyword in relationship_keywords:
    if keyword in relationship_examples:
        examples = relationship_examples[keyword]
        print(f"\n关键词: '{keyword}' (找到 {len(examples)} 个例子)")

        for i, ex in enumerate(examples[:3], 1):
            print(f"\n  例子 {i}:")
            print(f"    提取的名字: {ex['name']}")
            print(f"    所在对话: {ex['conversation']}")
            if ex['description']:
                print(f"    描述: {ex['description'][:100]}")
            if ex['aliases']:
                print(f"    别名: {ex['aliases'][:3]}")

print(f"\n\n完整报告已保存到: relationship_extraction_examples.json")
print("=" * 80)
