#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析Person实体并输出到JSON避免编码问题
"""
import json
from pathlib import Path
from collections import defaultdict, Counter

output_dir = Path('../extractions/batch_20260227_001822')
json_files = list(output_dir.glob('session_*.json'))

print(f"处理文件数: {len(json_files):,}")

# 收集数据
all_persons = []
person_by_conversation = defaultdict(list)
person_names = Counter()

for i, json_file in enumerate(json_files):
    if i % 10000 == 0:
        print(f"进度: {i}/{len(json_files)}")

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        conv_info = data.get('conversation', {})
        conv_name = conv_info.get('conversation_name', 'Unknown')

        entities = data.get('entities', {})
        if 'people' in entities:
            for person in entities['people']:
                person_name = person.get('name', '').strip()
                if person_name:
                    all_persons.append({
                        'name': person_name,
                        'conversation': conv_name,
                        'aliases': person.get('aliases', []),
                        'description': person.get('description', '')
                    })
                    person_by_conversation[conv_name].append(person_name)
                    person_names[person_name] += 1
    except:
        pass

print("统计完成，生成报告...")

# 生成报告
report = {
    'summary': {
        'total_person_mentions': len(all_persons),
        'unique_person_names': len(person_names),
        'conversation_count': len(person_by_conversation)
    },
    'top_50_names': [
        {
            'name': name,
            'count': count,
            'conversations': len(set([p['conversation'] for p in all_persons if p['name'] == name]))
        }
        for name, count in person_names.most_common(50)
    ],
    'top_20_conversations': [
        {
            'conversation': conv,
            'unique_persons': len(set(persons))
        }
        for conv, persons in sorted(person_by_conversation.items(),
                                    key=lambda x: len(set(x[1])),
                                    reverse=True)[:20]
    ],
    'cross_conversation_names': []
}

# 找出跨对话的人名
for name, count in person_names.items():
    convs = set([p['conversation'] for p in all_persons if p['name'] == name])
    if len(convs) > 1:
        report['cross_conversation_names'].append({
            'name': name,
            'total_count': count,
            'conversation_count': len(convs)
        })

# 按对话数排序
report['cross_conversation_names'].sort(key=lambda x: x['conversation_count'], reverse=True)
report['cross_conversation_names'] = report['cross_conversation_names'][:30]

# 保存到JSON
output_file = Path('person_analysis_report.json')
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"\n报告已保存到: {output_file}")
print(f"\n基本统计:")
print(f"  总Person提及数: {report['summary']['total_person_mentions']:,}")
print(f"  唯一人名数: {report['summary']['unique_person_names']:,}")
print(f"  对话数: {report['summary']['conversation_count']}")
