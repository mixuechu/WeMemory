#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只运行分析，不执行清理"""

import sys
import io
import json

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from intelligent_graph_cleaner_batch import IntelligentGraphCleanerBatch

print("=" * 80)
print("智能图谱分析 - 仅分析不执行")
print("=" * 80)

with IntelligentGraphCleanerBatch() as cleaner:
    # 步骤1: 分析重复实体
    cleaner.analyze_duplicates(similarity_threshold=0.85, auto_merge_exact=True)

    # 步骤2: 分析低价值实体
    cleaner.analyze_low_value_persons(auto_delete_rules=True)

    # 步骤3: 生成报告
    operations_file = cleaner.generate_operations_script()

    # 显示详细结果
    print("\n" + "=" * 80)
    print("分析结果详情")
    print("=" * 80)

    print("\n【自动操作】")
    print(f"总计: {len(cleaner.analysis_results['auto_actions'])} 个")

    merge_count = sum(1 for a in cleaner.analysis_results['auto_actions'] if a['type'] == 'merge')
    delete_count = sum(1 for a in cleaner.analysis_results['auto_actions'] if a['type'] == 'delete')

    print(f"  - 自动合并: {merge_count} 对")
    if merge_count > 0:
        print("\n  示例（前10个）：")
        for i, action in enumerate([a for a in cleaner.analysis_results['auto_actions'] if a['type'] == 'merge'][:10], 1):
            src = action['source'][0]
            tgt = action['target'][0]
            print(f"    {i}. {src} → {tgt} ({action['reason']})")

    print(f"\n  - 自动删除: {delete_count} 个")
    if delete_count > 0:
        print("\n  示例（前10个）：")
        for i, action in enumerate([a for a in cleaner.analysis_results['auto_actions'] if a['type'] == 'delete'][:10], 1):
            name = action['person'][0]
            print(f"    {i}. {name} ({action['reason']})")

    print("\n【LLM建议】")
    print(f"总计: {len(cleaner.analysis_results['llm_suggestions'])} 个")

    llm_merge = [s for s in cleaner.analysis_results['llm_suggestions'] if s['type'] == 'merge']
    llm_delete = [s for s in cleaner.analysis_results['llm_suggestions'] if s['type'] == 'delete']

    print(f"  - LLM建议合并: {len(llm_merge)} 对")
    if llm_merge:
        print("\n  示例（前10个）：")
        for i, sug in enumerate(llm_merge[:10], 1):
            src = sug['source'][0]
            tgt = sug['target'][0]
            print(f"    {i}. {src} → {tgt}")
            print(f"       理由: {sug['reason']}")
            print(f"       置信度: {sug['confidence']:.2%}")

    print(f"\n  - LLM建议删除: {len(llm_delete)} 个")
    if llm_delete:
        print("\n  示例（前10个）：")
        for i, sug in enumerate(llm_delete[:10], 1):
            name = sug['person'][0]
            print(f"    {i}. {name}")
            print(f"       理由: {sug['reason']}")
            print(f"       置信度: {sug['confidence']:.2%}")

    print("\n【需要人工审核】")
    print(f"总计: {len(cleaner.analysis_results['needs_review'])} 个")
    if cleaner.analysis_results['needs_review']:
        print("\n  示例（前5个）：")
        for i, review in enumerate(cleaner.analysis_results['needs_review'][:5], 1):
            if review['type'] == 'merge':
                p1 = review['person1'][0]
                p2 = review['person2'][0]
                print(f"    {i}. {p1} vs {p2}")
                print(f"       建议: {review['suggestion']['action']}")
                print(f"       置信度: {review['suggestion']['confidence']:.2%}")
                print(f"       理由: {review['suggestion']['reason']}")
            elif review['type'] == 'delete':
                name = review['person'][0]
                print(f"    {i}. {name}")
                print(f"       建议: {review['suggestion']['action']}")
                print(f"       置信度: {review['suggestion']['confidence']:.2%}")
                print(f"       理由: {review['suggestion']['reason']}")

    print("\n" + "=" * 80)
    print("✅ 分析完成")
    print(f"操作脚本: {operations_file}")
    print("=" * 80)
