#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取真正缺失的batch
"""
import sys
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# 添加当前目录到path
sys.path.insert(0, str(Path(__file__).parent))

# 导入batch_extract_all
import batch_extract_all as bea

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

log("=" * 80)
log("提取缺失的batch")
log("=" * 80)

# 1. 加载所有对话并生成所有batch
log("\n加载对话并生成所有batch...")
convs = bea.load_all_conversations()

all_batches = []
for conv in convs:
    batches = bea.split_into_batches(conv)
    all_batches.extend(batches)

all_batch_ids = set(b['batch_id'] for b in all_batches)
log(f"总batch数: {len(all_batches):,}")

# 2. 加载进度
progress = bea.load_progress()
processed_ids = set(progress['processed_batches'])
log(f"已处理: {len(processed_ids):,}")

# 3. 找出缺失的batch
missing_ids = all_batch_ids - processed_ids
missing_batches = [b for b in all_batches if b['batch_id'] in missing_ids]
log(f"缺失: {len(missing_batches):,}")

if len(missing_batches) == 0:
    log("\n没有缺失的batch!")
    sys.exit(0)

# 4. 显示top对话
log(f"\n缺失batch最多的对话 (TOP 10):")
from collections import defaultdict
conv_missing = defaultdict(int)
for b in missing_batches:
    conv_missing[b['conversation_name']] += 1

for name, count in sorted(conv_missing.items(), key=lambda x: x[1], reverse=True)[:10]:
    log(f"  {name}: {count} batches")

# 5. 开始提取
log(f"\n开始提取 (并行度: 50)...")
log("=" * 80 + "\n")

success_count = 0
failed_count = 0
start_time = time.time()

with ThreadPoolExecutor(max_workers=50) as executor:
    futures = {
        executor.submit(bea.process_batch, batch, progress): batch
        for batch in missing_batches
    }

    for future in as_completed(futures):
        result = future.result()

        if result['status'] == 'success':
            success_count += 1
            progress['success'] += 1
            progress['total_cost'] += result.get('cost', 0)
            progress['processed_batches'].append(result['batch_id'])

            # 从failed中移除
            if result['batch_id'] in [fb.get('batch_id') for fb in progress.get('failed_batches', [])]:
                progress['failed_batches'] = [
                    fb for fb in progress['failed_batches']
                    if fb['batch_id'] != result['batch_id']
                ]
                progress['failed'] = max(0, progress['failed'] - 1)

        elif result['status'] == 'failed':
            failed_count += 1
            progress['failed'] += 1

            # 添加到failed_batches
            if result['batch_id'] not in [fb.get('batch_id') for fb in progress.get('failed_batches', [])]:
                progress['failed_batches'].append({
                    'batch_id': result['batch_id'],
                    'conv_name': result.get('conv_name'),
                    'batch_index': result.get('batch_index'),
                    'error': result.get('error', 'Unknown error')
                })

        # 每10个保存一次
        completed = success_count + failed_count
        if completed % 50 == 0:
            bea.save_progress(progress)
            elapsed = time.time() - start_time
            rate = completed / elapsed if elapsed > 0 else 0
            remaining = len(missing_batches) - completed
            eta_sec = remaining / rate if rate > 0 else 0
            log(f"进度: {completed}/{len(missing_batches)} | 成功: {success_count} | 失败: {failed_count} | {rate:.1f} batch/s | ETA: {eta_sec/60:.1f}分")

# 最终保存
bea.save_progress(progress)

elapsed = time.time() - start_time
log(f"\n" + "=" * 80)
log(f"提取完成！")
log(f"  成功: {success_count}")
log(f"  失败: {failed_count}")
log(f"  耗时: {elapsed/60:.1f}分")
log(f"  新增成本: ${success_count * 0.0001:.4f}")
log(f"  速率: {success_count/elapsed:.1f} batch/s")
log("=" * 80)
