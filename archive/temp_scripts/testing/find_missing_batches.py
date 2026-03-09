#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
找出所有缺失的batch并直接提取
"""
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 导入batch_extract_all的所有内容
import importlib.util
spec = importlib.util.spec_from_file_location("batch_extract_all", "batch_extract_all.py")
bea = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bea)

import json
from pathlib import Path
import pickle

print('=' * 60)
print('找出所有缺失的batch')
print('=' * 60)

# 1. 生成所有batch
print('\n1. 生成所有应该存在的batch...')
all_conversations = bea.load_all_conversations()

all_batches = []
for conv in all_conversations:
    batches = bea.split_into_batches(conv)
    all_batches.extend(batches)

total_should_exist = len(all_batches)
all_batch_ids = set(b['batch_id'] for b in all_batches)
print(f'   总batch数: {total_should_exist:,}')

# 2. 加载已处理的batch
print('\n2. 加载已处理的batch...')
progress_file = Path('../extractions/batch_20260227_001822/progress.json')
with open(progress_file, 'r', encoding='utf-8') as f:
    progress = json.load(f)

processed_ids = set(progress['processed_batches'])
print(f'   已处理: {len(processed_ids):,}')

# 3. 找出缺失的batch
print('\n3. 找出缺失的batch...')
missing_ids = all_batch_ids - processed_ids
print(f'   缺失: {len(missing_ids):,}')

# 4. 创建缺失batch列表
missing_batches = [b for b in all_batches if b['batch_id'] in missing_ids]

print(f'\n4. 按对话统计缺失batch（TOP 20）:')
from collections import defaultdict
conv_missing = defaultdict(int)
for b in missing_batches:
    conv_missing[b['conversation_name']] += 1

for name, count in sorted(conv_missing.items(), key=lambda x: x[1], reverse=True)[:20]:
    print(f'   {name}: {count} batches')

# 5. 保存
with open('missing_batches.pkl', 'wb') as f:
    pickle.dump(missing_batches, f)

print(f'\n5. 已保存到: missing_batches.pkl')
print(f'   预估成本: ${len(missing_batches) * 0.0001:.2f}')
print(f'   预估时间: ~{len(missing_batches) * 2 / 50 / 60:.1f} 分钟 (50 workers)')
print()
print('=' * 60)
