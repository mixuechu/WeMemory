#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重试真正失败的batch (那些没有JSON文件的)
"""
import sys
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
import batch_extract_all as bea

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

log("=" * 80)
log("重试真正失败的batch")
log("=" * 80)

# 1. 加载progress
progress = bea.load_progress()
failed_batches_info = progress.get('failed_batches', [])

log(f"\nfailed_batches记录数: {len(failed_batches_info)}")

# 2. 检查哪些确实没有文件
actually_failed = []
for fb in failed_batches_info:
    batch_id = fb.get('batch_id')
    if not batch_id:
        continue

    output_file = bea.OUTPUT_DIR / f"session_{batch_id}.json"
    if not output_file.exists():
        actually_failed.append(fb)

log(f"确实没有文件的: {len(actually_failed)}")

if len(actually_failed) == 0:
    log("\n没有需要重试的batch!")
    sys.exit(0)

# 3. 从所有对话中找到这些batch
log("\n加载对话并查找失败batch...")
all_conversations = bea.load_all_conversations()

failed_batch_ids = set(fb['batch_id'] for fb in actually_failed)
batches_to_retry = []

for conv in all_conversations:
    batches = bea.split_into_batches(conv)
    for batch in batches:
        if batch['batch_id'] in failed_batch_ids:
            batches_to_retry.append(batch)

log(f"找到 {len(batches_to_retry)} 个batch可以重试")

if len(batches_to_retry) == 0:
    log("\n警告: failed_batches中的batch_id在当前对话中找不到!")
    log("这可能是因为对话内容已更改，batch_id已不同")
    sys.exit(1)

# 4. 显示失败原因统计
from collections import Counter
error_types = Counter()
for fb in actually_failed:
    error = fb.get('error', 'Unknown')
    # 提取错误类型
    if 'JSON' in error or 'json' in error or 'format' in error:
        error_types['JSON格式错误'] += 1
    elif 'network' in error.lower() or 'timeout' in error.lower():
        error_types['网络错误'] += 1
    elif 'rate' in error.lower() or 'quota' in error.lower():
        error_types['限流错误'] += 1
    else:
        error_types['其他错误'] += 1

log(f"\n失败原因统计:")
for error_type, count in error_types.most_common():
    log(f"  {error_type}: {count}")

# 5. 开始重试
log(f"\n开始重试 (并行度: 10, 降低并发避免限流)...")
log("=" * 80 + "\n")

success_count = 0
still_failed_count = 0
start_time = time.time()

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {
        executor.submit(bea.process_batch, batch, progress): batch
        for batch in batches_to_retry
    }

    for future in as_completed(futures):
        result = future.result()

        if result['status'] == 'success':
            success_count += 1
            progress['success'] += 1
            progress['total_cost'] += result.get('cost', 0)

            # 添加到processed_batches
            if result['batch_id'] not in progress['processed_batches']:
                progress['processed_batches'].append(result['batch_id'])

            # 从failed中移除
            progress['failed_batches'] = [
                fb for fb in progress['failed_batches']
                if fb['batch_id'] != result['batch_id']
            ]
            progress['failed'] = len(progress['failed_batches'])

        elif result['status'] == 'failed':
            still_failed_count += 1
            log(f"  仍失败: {result.get('conv_name')} batch {result.get('batch_index')} - {result.get('error', 'Unknown')}")

        # 每10个保存一次
        completed = success_count + still_failed_count
        if completed % 10 == 0:
            bea.save_progress(progress)
            elapsed = time.time() - start_time
            rate = completed / elapsed if elapsed > 0 else 0
            log(f"进度: {completed}/{len(batches_to_retry)} | 成功: {success_count} | 仍失败: {still_failed_count} | {rate:.1f}/s")

# 最终保存
bea.save_progress(progress)

elapsed = time.time() - start_time
log(f"\n" + "=" * 80)
log(f"重试完成！")
log(f"  成功: {success_count}")
log(f"  仍失败: {still_failed_count}")
log(f"  耗时: {elapsed:.1f}秒")
log(f"  新增成本: ${success_count * 0.0001:.4f}")
log(f"  当前failed总数: {progress['failed']}")
log("=" * 80)
