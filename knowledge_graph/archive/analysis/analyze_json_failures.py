#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析JSON失败原因并尝试修复"""

import json
import sys
import io
import re
from pathlib import Path
from collections import Counter

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

EXTRACTION_DIR = Path("../extractions/test_three_users")

def fix_context_field(raw_json_str: str) -> str:
    """修复context字段中的多引号片段问题

    例如: "context": "text1", "text2"
    修复为: "context": "text1。text2"
    """
    # 模式：匹配 "context": "xxx", "yyy"
    pattern = r'"context":\s*"([^"]*)"(?:,\s*"([^"]*)")+'

    def replace_func(match):
        # 获取所有匹配的文本片段
        first = match.group(1)
        # 查找所有后续的引号片段
        remaining = re.findall(r',\s*"([^"]*)"', match.group(0))
        all_parts = [first] + remaining
        # 合并所有片段
        merged = '。'.join(all_parts)
        return f'"context": "{merged}"'

    fixed = re.sub(pattern, replace_func, raw_json_str)
    return fixed

def main():
    files = list(EXTRACTION_DIR.glob("session_*.json"))

    print("=" * 80)
    print("JSON失败分析与修复")
    print("=" * 80)
    print()

    failures = []
    error_types = Counter()

    # 收集失败案例
    for f in files:
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)

            if not data.get('success'):
                error_msg = data.get('error', '')
                failures.append({
                    'file': f.name,
                    'error': error_msg,
                    'raw_response': data.get('raw_response', '')
                })

                # 分类错误类型
                if 'Expecting \':\'delimiter' in error_msg:
                    error_types['colon_delimiter'] += 1
                elif 'Expecting \',\'delimiter' in error_msg:
                    error_types['comma_delimiter'] += 1
                elif 'Expecting value' in error_msg:
                    error_types['expecting_value'] += 1
                else:
                    error_types['other'] += 1

    print(f"失败总数: {len(failures)}")
    print("\n错误类型分布:")
    print("-" * 80)
    for error_type, count in error_types.most_common():
        print(f"  {error_type}: {count}")

    # 尝试修复
    print("\n" + "=" * 80)
    print("尝试修复...")
    print("=" * 80)

    fixed_count = 0
    unfixable = []

    for failure in failures:
        raw = failure['raw_response']

        # 跳过没有raw_response的
        if not raw:
            unfixable.append({
                'file': failure['file'],
                'original_error': failure['error'],
                'after_fix_error': 'No raw_response',
                'sample': ''
            })
            print(f"❌ {failure['file']}: 无raw_response")
            continue

        # 提取JSON部分（去掉markdown代码块）
        if '```json' in raw:
            json_str = raw.split('```json')[1].split('```')[0].strip()
        elif '```' in raw:
            json_str = raw.split('```')[1].split('```')[0].strip()
        else:
            json_str = raw.strip()

        # 尝试修复
        try:
            # 先尝试直接解析
            json.loads(json_str)
            fixed_count += 1
            print(f"✅ {failure['file']}: 原始JSON可解析（可能是提取逻辑问题）")
        except json.JSONDecodeError as e1:
            # 尝试修复context字段
            fixed_json = fix_context_field(json_str)
            try:
                json.loads(fixed_json)
                fixed_count += 1
                print(f"✅ {failure['file']}: 修复成功（context字段合并）")
            except json.JSONDecodeError as e2:
                unfixable.append({
                    'file': failure['file'],
                    'original_error': str(e1),
                    'after_fix_error': str(e2),
                    'sample': json_str[:200]
                })
                print(f"❌ {failure['file']}: 无法修复")

    print()
    print("=" * 80)
    print("修复总结:")
    print("=" * 80)
    print(f"可修复: {fixed_count}/{len(failures)} ({fixed_count/len(failures)*100:.1f}%)")
    print(f"无法修复: {len(unfixable)}")

    if unfixable:
        print("\n无法修复的案例 (前3个):")
        print("-" * 80)
        for item in unfixable[:3]:
            print(f"\n文件: {item['file']}")
            print(f"原始错误: {item['original_error']}")
            print(f"修复后错误: {item['after_fix_error']}")
            print(f"JSON样本: {item['sample']}...")

if __name__ == '__main__':
    main()
