#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析失败批次"""

import sys
import io
import re
from collections import Counter

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

log_file = '../extractions/batch_20260227_001822/extraction_log.txt'

failed_batches = []
with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
    for line in f:
        if '❌ 提取失败' in line:
            # 提取: [对话名 batch 编号]: 错误信息
            match = re.search(r'❌ 提取失败 \[(.+?) batch (\d+)\]: (.+)$', line)
            if match:
                conv_name = match.group(1)
                batch_num = match.group(2)
                error_msg = match.group(3)
                failed_batches.append({
                    'conv': conv_name,
                    'batch': int(batch_num),
                    'error': error_msg,
                    'line': line.strip()
                })

print('='*70)
print(f'🔍 失败批次分析（共{len(failed_batches)}个）')
print('='*70)

# 按对话统计
conv_counter = Counter(item['conv'] for item in failed_batches)
print(f'\n📊 失败分布（按对话）:')
for conv, count in conv_counter.most_common(15):
    print(f'  {conv}: {count} 个批次')

# 按错误类型统计
error_types = Counter()
for item in failed_batches:
    error = item['error']
    if 'Expecting \':\''.lower() in error.lower() or 'delimiter' in error.lower():
        error_types['JSON格式错误(冒号/逗号)'] += 1
    elif 'Expecting value' in error:
        error_types['JSON格式错误(缺少值)'] += 1
    elif '429' in error:
        error_types['API限速(429)'] += 1
    elif '503' in error or 'TCP' in error:
        error_types['网络错误(503 TCP)'] += 1
    else:
        error_types['其他错误'] += 1

print(f'\n📊 失败类型统计:')
for error_type, count in error_types.most_common():
    print(f'  {error_type}: {count} 次 ({count/len(failed_batches)*100:.1f}%)')

print(f'\n💾 失败批次详情（前20个）:')
for i, item in enumerate(failed_batches[:20], 1):
    error_short = item['error'][:60] + '...' if len(item['error']) > 60 else item['error']
    print(f'{i:2d}. [{item["conv"]}] batch {item["batch"]}: {error_short}')

print(f'\n💡 关键结论:')
print(f'  ✅ 所有失败都记录在 extraction_log.txt 中')
print(f'  ✅ 可以通过日志重新提取失败批次')
print(f'  ❌ progress.json 只记录了成功的 batch_id，失败的没有单独列表')
print(f'  ✅ 重新运行时，失败批次会自动重试（因为没有生成文件）')
print(f'  ')
print(f'  失败率: {len(failed_batches)}/11020 = {len(failed_batches)/11020*100:.2f}%')
