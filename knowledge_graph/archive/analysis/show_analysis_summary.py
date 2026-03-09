#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""展示已有的分析结果（不调用LLM）"""

import sys
import io

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from graph_manager import GraphManager

print("=" * 80)
print("JY和吉月对话提取结果的智能分析")
print("=" * 80)

with GraphManager() as gm:
    # 1. 重复实体分析
    print("\n【1】重复实体（需要合并）")
    print("=" * 80)
    duplicates = gm.find_duplicate_persons(0.85)

    # 分类统计
    case_diff = [d for d in duplicates if d['person1'][0].lower() == d['person2'][0].lower()]
    similar = [d for d in duplicates if d['person1'][0].lower() != d['person2'][0].lower()]

    print(f"\n总计: {len(duplicates)} 对")
    print(f"  - 大小写不同（自动合并）: {len(case_diff)} 对")
    print(f"  - 名字相似（需要判断）: {len(similar)} 对")

    if case_diff:
        print(f"\n【大小写不同 - 应自动合并】前20个：")
        for i, dup in enumerate(case_diff[:20], 1):
            p1, p2 = dup['person1'][0], dup['person2'][0]
            target = p1 if p1[0].isupper() else p2
            source = p2 if target == p1 else p1
            print(f"  {i}. {source} → {target}")

    if similar:
        print(f"\n【名字相似 - 需要LLM判断】前20个：")
        for i, dup in enumerate(similar[:20], 1):
            p1, p2 = dup['person1'][0], dup['person2'][0]
            print(f"  {i}. {p1} vs {p2} ({dup['reason']})")

    # 2. 孤立节点
    print("\n\n【2】孤立节点（无任何关系，应删除）")
    print("=" * 80)
    isolated = gm.find_isolated_persons()
    print(f"\n总计: {len(isolated)} 个")

    # 分类
    pure_number = [p for p in isolated if p['name'].isdigit()]
    useless = [p for p in isolated if any(kw in p['name'] for kw in ['第三方', '某', '未知', '路人'])]
    others = [p for p in isolated if p not in pure_number and p not in useless]

    print(f"  - 纯数字ID: {len(pure_number)} 个")
    print(f"  - 泛指/无用: {len(useless)} 个")
    print(f"  - 其他: {len(others)} 个")

    if pure_number:
        print(f"\n【纯数字ID】：")
        for p in pure_number:
            print(f"  - {p['name']} ({p['conversation_name']})")

    if useless[:10]:
        print(f"\n【泛指/无用】前10个：")
        for p in useless[:10]:
            print(f"  - {p['name']} ({p['conversation_name']})")

    if others[:10]:
        print(f"\n【其他孤立节点】前10个：")
        for p in others[:10]:
            print(f"  - {p['name']} ({p['conversation_name']})")

    # 3. 低价值节点
    print("\n\n【3】低价值节点（关系少或名字无意义）")
    print("=" * 80)
    low_value = gm.find_low_value_persons()

    # 去除已经在孤立节点中的
    isolated_keys = {(p['name'], p['conversation_name']) for p in isolated}
    low_value_filtered = [p for p in low_value if (p['name'], p['conversation_name']) not in isolated_keys]

    print(f"\n总计: {len(low_value_filtered)} 个（不含孤立节点）")

    # 分类
    rel_1 = [p for p in low_value_filtered if p.get('relationships', 0) == 1]
    rel_2 = [p for p in low_value_filtered if p.get('relationships', 0) == 2]

    print(f"  - 仅1个关系: {len(rel_1)} 个")
    print(f"  - 仅2个关系: {len(rel_2)} 个")

    if rel_1[:15]:
        print(f"\n【仅1个关系】前15个：")
        for p in rel_1[:15]:
            print(f"  - {p['name']} ({p['conversation_name']}) - {p['reason']}")

    # 4. 总结
    print("\n\n" + "=" * 80)
    print("【总结】建议的清理操作")
    print("=" * 80)

    auto_merge = len(case_diff)
    auto_delete = len(pure_number) + len(useless)
    need_llm_merge = len(similar)
    need_llm_delete = len(others) + len(low_value_filtered)

    print(f"\n自动操作（无需LLM）：")
    print(f"  - 自动合并（大小写）: {auto_merge} 对")
    print(f"  - 自动删除（纯数字+泛指）: {auto_delete} 个")

    print(f"\n需要LLM判断：")
    print(f"  - 名字相似实体对: {need_llm_merge} 对")
    print(f"  - 低价值实体: {need_llm_delete} 个")

    total_persons_before = 429
    total_after_auto = total_persons_before - auto_merge - auto_delete

    print(f"\n清理效果预估：")
    print(f"  - 清理前: {total_persons_before} 个Person节点")
    print(f"  - 自动清理后: ~{total_after_auto} 个")
    print(f"  - LLM判断后: 预计进一步减少30-50个")

    print("\n" + "=" * 80)
