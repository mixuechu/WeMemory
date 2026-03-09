#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简化测试批量LLM"""

import sys
import io

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("开始测试...")

try:
    from intelligent_graph_cleaner_batch import IntelligentGraphCleanerBatch

    print("✅ 模块导入成功")

    with IntelligentGraphCleanerBatch() as cleaner:
        print("✅ 清理器初始化成功")

        # 只分析重复实体
        print("\n开始分析重复实体...")
        cleaner.analyze_duplicates(similarity_threshold=0.85, auto_merge_exact=True)

        print("\n✅ 分析完成")
        print(f"自动操作: {len(cleaner.analysis_results['auto_actions'])}")
        print(f"LLM建议: {len(cleaner.analysis_results['llm_suggestions'])}")
        print(f"需要审核: {len(cleaner.analysis_results['needs_review'])}")

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
