#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""优化版：为每个Person实体构建详细信息索引"""
import json
import pickle
import sys
from pathlib import Path
from collections import defaultdict

# 禁用输出缓冲
sys.stdout.reconfigure(line_buffering=True)

def safe_print(msg):
    print(msg, flush=True)

safe_print("=== 构建Person详细信息索引（优化版）===\n")

# 1. 加载person_database
safe_print("1. 加载 person_database.pkl...")
with open('person_database.pkl', 'rb') as f:
    db = pickle.load(f)
persons = db['persons']
safe_print(f"   [OK] {len(persons)} 个Person实例")

# 2. 构建反向索引：(conversation, name, source_file) -> [person_ids]
safe_print("\n2. 构建反向索引...")
person_lookup = defaultdict(list)
for pid, person in enumerate(persons):
    key = (person['conversation'], person['name'], person['source_file'])
    person_lookup[key].append(pid)

safe_print(f"   [OK] 索引构建完成，共 {len(person_lookup)} 个键")

# 3. 初始化结果结构
safe_print("\n3. 初始化结果结构...")
person_details = {pid: {'events': [], 'relationships': [], 'topics': []}
                  for pid in range(len(persons))}

# 4. 遍历所有extraction文件
extraction_dir = Path('D:/导出聊天记录excel/backups/before_merge_20260303_143226/batch_20260227_001822')
files = list(extraction_dir.glob('session_*.json'))

safe_print(f"\n4. 处理 {len(files)} 个extraction文件...")
safe_print("   每1000个文件报告一次进度...\n")

processed = 0
for i, file_path in enumerate(files):
    # 每1000个文件报告进度
    if i % 1000 == 0:
        safe_print(f"   进度: {i}/{len(files)} ({i*100//len(files)}%)")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not data.get('success'):
            continue

        conv_name = data['conversation']['conversation_name']
        entities = data.get('entities', {})
        source_file = file_path.name

        # 4.1 处理events
        for event in entities.get('events', []):
            participants = event.get('participants', [])

            event_data = {
                'name': event.get('name', ''),
                'type': event.get('type', ''),
                'description': event.get('description', ''),
                'time_description': event.get('time_description', ''),
                'location': event.get('location', ''),
                'participants': participants
            }

            for participant_name in participants:
                key = (conv_name, participant_name, source_file)
                for pid in person_lookup.get(key, []):
                    person_details[pid]['events'].append(event_data)

        # 4.2 处理relationships
        for rel in entities.get('relationships', []):
            source_name = rel.get('source', '')
            target_name = rel.get('target', '')
            rel_type = rel.get('type', '')

            # 处理source
            source_key = (conv_name, source_name, source_file)
            for pid in person_lookup.get(source_key, []):
                person_details[pid]['relationships'].append({
                    'type': rel_type,
                    'role': 'source',
                    'other': target_name,
                    'other_type': rel.get('target_type', ''),
                    'context': rel.get('context', '')
                })

            # 处理target（如果是Person）
            if rel.get('target_type') == 'Person':
                target_key = (conv_name, target_name, source_file)
                for pid in person_lookup.get(target_key, []):
                    person_details[pid]['relationships'].append({
                        'type': rel_type,
                        'role': 'target',
                        'other': source_name,
                        'other_type': rel.get('source_type', ''),
                        'context': rel.get('context', '')
                    })

            # 处理DISCUSSED_TOPIC
            if rel_type == 'DISCUSSED_TOPIC':
                source_key = (conv_name, source_name, source_file)
                for pid in person_lookup.get(source_key, []):
                    person_details[pid]['topics'].append({
                        'name': target_name,
                        'context': rel.get('context', '')
                    })

        processed += 1

    except Exception as e:
        # 静默跳过错误
        pass

safe_print(f"\n   [OK] 成功处理 {processed}/{len(files)} 个文件")

# 5. 统计
safe_print("\n5. 统计信息...")
total_events = sum(len(d['events']) for d in person_details.values())
total_rels = sum(len(d['relationships']) for d in person_details.values())
total_topics = sum(len(d['topics']) for d in person_details.values())

persons_with_events = sum(1 for d in person_details.values() if d['events'])
persons_with_rels = sum(1 for d in person_details.values() if d['relationships'])
persons_with_topics = sum(1 for d in person_details.values() if d['topics'])

safe_print(f"   总Events: {total_events}")
safe_print(f"   总Relationships: {total_rels}")
safe_print(f"   总Topics: {total_topics}")
safe_print(f"   有Events的Person: {persons_with_events}")
safe_print(f"   有Relationships的Person: {persons_with_rels}")
safe_print(f"   有Topics的Person: {persons_with_topics}")

# 6. 保存索引
output_file = 'person_details_index.json'
safe_print(f"\n6. 保存索引到 {output_file}...")

# 转换key为字符串
person_details_str = {str(k): v for k, v in person_details.items()}

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(person_details_str, f, ensure_ascii=False, indent=2)

import os
file_size = os.path.getsize(output_file) / 1024 / 1024
safe_print(f"   [OK] 保存完成！文件大小: {file_size:.2f} MB")

safe_print("\n=== 完成！===")
safe_print(f"索引文件: {output_file}")
safe_print(f"可在HTML界面中加载此文件查看每个Person的详细关联信息")
