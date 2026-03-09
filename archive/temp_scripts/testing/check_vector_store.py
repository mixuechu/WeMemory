#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查向量库数据结构"""
import pickle
import random

# 加载向量库
with open("vector_stores/conversations_complete.pkl", 'rb') as f:
    data = pickle.load(f)

metadata = data.get('metadata', [])

print(f"总记忆数: {len(metadata)}")
print("\n随机查看10个记忆片段的结构：\n")

samples = random.sample(metadata, 10)

with open("knowledge_graph/vector_store_check.txt", 'w', encoding='utf-8') as f:
    for i, item in enumerate(samples, 1):
        f.write(f"=== 样本 {i} ===\n")
        f.write(f"对话名称: {item.get('conversation_name', 'N/A')}\n")
        f.write(f"Content_text: {item.get('content_text', 'N/A')[:100]}...\n")
        f.write(f"Context_text: {item.get('context_text', 'N/A')[:100]}...\n")
        f.write(f"Timestamp: {item.get('start_timestamp', 'N/A')}\n")
        f.write(f"Keys: {list(item.keys())}\n\n")

    # 找到有实际内容的对话
    f.write("\n查找有实际内容的对话：\n\n")
    conversations_with_content = {}

    for item in metadata:
        content = item.get('content_text', '')
        if content and len(content) > 10:  # 有实际内容
            conv_name = item.get('conversation_name', 'Unknown')
            if conv_name not in conversations_with_content:
                conversations_with_content[conv_name] = []
            conversations_with_content[conv_name].append(item)

    # 找到消息数量适中的对话
    suitable = []
    for conv_name, messages in conversations_with_content.items():
        if 5 <= len(messages) <= 15:
            suitable.append((conv_name, messages))

    f.write(f"\n找到 {len(suitable)} 个适合测试的对话（5-15条消息，有实际内容）\n\n")
    f.write("前20个：\n")
    for i, (name, messages) in enumerate(suitable[:20], 1):
        f.write(f"{i}. {name} ({len(messages)} 条消息)\n")
        f.write(f"   第一条: {messages[0].get('content_text', '')[:80]}...\n\n")

print("结果已保存到 knowledge_graph/vector_store_check.txt")
