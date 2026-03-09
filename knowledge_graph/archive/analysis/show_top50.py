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
        for i, (user, count) in enumerate(user_stats.most_common(50), 1)]

# 判断是否是群聊
def is_group(name):
    group_keywords = ['群', '社区', '社群']
    group_emojis = ['🦄','📍','™','🗿','🌟','🏠','🇨🇦','💫','🐔']

    if any(keyword in name for keyword in group_keywords):
        return True
    if any(emoji in name for emoji in group_emojis):
        return True
    if any(c in name for c in ['①','②','③','④','⑤','1️⃣','2️⃣','3️⃣','4️⃣','5️⃣']):
        return True
    return False

print('Top 50 好友/群聊对话数量：')
print('=' * 75)
print(f"{'排名':>4} | {'名称':42} | {'对话数':>8} | {'类型':4}")
print('-' * 75)

for item in data:
    rank = item['rank']
    name = item['name']
    count = item['conversations']

    conv_type = '群聊' if is_group(name) else '个人'

    # 截断过长的名字
    display_name = name[:40] + '..' if len(name) > 42 else name

    print(f"{rank:4} | {display_name:42} | {count:8,} | {conv_type:4}")

print('-' * 75)

# 统计
total_top50 = sum(item['conversations'] for item in data)
group_count = sum(1 for item in data if is_group(item['name']))
personal_count = 50 - group_count

print(f"\n统计：")
print(f"  - 群聊数量: {group_count}")
print(f"  - 个人好友: {personal_count}")
print(f"  - Top50总对话数: {total_top50:,}")
print(f"  - 占总数比例: {total_top50/183287*100:.1f}%")
