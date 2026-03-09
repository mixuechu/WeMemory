#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从磁盘上的JSON文件重建progress.json
"""
import sys
from pathlib import Path
import json

# 添加当前目录到path
sys.path.insert(0, str(Path(__file__).parent))

# 导入batch_extract_all
import batch_extract_all as bea

print("=" * 80)
print("从磁盘文件重建progress.json")
print("=" * 80)

# 1. 扫描所有JSON文件
output_dir = bea.OUTPUT_DIR
json_files = list(output_dir.rglob("*.json"))
print(f"\n磁盘上的JSON文件: {len(json_files):,}")

# 2. 提取batch_id
batch_ids_on_disk = set()
for json_file in json_files:
    # batch_id 是文件名(不含.json)
    batch_id = json_file.stem
    batch_ids_on_disk.add(batch_id)

print(f"唯一batch_id数: {len(batch_ids_on_disk):,}")

# 3. 加载当前progress
progress = bea.load_progress()
old_processed_count = len(progress.get('processed_batches', []))
old_success = progress.get('success', 0)
old_failed = progress.get('failed', 0)

print(f"\n当前progress.json状态:")
print(f"  processed_batches: {old_processed_count:,}")
print(f"  success: {old_success:,}")
print(f"  failed: {old_failed}")

# 4. 重建processed_batches
progress['processed_batches'] = list(batch_ids_on_disk)
progress['success'] = len(batch_ids_on_disk)

# 5. 清理failed相关
# 检查哪些failed_batches实际上已经有文件了
if 'failed_batches' in progress:
    old_failed_count = len(progress['failed_batches'])
    actually_failed = []
    for fb in progress['failed_batches']:
        if fb.get('batch_id') not in batch_ids_on_disk:
            actually_failed.append(fb)

    progress['failed_batches'] = actually_failed
    progress['failed'] = len(actually_failed)

    print(f"\n清理failed记录:")
    print(f"  原failed_batches: {old_failed_count}")
    print(f"  实际仍失败: {len(actually_failed)}")
    print(f"  已在磁盘: {old_failed_count - len(actually_failed)}")

# 6. 保存
bea.save_progress(progress)

print(f"\n新的progress.json状态:")
print(f"  processed_batches: {len(progress['processed_batches']):,}")
print(f"  success: {progress['success']:,}")
print(f"  failed: {progress['failed']}")

print(f"\n" + "=" * 80)
print(f"重建完成!")
print(f"  新增记录: {len(batch_ids_on_disk) - old_processed_count:,}")
print("=" * 80)
