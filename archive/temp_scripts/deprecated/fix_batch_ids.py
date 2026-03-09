#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复progress.json中的batch_id格式 - 移除session_前缀
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import batch_extract_all as bea

print("=" * 80)
print("修复progress.json中的batch_id格式")
print("=" * 80)

# 加载progress
progress = bea.load_progress()

# 统计
old_format_count = 0
new_format_count = 0
fixed_ids = []

for batch_id in progress.get('processed_batches', []):
    if batch_id.startswith('session_'):
        old_format_count += 1
        # 移除session_前缀
        fixed_id = batch_id.replace('session_', '', 1)
        fixed_ids.append(fixed_id)
    else:
        new_format_count += 1
        fixed_ids.append(batch_id)

print(f"\n当前processed_batches:")
print(f"  总数: {len(progress['processed_batches']):,}")
print(f"  旧格式(session_前缀): {old_format_count:,}")
print(f"  新格式(无前缀): {new_format_count:,}")

# 修复failed_batches
failed_fixed = []
for fb in progress.get('failed_batches', []):
    if 'batch_id' in fb and fb['batch_id'].startswith('session_'):
        fb['batch_id'] = fb['batch_id'].replace('session_', '', 1)
    failed_fixed.append(fb)

# 更新progress
progress['processed_batches'] = fixed_ids
progress['failed_batches'] = failed_fixed

# 保存
bea.save_progress(progress)

print(f"\n修复后:")
print(f"  总数: {len(fixed_ids):,}")
print(f"  全部使用新格式(无session_前缀)")
print("=" * 80)
