#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

with open('test_ai_response.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# 提取AI响应部分
ai_response = content.split('=== AI RESPONSE ===')[1].strip()

# 去掉markdown
ai_response = ai_response.replace('```json', '').replace('```', '').strip()

# 尝试解析
try:
    data = json.loads(ai_response)
    print("JSON解析成功！")
    print(f"\n合并组数: {len(data['merge_groups'])}")

    # 显示前3组
    for i, group in enumerate(data['merge_groups'][:3], 1):
        print(f"\n组{i}:")
        print(f"  建议名: {group['suggested_name']}")
        print(f"  原因: {group['reason']}")
        print(f"  包含: {len(group['variants'])}个变体")
        print(f"  变体示例: {group['variants'][:5]}")

except json.JSONDecodeError as e:
    print(f"JSON解析失败: {e}")
    print(f"\nAI响应长度: {len(ai_response)}")
    print(f"前500字符:\n{ai_response[:500]}")
    print(f"\n后500字符:\n{ai_response[-500:]}")
