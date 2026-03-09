#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重试所有失败的batch
"""
import sys
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import time

# 导入batch_extract_all的功能
import importlib.util
spec = importlib.util.spec_from_file_location("batch_extract_all", "batch_extract_all.py")
bea = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bea)

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

log("=" * 80)
log("重试失败的batch")
log("=" * 80)

# 1. 加载失败的batch信息
progress_file = Path('../extractions/batch_20260227_001822/progress.json')
with open(progress_file, 'r', encoding='utf-8') as f:
    progress = json.load(f)

failed_batches_info = progress.get('failed_batches', [])
failed_batch_ids = set(fb['batch_id'] for fb in failed_batches_info)

log(f"\n失败batch数: {len(failed_batch_ids)}")

# 2. 从所有对话中找到这些失败的batch
log("\n加载对话并查找失败的batch...")
all_conversations = bea.load_all_conversations()

failed_batches_to_retry = []
for conv in all_conversations:
    batches = bea.split_into_batches(conv)
    for batch in batches:
        if batch['batch_id'] in failed_batch_ids:
            failed_batches_to_retry.append(batch)

log(f"找到 {len(failed_batches_to_retry)} 个失败batch可以重试")

if len(failed_batches_to_retry) == 0:
    log("\n没有需要重试的batch")
    sys.exit(0)

# 3. 重试
log(f"\n开始重试 (并行度: 10)...")
log("=" * 80 + "\n")

success_count = 0
still_failed_count = 0
start_time = time.time()

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {
        executor.submit(bea.process_batch, batch, progress): batch
        for batch in failed_batches_to_retry
    }

    for future in as_completed(futures):
        result = future.result()

        if result['status'] == 'success':
            success_count += 1
            progress['success'] += 1
            progress['failed'] -= 1
            progress['total_cost'] += result.get('cost', 0)
            progress['processed_batches'].append(result['batch_id'])

            # 从failed_batches中移除
            progress['failed_batches'] = [
                fb for fb in progress['failed_batches']
                if fb['batch_id'] != result['batch_id']
            ]

        elif result['status'] == 'failed':
            still_failed_count += 1
            log(f"  ❌ 仍然失败: {result.get('conv_name')} batch {result.get('batch_index')}")

        # 每10个保存一次
        completed = success_count + still_failed_count
        if completed % 10 == 0:
            bea.save_progress(progress)
            log(f"进度: {completed}/{len(failed_batches_to_retry)} | 成功: {success_count} | 仍失败: {still_failed_count}")

# 最终保存
bea.save_progress(progress)

elapsed = time.time() - start_time
log(f"\n" + "=" * 80)
log(f"重试完成！")
log(f"  成功: {success_count}")
log(f"  仍失败: {still_failed_count}")
log(f"  耗时: {elapsed:.1f}秒")
log(f"  新增成本: ${success_count * 0.0001:.4f}")
log("=" * 80)
