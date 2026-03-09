#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终全面验证 - 确保所有对话的所有记录都已抽取
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import batch_extract_all as bea

print("=" * 80)
print("最终全面验证")
print("=" * 80)

# 1. 检查源对话文件
source_dir = Path('D:/导出聊天记录excel/chat_data_filtered')
source_files = list(source_dir.glob('*.json'))
print(f"\n1️⃣ 源对话文件:")
print(f"   目录: {source_dir}")
print(f"   文件数: {len(source_files)}")

# 2. 加载所有对话
print(f"\n2️⃣ 加载对话:")
all_conversations = bea.load_all_conversations()
print(f"   成功加载: {len(all_conversations)} 个对话")

# 3. 生成所有应该存在的batch
print(f"\n3️⃣ 分析应生成的batch:")
all_batches = []
conv_batch_count = {}

for conv in all_conversations:
    batches = bea.split_into_batches(conv)
    all_batches.extend(batches)
    conv_name = conv.get('name', 'Unknown')
    conv_batch_count[conv_name] = len(batches)

all_batch_ids = set(b['batch_id'] for b in all_batches)
print(f"   应生成batch总数: {len(all_batch_ids):,}")

# 显示batch数最多的对话
print(f"\n   batch数最多的对话 (TOP 10):")
sorted_convs = sorted(conv_batch_count.items(), key=lambda x: x[1], reverse=True)
for name, count in sorted_convs[:10]:
    print(f"   - {name}: {count} batches")

# 4. 检查磁盘上的提取文件
print(f"\n4️⃣ 检查磁盘上的提取文件:")
output_dir = bea.OUTPUT_DIR
json_files = list(output_dir.rglob("*.json"))
# 排除progress.json
json_files = [f for f in json_files if f.name != 'progress.json']
print(f"   输出目录: {output_dir}")
print(f"   JSON文件数: {len(json_files):,}")

# 提取文件的batch_id
file_batch_ids = set(f.stem.replace('session_', '') for f in json_files)
print(f"   唯一batch_id数: {len(file_batch_ids):,}")

# 5. 检查progress.json
print(f"\n5️⃣ 检查progress.json记录:")
progress = bea.load_progress()
processed_ids = set(progress.get('processed_batches', []))
print(f"   processed_batches: {len(processed_ids):,}")
print(f"   success计数: {progress.get('success', 0):,}")
print(f"   failed计数: {progress.get('failed', 0)}")
print(f"   总成本: ${progress.get('total_cost', 0):.4f}")

# 6. 交叉验证
print(f"\n6️⃣ 交叉验证:")

# 6.1 应存在 vs 磁盘文件
missing_files = all_batch_ids - file_batch_ids
extra_files = file_batch_ids - all_batch_ids
print(f"\n   应存在但文件缺失: {len(missing_files):,}")
if missing_files and len(missing_files) <= 10:
    for bid in list(missing_files)[:10]:
        # 找到对应的batch
        for b in all_batches:
            if b['batch_id'] == bid:
                print(f"   - {b['conversation_name']} batch {b['batch_index']}")
                break

print(f"   文件存在但不应存在: {len(extra_files):,}")
if extra_files and len(extra_files) <= 10:
    for bid in list(extra_files)[:10]:
        print(f"   - {bid}")

# 6.2 磁盘文件 vs progress记录
missing_in_progress = file_batch_ids - processed_ids
missing_files_in_progress = processed_ids - file_batch_ids
print(f"\n   文件存在但未记录在progress: {len(missing_in_progress):,}")
print(f"   progress记录但文件不存在: {len(missing_files_in_progress):,}")

# 6.3 应存在 vs progress记录
not_processed = all_batch_ids - processed_ids
over_processed = processed_ids - all_batch_ids
print(f"\n   应存在但未在progress中: {len(not_processed):,}")
print(f"   progress中但不应存在: {len(over_processed):,}")

# 7. 计算覆盖率
print(f"\n7️⃣ 覆盖率统计:")
coverage_disk = len(all_batch_ids & file_batch_ids) / len(all_batch_ids) * 100
coverage_progress = len(all_batch_ids & processed_ids) / len(all_batch_ids) * 100
print(f"   磁盘文件覆盖率: {coverage_disk:.2f}%")
print(f"   progress记录覆盖率: {coverage_progress:.2f}%")

# 8. 按对话统计覆盖率
print(f"\n8️⃣ 按对话统计未完成的:")
incomplete_convs = []
for conv in all_conversations:
    conv_name = conv.get('name', 'Unknown')
    batches = bea.split_into_batches(conv)
    conv_batch_ids = set(b['batch_id'] for b in batches)

    # 检查有多少batch已经有文件
    completed = len(conv_batch_ids & file_batch_ids)
    total = len(conv_batch_ids)

    if completed < total:
        incomplete_convs.append({
            'name': conv_name,
            'completed': completed,
            'total': total,
            'missing': total - completed
        })

if incomplete_convs:
    print(f"   未完全提取的对话数: {len(incomplete_convs)}")
    print(f"\n   TOP 10 未完成对话:")
    for conv in sorted(incomplete_convs, key=lambda x: x['missing'], reverse=True)[:10]:
        pct = conv['completed'] / conv['total'] * 100
        print(f"   - {conv['name']}: {conv['completed']}/{conv['total']} ({pct:.1f}%) 缺失:{conv['missing']}")
else:
    print(f"   ✅ 所有对话都已完全提取!")

# 9. 最终结论
print(f"\n" + "=" * 80)
print(f"最终结论:")
print(f"=" * 80)

if len(missing_files) == 0 and len(not_processed) == 0:
    print(f"✅ 所有 {len(all_conversations)} 个对话的所有 {len(all_batch_ids):,} 个batch都已完成抽取!")
    print(f"✅ 磁盘文件: {len(json_files):,}")
    print(f"✅ 覆盖率: 100.00%")
    print(f"✅ 成本: ${progress.get('total_cost', 0):.4f}")
else:
    print(f"⚠️ 发现问题:")
    if missing_files:
        print(f"   - {len(missing_files)} 个batch缺少文件")
    if not_processed:
        print(f"   - {len(not_processed)} 个batch未记录在progress中")
    print(f"\n当前完成度: {coverage_disk:.2f}%")

print("=" * 80)
