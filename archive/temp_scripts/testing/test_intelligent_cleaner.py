#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试智能清理器 - 只处理少量样本"""

import sys
import io
from intelligent_graph_cleaner import IntelligentGraphCleaner

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("=" * 80)
print("智能图谱清理工具 - 测试版（仅处理前5对重复）")
print("=" * 80)

with IntelligentGraphCleaner() as cleaner:
    # 获取重复实体
    duplicates = cleaner.gm.find_duplicate_persons(0.85)
    print(f"\n总共找到 {len(duplicates)} 对重复实体")
    print("只处理前5对进行测试...")

    # 手动处理前5对
    for i, dup in enumerate(duplicates[:5], 1):
        p1_name, p1_conv = dup['person1']
        p2_name, p2_conv = dup['person2']

        print(f"\n{'=' * 80}")
        print(f"处理 {i}/5: {p1_name} vs {p2_name}")
        print(f"原因: {dup['reason']}")
        print('=' * 80)

        # 大小写完全相同 → 自动合并
        if p1_name.lower() == p2_name.lower() and p1_name != p2_name:
            target = p1_name if p1_name[0].isupper() else p2_name
            source = p2_name if target == p1_name else p1_name

            print(f"✅ 规则判断: 大小写不同，自动合并")
            print(f"   {source} → {target}")

            cleaner.analysis_results['auto_actions'].append({
                'type': 'merge',
                'source': [source, p1_conv],
                'target': [target, p1_conv],
                'reason': '大小写不同',
                'confidence': 1.0
            })
            continue

        # 其他情况 → LLM判断
        person1_info = cleaner._get_person_info(p1_name, p1_conv)
        person2_info = cleaner._get_person_info(p2_name, p2_conv)

        print(f"🤖 调用LLM判断...")
        print(f"   实体1: {p1_name} ({person1_info['relationships_count']}个关系)")
        print(f"   实体2: {p2_name} ({person2_info['relationships_count']}个关系)")

        decision = cleaner.ask_llm_merge_decision(person1_info, person2_info)

        print(f"\n📊 LLM决策:")
        print(f"   动作: {decision['action']}")
        print(f"   置信度: {decision['confidence']:.2%}")
        print(f"   理由: {decision['reason']}")

        if decision['action'] == 'merge':
            target_name = p1_name if decision.get('target') == 'person1' else p2_name
            source_name = p2_name if target_name == p1_name else p1_name

            if decision['confidence'] >= 0.9:
                cleaner.analysis_results['llm_suggestions'].append({
                    'type': 'merge',
                    'source': [source_name, p1_conv],
                    'target': [target_name, p1_conv],
                    'reason': decision['reason'],
                    'confidence': decision['confidence'],
                    'auto_execute': True
                })
                print(f"   ✅ 建议自动合并: {source_name} → {target_name}")
            else:
                cleaner.analysis_results['needs_review'].append({
                    'type': 'merge',
                    'person1': [p1_name, p1_conv],
                    'person2': [p2_name, p2_conv],
                    'suggestion': decision
                })
                print(f"   ⚠️  需要人工审核（置信度较低）")

    # 生成操作脚本
    print("\n" + "=" * 80)
    print("生成操作脚本...")
    print("=" * 80)

    operations_file = cleaner.generate_operations_script("test_cleanup_operations.json")

    print(f"\n✅ 测试完成！")
    print(f"   操作脚本: {operations_file}")
    print(f"   自动操作: {len(cleaner.analysis_results['auto_actions'])} 个")
    print(f"   LLM建议: {len(cleaner.analysis_results['llm_suggestions'])} 个")
    print(f"   需要审核: {len(cleaner.analysis_results['needs_review'])} 个")
