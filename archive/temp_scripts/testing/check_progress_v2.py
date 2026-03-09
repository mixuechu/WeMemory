#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import io
import json
from pathlib import Path
from collections import defaultdict

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 扫描所有提取的JSON文件
extraction_dir = Path('../extractions/batch_20260227_001822')
session_files = list(extraction_dir.glob('session_*.json'))

print(f'扫描中... 找到 {len(session_files)} 个批次文件\n')

# 统计每个对话的批次完成情况
conversation_batches = defaultdict(lambda: {'completed': set(), 'total': 0})

for json_file in session_files:
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if data.get('success') and 'conversation' in data:
                conv_info = data['conversation']
                conv_name = conv_info['conversation_name']
                batch_idx = conv_info['batch_index']
                total_batches = conv_info['total_batches']

                conversation_batches[conv_name]['completed'].add(batch_idx)
                conversation_batches[conv_name]['total'] = max(
                    conversation_batches[conv_name]['total'],
                    total_batches
                )
    except Exception as e:
        continue

# 分类统计
fully_completed = []
partially_completed = []
for conv_name, info in conversation_batches.items():
    completed_count = len(info['completed'])
    total_count = info['total']

    if completed_count == total_count:
        fully_completed.append((conv_name, total_count))
    elif completed_count > 0:
        partially_completed.append((conv_name, completed_count, total_count))

# 排序
fully_completed.sort(key=lambda x: x[1], reverse=True)
partially_completed.sort(key=lambda x: x[2], reverse=True)

# 读取进度信息
progress_path = extraction_dir / 'progress.json'
with open(progress_path, 'r', encoding='utf-8') as f:
    progress = json.load(f)

print('='*80)
print('📊 一晚上跑了多少好友的提取进度统计')
print('='*80)
print(f'\n✅ 完全完成的好友: {len(fully_completed)} 个')
print(f'🔄 部分完成的好友: {len(partially_completed)} 个')
print(f'📈 总对话数: {len(conversation_batches)} 个（已有进展）')
print(f'\n📦 批次进度:')
print(f'   成功: {progress["success"]:,} 批次')
print(f'   失败: {progress["failed"]:,} 批次')
print(f'   总计: {progress["success"] + progress["failed"]:,}/49,214 ({(progress["success"] + progress["failed"])/49214*100:.1f}%)')
print(f'\n💰 已花费: ${progress["total_cost"]:.2f}')

if fully_completed:
    print(f'\n✅ 完全完成的好友（前30个，按批次数排序）:')
    for i, (name, total) in enumerate(fully_completed[:30], 1):
        print(f'   {i:2d}. {name}: {total} 个批次 ✓')

if partially_completed:
    print(f'\n🔄 部分完成的好友（前20个）:')
    for i, (name, completed, total) in enumerate(partially_completed[:20], 1):
        percentage = completed / total * 100
        print(f'   {i:2d}. {name}: {completed}/{total} 批次 ({percentage:.0f}%)')

print(f'\n💡 预估完成时间: 基于当前速度约 {(49214 - progress["success"] - progress["failed"]) / 0.3 / 60:.1f} 小时')
