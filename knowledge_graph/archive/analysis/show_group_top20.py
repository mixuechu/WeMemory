#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys
import io
import pickle
from collections import Counter

# Windows UTF-8 fix
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 读取完整数据
with open('vector_stores/conversations_complete.pkl', 'rb') as f:
    full_data = pickle.load(f)

metadata = full_data.get('metadata', [])

user_stats = Counter()
for item in metadata:
    conv_name = item.get('conversation_name', 'Unknown')
    user_stats[conv_name] += 1

# 转换为列表
data = [{'rank': i, 'name': user, 'conversations': count}
        for i, (user, count) in enumerate(user_stats.most_common(), 1)]

# 过滤出群聊
def is_group(name):
    group_keywords = ['群', '社区', '社群']
    group_emojis = ['🦄','📍','™','🗿','🌟','🏠','🇨🇦','💫','🐔']

    # 包含"群"字
    if any(keyword in name for keyword in group_keywords):
        return True

    # 包含群聊常见emoji
    if any(emoji in name for emoji in group_emojis):
        return True

    # 包含数字+emoji组合（如"3⃣️群"）
    if any(c in name for c in ['①','②','③','④','⑤','1️⃣','2️⃣','3️⃣','4️⃣','5️⃣']):
        return True

    return False

groups = [item for item in data if is_group(item['name'])]

print('Top 50 群聊对话数量：')
print('=' * 70)
print(f"{'排名':>4} | {'名称':40} | {'对话数':>8}")
print('-' * 70)

for i, item in enumerate(groups[:50], 1):
    rank = item['rank']  # 原始排名
    name = item['name']
    count = item['conversations']

    # 截断过长的名字
    display_name = name[:38] + '..' if len(name) > 40 else name

    print(f"{i:4} | {display_name:40} | {count:8,} (原#{rank})")

print('-' * 70)

# 统计
total_group_top50 = sum(item['conversations'] for item in groups[:50]) if len(groups) >= 50 else sum(item['conversations'] for item in groups)
actual_count = min(50, len(groups))
print(f"\n统计：")
print(f"  - Top{actual_count}群聊总对话数: {total_group_top50:,}")
print(f"  - 占全部对话比例: {total_group_top50/183287*100:.1f}%")
print(f"  - 总群聊数: {len(groups)}")
