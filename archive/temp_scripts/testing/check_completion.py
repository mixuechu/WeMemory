#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查完成情况 - 无stdout问题版本
"""
import sys
from pathlib import Path

# 添加当前目录到path
sys.path.insert(0, str(Path(__file__).parent))

# 导入batch_extract_all
import batch_extract_all as bea

# 1. 加载所有对话
convs = bea.load_all_conversations()

# 2. 生成所有batch
all_batches = []
for conv in convs:
    batches = bea.split_into_batches(conv)
    all_batches.extend(batches)

total_should_exist = len(all_batches)
all_batch_ids = set(b['batch_id'] for b in all_batches)

# 3. 加载progress
progress = bea.load_progress()
processed_ids = set(progress['processed_batches'])

# 4. 找出缺失的
missing_ids = all_batch_ids - processed_ids

print(f"应存在batch总数: {total_should_exist:,}")
print(f"已处理: {len(processed_ids):,}")
print(f"缺失: {len(missing_ids):,}")
print(f"")
print(f"成功: {progress['success']:,}")
print(f"失败: {progress['failed']}")
print(f"失败详情记录数: {len(progress['failed_batches'])}")
