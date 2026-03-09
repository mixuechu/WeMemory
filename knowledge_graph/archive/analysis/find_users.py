#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pickle
import sys
import io
from collections import Counter

# Windows UTF-8 fix
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('vector_stores/conversations_complete.pkl', 'rb') as f:
    data = pickle.load(f)

metadata = data.get('metadata', [])
user_stats = Counter()

for item in metadata:
    conv_name = item.get('conversation_name', 'Unknown')
    user_stats[conv_name] += 1

# 查找这三个人
targets = ['吉月', 'JY', 'weiwei']

print('查找目标用户:')
print('=' * 60)

found = {}
for name, count in user_stats.most_common():
    for target in targets:
        if target.lower() in name.lower():
            found[name] = count
            print(f'{name}: {count:,} 对话')

print()
print('=' * 60)
if len(found) >= 3:
    total = sum(found.values())
    time_hours = total * 28 / 20 / 3600
    cost = total * 0.001434
    print(f'总计: {total:,} 对话')
    print(f'耗时: {time_hours:.2f} 小时 ({time_hours*60:.0f} 分钟)')
    print(f'成本: ${cost:.2f}')
else:
    print(f'只找到 {len(found)}/{len(targets)} 个用户')
