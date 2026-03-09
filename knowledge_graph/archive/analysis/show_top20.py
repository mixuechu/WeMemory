#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys
import io

# Windows UTF-8 fix
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('knowledge_graph/top_users.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('Top 20 好友/群聊对话数量：')
print('=' * 80)
print(f"{'排名':>4} | {'名称':40} | {'对话数':>8} | {'类型':6}")
print('-' * 80)

for item in data[:20]:
    rank = item['rank']
    name = item['name']
    count = item['conversations']

    # 判断是否是群聊
    is_group = '群' in name or any(emoji in name for emoji in ['🦄','📍','™','🗿','🌟','🏠','🇨🇦','💫'])
    conv_type = '群聊' if is_group else '个人'

    # 截断过长的名字
    display_name = name[:38] + '..' if len(name) > 40 else name

    print(f"{rank:4} | {display_name:40} | {count:8,} | {conv_type:6}")

print('-' * 80)

# 统计
total_top20 = sum(item['conversations'] for item in data[:20])
group_count = sum(1 for item in data[:20] if '群' in item['name'] or any(e in item['name'] for e in ['🦄','📍','™','🗿','🌟','🏠','🇨🇦','💫']))
personal_count = 20 - group_count

print(f"\n统计：")
print(f"  - 群聊数量: {group_count}")
print(f"  - 个人好友: {personal_count}")
print(f"  - Top20总对话数: {total_top20:,}")
print(f"  - 占总数比例: {total_top20/183287*100:.1f}%")
