#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

# 设置UTF-8输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("检查对话名称")
print("=" * 80)

# 1. 源对话文件
source_dir = Path('../chat_data_filtered')
source_files = list(source_dir.glob('*.json'))
print(f"\n源对话文件总数: {len(source_files)}")

if len(source_files) > 0:
    print("\n前10个源对话名称：")
    for f in source_files[:10]:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                name = data.get('name', 'N/A')
                print(f"  - {name}")
        except Exception as e:
            print(f"  - 错误: {e}")
else:
    print("  源对话目录为空！")

# 2. 提取文件中的对话名
extraction_dir = Path('../extractions/batch_20260227_001822')
sample_files = list(extraction_dir.glob('session_*.json'))[:10]

print(f"\n提取文件中的对话名称（前10个）：")
for f in sample_files:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)
            conv_name = data.get('conversation', {}).get('conversation_name', 'N/A')
            print(f"  - {conv_name}")
    except Exception as e:
        print(f"  - 错误: {e}")

# 3. 查找"成都国税"
print(f"\n查找包含'国税'或'成都'的对话名：")
target_keywords = ['国税', '成都', 'guoshui', 'chengdu']

# 在源文件中查找
print("\n在源对话中：")
found_in_source = []
for f in source_files:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)
            name = data.get('name', '')
            for keyword in target_keywords:
                if keyword.lower() in name.lower():
                    found_in_source.append(name)
                    break
    except:
        pass

if found_in_source:
    for name in found_in_source[:5]:
        print(f"  - {name}")
else:
    print("  未找到")

# 在提取文件中查找（抽样1000个）
print("\n在提取文件中（抽样）：")
found_in_extraction = set()
sample_size = min(1000, len(list(extraction_dir.glob('session_*.json'))))
for f in list(extraction_dir.glob('session_*.json'))[:sample_size]:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)
            conv_name = data.get('conversation', {}).get('conversation_name', '')
            for keyword in target_keywords:
                if keyword in conv_name:
                    found_in_extraction.add(conv_name)
                    break
    except:
        pass

if found_in_extraction:
    for name in list(found_in_extraction)[:5]:
        print(f"  - {name}")
else:
    print("  未找到")

print("\n" + "=" * 80)
