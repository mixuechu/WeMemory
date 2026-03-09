#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐步测试批量清理器"""

import sys
import io

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("步骤1: 测试导入...")

try:
    from graph_manager import GraphManager
    print("✅ GraphManager导入成功")
except Exception as e:
    print(f"❌ GraphManager导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    print("✅ Vertexai导入成功")
except Exception as e:
    print(f"❌ Vertexai导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n步骤2: 测试GraphManager连接...")
try:
    gm = GraphManager()
    print("✅ GraphManager连接成功")

    # 获取重复实体
    print("\n步骤3: 查找重复实体...")
    duplicates = gm.find_duplicate_persons(0.85)
    print(f"✅ 找到 {len(duplicates)} 对重复实体")

    # 分类
    case_diff = [d for d in duplicates if d['person1'][0].lower() == d['person2'][0].lower()]
    similar = [d for d in duplicates if d['person1'][0].lower() != d['person2'][0].lower()]

    print(f"  大小写不同: {len(case_diff)} 对")
    print(f"  名字相似: {len(similar)} 对")

    gm.close()
    print("\n✅ 所有测试通过")

except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
