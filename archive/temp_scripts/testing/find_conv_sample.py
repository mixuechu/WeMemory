#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
找到"成都国税"对话的一个示例文件并显示详情
"""
import json
from pathlib import Path

output_dir = Path('../extractions/batch_20260227_001822')
json_files = list(output_dir.glob('session_*.json'))

target_conv = "成都国税"
found = False

for json_file in json_files:
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        conv_info = data.get('conversation', {})
        conv_name = conv_info.get('conversation_name', '')

        if target_conv in conv_name:
            print("=" * 80)
            print(f"找到对话: {conv_name}")
            print("=" * 80)
            print(f"\n文件: {json_file.name}")
            print(f"\n对话信息:")
            print(f"  名称: {conv_info.get('conversation_name', 'N/A')}")
            print(f"  类型: {conv_info.get('conversation_type', 'N/A')}")
            print(f"  时间: {conv_info.get('conversation_time', 'N/A')}")
            print(f"  消息数: {conv_info.get('message_count', 'N/A')}")
            print(f"  batch索引: {conv_info.get('batch_index', 'N/A')}")

            # 显示部分人名
            entities = data.get('entities', {})
            if 'people' in entities:
                people = entities['people']
                print(f"\n本batch中的Person数: {len(people)}")
                print(f"\n前10个人名:")
                for i, person in enumerate(people[:10], 1):
                    print(f"  {i}. {person.get('name', 'N/A')}")
                    if person.get('aliases'):
                        print(f"     别名: {person.get('aliases')}")

            found = True
            break

    except Exception as e:
        pass

if not found:
    print(f"未找到包含'{target_conv}'的对话")
