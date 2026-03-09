#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import io
import json
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 读取批次计划
batch_plan_path = Path('batch_plan.json')
with open(batch_plan_path, 'r', encoding='utf-8') as f:
    batch_plan = json.load(f)

# 读取进度
progress_path = Path('../extractions/batch_20260227_001822/progress.json')
with open(progress_path, 'r', encoding='utf-8') as f:
    progress = json.load(f)

# 统计已完成的对话
completed_batches = set(progress['processed_batches'])
conversation_status = {}

for conv_name, batches in batch_plan.items():
    total_batches = len(batches)
    completed = sum(1 for batch_id in batches if batch_id in completed_batches)
    conversation_status[conv_name] = {
        'total': total_batches,
        'completed': completed,
        'is_done': completed == total_batches
    }

# 统计完全完成的对话数
fully_completed = [name for name, status in conversation_status.items() if status['is_done']]
partially_completed = [name for name, status in conversation_status.items() if 0 < status['completed'] < status['total']]
not_started = [name for name, status in conversation_status.items() if status['completed'] == 0]

print('='*80)
print('📊 一晚上跑了多少好友的提取进度统计')
print('='*80)
print(f'\n✅ 完全完成的好友: {len(fully_completed)} 个')
print(f'🔄 部分完成的好友: {len(partially_completed)} 个')
print(f'⏸️  尚未开始的好友: {len(not_started)} 个')
print(f'\n📈 批次进度:')
print(f'   成功: {progress["success"]} 批次')
print(f'   失败: {progress["failed"]} 批次')
print(f'   总计: {progress["success"] + progress["failed"]}/49214 ({(progress["success"] + progress["failed"])/49214*100:.1f}%)')
print(f'\n💰 已花费: ${progress["total_cost"]:.2f}')

print(f'\n前20个完全完成的好友:')
for i, name in enumerate(fully_completed[:20], 1):
    status = conversation_status[name]
    print(f'   {i:2d}. {name}: {status["total"]} 个批次')

if partially_completed:
    print(f'\n前10个部分完成的好友:')
    for i, name in enumerate(partially_completed[:10], 1):
        status = conversation_status[name]
        print(f'   {i:2d}. {name}: {status["completed"]}/{status["total"]} 批次 ({status["completed"]/status["total"]*100:.0f}%)')
