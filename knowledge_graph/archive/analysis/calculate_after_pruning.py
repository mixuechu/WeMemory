#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys
import io
import pickle
from collections import Counter

# Windows UTF-8 fix
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 黑名单
BLACKLIST = [
    "🦄 西安留学生聚集地™🗿②",
    "📍XA留学生活动中心3⃣️群🌟",
    "鹏程.盘古α技术交流群①",
    "多伦多租房＋闲置群🇨🇦",
    "📍XA留学生活动中心2⃣️群💫",
    "二手家具5️⃣",
    "警民共建金水湾网格管理群",
    "租房群-13",
    "DT租房群",
    "停车群",
    "姜溪花都4号楼业主群",
    "多伦多区块链六群",
    "Cursor 号池105会员群",
    "大二～大三课本交易1️⃣",
    "GTA二手闲置租房求职考证互助群",
    "VIP 2群|一支烟花AI社区",
    "一支烟花AI 广州社区",
    "GAIDN广州AI社群",
    "Austin 的 AI 产品交流群",
    "628～29深圳站→已报名朋友进群",
    "河津年轻人创业交流群",
    "牛米之 🏠，平安永远"
]

# 读取数据
with open('vector_stores/conversations_complete.pkl', 'rb') as f:
    full_data = pickle.load(f)

metadata = full_data.get('metadata', [])

# 统计
total_conversations = len(metadata)
blacklisted_conversations = 0
remaining_conversations = 0

user_stats = Counter()
blacklisted_stats = Counter()

for item in metadata:
    conv_name = item.get('conversation_name', 'Unknown')

    if conv_name in BLACKLIST:
        blacklisted_conversations += 1
        blacklisted_stats[conv_name] += 1
    else:
        remaining_conversations += 1
        user_stats[conv_name] += 1

print("=" * 80)
print("剪枝统计结果")
print("=" * 80)
print()

print(f"原始总对话数: {total_conversations:,}")
print(f"黑名单对话数: {blacklisted_conversations:,} ({blacklisted_conversations/total_conversations*100:.1f}%)")
print(f"剩余对话数: {remaining_conversations:,} ({remaining_conversations/total_conversations*100:.1f}%)")
print()

print("=" * 80)
print("被删除的群聊及对话数")
print("=" * 80)
for name, count in sorted(blacklisted_stats.items(), key=lambda x: x[1], reverse=True):
    print(f"  - {name}: {count:,}")
print()

# 时间和成本估算
print("=" * 80)
print("提取预估")
print("=" * 80)
avg_time_per_conversation = 28  # 秒
workers = 20
cost_per_conversation = 0.001434  # 美元

total_seconds = remaining_conversations * avg_time_per_conversation / workers
total_hours = total_seconds / 3600
total_days = total_hours / 24
total_cost = remaining_conversations * cost_per_conversation

print(f"剩余对话数: {remaining_conversations:,}")
print(f"并行度: {workers} workers")
print(f"平均速度: {avg_time_per_conversation} 秒/对话")
print()
print(f"预计耗时:")
print(f"  - 总秒数: {total_seconds:,.0f} 秒")
print(f"  - 总小时: {total_hours:.1f} 小时")
print(f"  - 总天数: {total_days:.2f} 天")
print()
print(f"预计成本: ${total_cost:.2f}")
print()

# 节省的资源
saved_conversations = blacklisted_conversations
saved_seconds = saved_conversations * avg_time_per_conversation / workers
saved_hours = saved_seconds / 3600
saved_cost = saved_conversations * cost_per_conversation

print("=" * 80)
print("节省的资源")
print("=" * 80)
print(f"节省对话数: {saved_conversations:,}")
print(f"节省时间: {saved_hours:.1f} 小时 ({saved_hours/24:.2f} 天)")
print(f"节省成本: ${saved_cost:.2f}")
print()

# 保留的群聊
remaining_groups = [name for name, count in user_stats.items()
                   if any(keyword in name for keyword in ['群', '社区', '社群'])
                   or any(emoji in name for emoji in ['🦄','📍','™','🗿','🌟','🏠','🇨🇦','💫','🐔'])]

if remaining_groups:
    print("=" * 80)
    print("保留的群聊")
    print("=" * 80)
    for name in remaining_groups:
        count = user_stats[name]
        print(f"  - {name}: {count:,}")
    print()

print("=" * 80)
print("✅ 剪枝完成后，耗时从 3天 降至 {:.2f}天".format(total_days))
print("=" * 80)
