#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细检查完成情况
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import batch_extract_all as bea

# 1. 加载所有对话
convs = bea.load_all_conversations()

# 2. 生成所有batch
all_batches = []
for conv in convs:
    batches = bea.split_into_batches(conv)
    all_batches.extend(batches)

all_batch_ids = set(b['batch_id'] for b in all_batches)

# 3. 加载progress
progress = bea.load_progress()
processed_ids = set(progress['processed_batches'])

# 4. 详细比较
print(f"应存在batch总数: {len(all_batch_ids):,}")
print(f"已处理batch数: {len(processed_ids):,}")

# 找出真正缺失的
missing = all_batch_ids - processed_ids
print(f"应存在但未处理: {len(missing):,}")

# 找出多余的
extra = processed_ids - all_batch_ids
print(f"已处理但不应存在: {len(extra):,}")

# 覆盖率
coverage = len(all_batch_ids & processed_ids) / len(all_batch_ids) * 100
print(f"覆盖率: {coverage:.2f}%")

if missing:
    print(f"\n缺失batch的前10个ID:")
    for bid in list(missing)[:10]:
        print(f"  {bid}")

if extra:
    print(f"\n多余batch的前10个ID:")
    for bid in list(extra)[:10]:
        print(f"  {bid}")
