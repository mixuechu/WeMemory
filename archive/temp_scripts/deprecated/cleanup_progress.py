#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理progress.json - 移除实际已有文件的"失败"记录
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import batch_extract_all as bea

print("=" * 80)
print("清理progress.json中的过期失败记录")
print("=" * 80)

# 加载progress
progress = bea.load_progress()

old_failed_count = len(progress.get('failed_batches', []))
old_failed_number = progress.get('failed', 0)

print(f"\n清理前:")
print(f"  failed计数: {old_failed_number}")
print(f"  failed_batches记录数: {old_failed_count}")

# 检查每个failed batch是否真的没有文件
actually_failed = []
recovered = []

for fb in progress.get('failed_batches', []):
    batch_id = fb.get('batch_id')
    if not batch_id:
        continue

    output_file = bea.OUTPUT_DIR / f"session_{batch_id}.json"
    if output_file.exists():
        # 文件存在，这是个过期的失败记录
        recovered.append(batch_id)
        # 确保在processed_batches中
        if batch_id not in progress['processed_batches']:
            progress['processed_batches'].append(batch_id)
    else:
        # 文件不存在，确实失败了
        actually_failed.append(fb)

# 更新progress
progress['failed_batches'] = actually_failed
progress['failed'] = len(actually_failed)
progress['success'] = len(progress['processed_batches'])

# 保存
bea.save_progress(progress)

print(f"\n清理后:")
print(f"  failed计数: {progress['failed']}")
print(f"  failed_batches记录数: {len(actually_failed)}")
print(f"  已恢复到processed: {len(recovered)}")
print(f"  success计数: {progress['success']:,}")
print(f"  processed_batches总数: {len(progress['processed_batches']):,}")

if len(actually_failed) > 0:
    print(f"\n仍然失败的batch:")
    for fb in actually_failed:
        print(f"  {fb.get('conv_name')} - batch {fb.get('batch_index')}: {fb.get('error', 'Unknown')}")
else:
    print(f"\n🎉 所有batch都已成功提取!")

print("=" * 80)
