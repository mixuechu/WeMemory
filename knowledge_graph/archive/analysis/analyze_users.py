#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析用户对话数量分布"""

import pickle
import json
from collections import Counter

with open('vector_stores/conversations_complete.pkl', 'rb') as f:
    data = pickle.load(f)

metadata = data.get('metadata', [])

# 按用户统计对话数量
user_stats = Counter()
for item in metadata:
    conv_name = item.get('conversation_name', 'Unknown')
    user_stats[conv_name] += 1

# 输出Top 30
top30 = []
for i, (user, count) in enumerate(user_stats.most_common(30), 1):
    top30.append({
        'rank': i,
        'name': user,
        'conversations': count
    })

# 保存到JSON
with open('knowledge_graph/top_users.json', 'w', encoding='utf-8') as f:
    json.dump(top30, f, ensure_ascii=False, indent=2)

print(f'Top 30 users saved to: knowledge_graph/top_users.json')
print(f'Total users: {len(user_stats)}')
print(f'Total conversations: {sum(user_stats.values())}')
