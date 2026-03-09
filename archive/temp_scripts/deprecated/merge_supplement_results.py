#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并supplement结果并生成最终HTML"""
import json
from pathlib import Path

# 加载之前成功的103个对话结果（从原HTML中提取需要原始JSON，但我们没有，需要重新生成）
# 实际上之前运行generate_missing_suggestions.py时保存了结果
# 让我们直接加载retry_results.json（46个）

# 加载重试成功的46个对话
with open('retry_results.json', 'r', encoding='utf-8') as f:
    retry_results = json.load(f)

print(f"重试成功: {len(retry_results)} 个对话")
print(f"总合并组数: {sum(len(r['merge_groups']) for r in retry_results)}")

# 实际上我们需要原始的103个对话的数据
# 让我检查是否有保存的中间结果
import os
if os.path.exists('temp_supplement_results.json'):
    with open('temp_supplement_results.json', 'r', encoding='utf-8') as f:
        original_results = json.load(f)
    print(f"原始成功: {len(original_results)} 个对话")
else:
    print("警告：找不到原始的103个对话结果，只能使用重试的46个")
    original_results = []

# 合并结果
all_results = original_results + retry_results
all_results.sort(key=lambda x: len(x['merge_groups']), reverse=True)

print(f"\n合并后总计:")
print(f"  对话数: {len(all_results)}")
print(f"  合并组数: {sum(len(r['merge_groups']) for r in all_results)}")

# 保存合并结果
with open('all_supplement_results.json', 'w', encoding='utf-8') as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

print(f"\n合并结果已保存: all_supplement_results.json")
