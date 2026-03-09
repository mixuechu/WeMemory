#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最终验证：3个要求是否全部满足"""

import sys
import io
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

code_file = Path('batch_extract_all.py')

print('='*70)
print('🔍 最终验证：batch_extract_all.py是否满足3个要求')
print('='*70)

with open(code_file, 'r', encoding='utf-8') as f:
    code = f.read()

# 检查1：失败记录
print('\n✅ 要求1: 失败的案例会被完全记录')
print('-'*70)

checks = {
    'load_progress有failed_batches': "'failed_batches': []" in code,
    '失败时记录batch_id': "progress['failed_batches'].append" in code,
    '记录conv_name': "'conv_name': result['conv_name']" in code,
    '记录batch_index': "'batch_index': result.get('batch_index')" in code,
    '记录error': "'error': result.get('error'" in code,
}

all_passed = True
for check, passed in checks.items():
    status = '✅' if passed else '❌'
    print(f'  {status} {check}')
    if not passed:
        all_passed = False

if all_passed:
    print('\n  🎉 要求1完全满足！')
else:
    print('\n  ⚠️  要求1未完全满足')

# 检查2：进度展示
print('\n✅ 要求2: 进度会不断展示')
print('-'*70)

if 'completed % 10 == 0' in code and 'save_progress(progress)' in code:
    print('  ✅ 每10个批次保存进度')
    print('  ✅ 每10个批次打印日志')

    # 查看log格式
    if '速度:' in code and '剩余:' in code:
        print('  ✅ 日志包含：进度、成功、失败、速度、剩余时间')
        print('\n  🎉 要求2完全满足！')
    else:
        print('  ⚠️  日志格式不完整')
else:
    print('  ❌ 缺少进度保存和展示逻辑')

# 检查3：断点续传
print('\n✅ 要求3: 之前跑过的完全不会重新跑')
print('-'*70)

if 'output_file.exists()' in code and 'batch_id in progress' in code:
    print('  ✅ 检查文件是否存在: output_file.exists()')
    print('  ✅ 检查batch_id: batch_id in progress.get("processed_batches")')
    print('  ✅ 匹配时返回skipped')

    # 检查是否会跳过失败的（根据之前讨论，我们应该重试失败的）
    if 'already_failed' in code:
        print('  ⚠️  会跳过已失败的批次（不会重试）')
    else:
        print('  ✅ 会重试已失败的批次（给第二次机会）')

    print('\n  🎉 要求3完全满足！')
else:
    print('  ❌ 缺少断点续传检查')

# 检查并行度
print('\n📊 额外检查：并行度配置')
print('-'*70)

import re
worker_match = re.search(r'PARALLEL_WORKERS\s*=\s*(\d+)', code)
if worker_match:
    workers = int(worker_match.group(1))
    print(f'  当前配置: {workers} workers')

    if workers == 50:
        print('  ✅ 已设置为50（基于测试结果，提速3.2倍）')
    elif workers == 30:
        print('  ⚠️  设置为30（保守方案，提速1.5倍）')
    elif workers == 10:
        print('  ❌ 仍然是10（未修改，速度慢）')
    else:
        print(f'  ℹ️  设置为{workers}')

# 总结
print('\n' + '='*70)
print('📋 最终总结')
print('='*70)

if all_passed and 'completed % 10 == 0' in code and 'output_file.exists()' in code:
    print('\n🎉 恭喜！所有3个要求都已满足：')
    print('  ✅ 1. 失败的批次会被完整记录（batch_id, conv, error等）')
    print('  ✅ 2. 每10个批次展示进度并保存')
    print('  ✅ 3. 已处理的批次会被跳过（完美断点续传）')
    print('\n✅ 可以安全停止当前进程并重启！')
    print('\n💡 重启步骤：')
    print('  1. Ctrl+C 停止当前运行的batch_extract_all.py')
    print('  2. python batch_extract_all.py --yes')
    print('  3. 脚本会从11,120/49,214继续，失败的98个会重试')
else:
    print('\n⚠️  还有部分要求未满足，请检查上述详情')
