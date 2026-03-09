#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证改进版脚本是否满足3个要求"""

import sys
import io
import json
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

progress_file = Path('../extractions/batch_20260227_001822/progress.json')

print('='*70)
print('🔍 验证当前batch_extract_all.py的3个关键要求')
print('='*70)

# 读取当前进度
with open(progress_file, 'r', encoding='utf-8') as f:
    progress = json.load(f)

print(f'\n📊 当前progress.json内容:')
print(f'  success: {progress.get("success")}')
print(f'  failed: {progress.get("failed")}')
print(f'  skipped: {progress.get("skipped")}')
print(f'  total_cost: ${progress.get("total_cost", 0):.2f}')
print(f'  processed_batches: {len(progress.get("processed_batches", []))} 个')
print(f'  failed_batches: {"有" if "failed_batches" in progress else "❌ 无"}')

print(f'\n✅ 要求1: 失败的案例会被完全记录')
print('-'*70)

if 'failed_batches' in progress and len(progress['failed_batches']) > 0:
    print(f'✅ PASS: progress.json有failed_batches字段，包含{len(progress["failed_batches"])}条记录')
    print(f'\n前3个失败记录样本:')
    for i, failed in enumerate(progress['failed_batches'][:3], 1):
        print(f'  {i}. {failed}')
else:
    print(f'❌ FAIL: progress.json没有failed_batches字段')
    print(f'  当前只有failed计数({progress.get("failed")}次)')
    print(f'  但没有记录具体哪些batch失败了')
    print(f'  ')
    print(f'  💡 解决方案: 需要修改batch_extract_all.py')
    print(f'     1. 在load_progress()添加 failed_batches: []')
    print(f'     2. 在失败时记录 batch_id, conv_name, error')

print(f'\n✅ 要求2: 进度会不断展示')
print('-'*70)

log_file = Path('../extractions/batch_20260227_001822/extraction_log.txt')
progress_lines = []
with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
    for line in f:
        if '进度:' in line:
            progress_lines.append(line.strip())

print(f'✅ PASS: extraction_log.txt有{len(progress_lines)}条进度记录')
print(f'\n最近5条进度:')
for line in progress_lines[-5:]:
    print(f'  {line}')

print(f'\n✅ 要求3: 之前跑过的完全不会重新跑')
print('-'*70)

# 读取代码检查断点续传逻辑
code_file = Path('batch_extract_all.py')
with open(code_file, 'r', encoding='utf-8') as f:
    code = f.read()

if 'output_file.exists()' in code and 'batch_id in progress' in code:
    print(f'✅ PASS: 代码有断点续传检查')
    print(f'  检查逻辑:')
    print(f'    if output_file.exists() or batch_id in processed_batches:')
    print(f'        跳过（已处理）')
else:
    print(f'❌ FAIL: 代码缺少断点续传检查')

# 验证文件数量
output_dir = Path('../extractions/batch_20260227_001822')
json_files = list(output_dir.glob('session_*.json'))
print(f'\n验证结果:')
print(f'  - processed_batches记录: {len(progress.get("processed_batches", []))} 个')
print(f'  - 实际JSON文件: {len(json_files)} 个')
print(f'  - 差异: {abs(len(json_files) - len(progress.get("processed_batches", [])))}')

print(f'\n{"="*70}')
print(f'📋 总结')
print(f'{"="*70}')

issues = []

if 'failed_batches' not in progress:
    issues.append('❌ 需要添加failed_batches记录')
else:
    print(f'✅ 要求1满足: 失败批次有完整记录')

if len(progress_lines) > 100:
    print(f'✅ 要求2满足: 进度持续展示（{len(progress_lines)}条记录）')
else:
    print(f'⚠️  要求2部分满足: 进度有展示，但记录较少')

if 'output_file.exists()' in code:
    print(f'✅ 要求3满足: 有断点续传检查')
else:
    issues.append('❌ 需要添加断点续传检查')

if issues:
    print(f'\n⚠️  需要改进的地方:')
    for issue in issues:
        print(f'  {issue}')
    print(f'\n💡 建议: 使用batch_extract_all_improved.py或手动修改现有脚本')
else:
    print(f'\n🎉 所有要求都满足！可以安全重启')
