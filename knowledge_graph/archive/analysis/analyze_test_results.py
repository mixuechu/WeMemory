#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析三用户测试提取结果"""

import json
import sys
import io
from pathlib import Path
from collections import Counter

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

EXTRACTION_DIR = Path("../extractions/test_three_users")

def main():
    files = list(EXTRACTION_DIR.glob("session_*.json"))
    print("=" * 70)
    print("三用户提取结果统计")
    print("=" * 70)
    print(f"\n总文件数: {len(files):,}\n")

    success = 0
    failed = 0
    total_cost = 0
    total_duration = 0
    total_entities = {
        'people': 0,
        'organizations': 0,
        'topics': 0,
        'events': 0,
        'locations': 0
    }
    total_relationships = 0
    conversation_ids = Counter()

    # 分析所有文件
    for f in files:
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)

            if data.get('success'):
                success += 1
                meta = data.get('extraction_metadata', {})
                total_cost += meta.get('cost', 0)
                total_duration += meta.get('duration_seconds', 0)

                entities = data.get('entities', {})
                for key in total_entities:
                    total_entities[key] += len(entities.get(key, []))
                total_relationships += len(entities.get('relationships', []))

                # 统计conversation_id
                conv_name = data['conversation']['conversation_name']
                conversation_ids[conv_name] += 1
            else:
                failed += 1

    print(f"成功提取: {success:,} ({success/(success+failed)*100:.1f}%)")
    print(f"失败: {failed}")
    print(f"\n总成本: ${total_cost:.2f}")
    print(f"总耗时: {total_duration/60:.1f} 分钟 ({total_duration/3600:.2f} 小时)")
    print(f"\n平均成本: ${total_cost/success:.4f} / 对话")
    print(f"平均耗时: {total_duration/success:.1f} 秒 / 对话")

    print(f"\n" + "=" * 70)
    print("平均实体统计 (每个对话):")
    print("=" * 70)
    for key, value in total_entities.items():
        print(f"  {key:15s}: {value/success:.1f}")
    print(f"  {'relationships':15s}: {total_relationships/success:.1f}")

    print(f"\n" + "=" * 70)
    print("对话分布:")
    print("=" * 70)
    for name, count in conversation_ids.most_common():
        print(f"  {name}: {count:,} 对话")

    # 检查conversation_id字段
    print(f"\n" + "=" * 70)
    print("conversation_id 字段检查 (前5个文件):")
    print("=" * 70)

    for f in files[:5]:
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)
            conv_name = data['conversation']['conversation_name']
            people = data['entities'].get('people', [])

            print(f"\n文件: {f.name}")
            print(f"  对话名: {conv_name}")
            print(f"  人物数: {len(people)}")

            for person in people[:3]:  # 只显示前3个
                print(f"    - {person['name']}: conversation_id={person.get('conversation_id', 'MISSING!')}")

if __name__ == '__main__':
    main()
