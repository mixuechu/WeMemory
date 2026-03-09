#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用LLM增强事件描述（关系三元组保持规则版本）
"""

import json
import os
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 加载.env
env_file = Path(__file__).parent.parent / '.env'
load_dotenv(env_file)

from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel

# 初始化Gemini
PROJECT_ID = os.getenv('VITE_GOOGLE_CLOUD_PROJECT')
LOCATION = os.getenv('VITE_GOOGLE_CLOUD_LOCATION', 'us-central1')
CREDENTIALS_JSON = os.getenv('VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON')

creds_dict = json.loads(CREDENTIALS_JSON)
credentials = service_account.Credentials.from_service_account_info(creds_dict)
vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

MODEL_NAME = "gemini-2.5-flash"
model = GenerativeModel(MODEL_NAME)

import sys

print("=" * 80)
print("用LLM增强事件描述")
print("=" * 80)
print(f"\n✓ Gemini模型: {MODEL_NAME}")
sys.stdout.flush()  # 强制输出

def enhance_event(record):
    """用LLM增强事件描述"""

    metadata = record['metadata']
    event_name = metadata.get('event_name', '')
    time_desc = metadata.get('time_description', '')
    participants = metadata.get('participants', [])
    original_text = record['text']

    prompt = f"""将以下事件信息转换为一句自然、流畅的中文描述。

事件信息：
- 时间：{time_desc if time_desc else "未指定"}
- 参与者：{', '.join(participants) if participants else "未指定"}
- 原始描述：{original_text}

要求：
1. 生成一句话描述，简洁自然
2. 如果有明确时间，放在句首
3. 避免参与者名字重复
4. 保持事实准确，不添加细节
5. 语言流畅，符合口语表达

只输出这一句话，不要其他内容。
"""

    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 8192,
                }
            )

            enhanced_text = response.text.strip()

            # 去掉可能的引号
            if enhanced_text.startswith('"') and enhanced_text.endswith('"'):
                enhanced_text = enhanced_text[1:-1]
            if enhanced_text.startswith('"') and enhanced_text.endswith('"'):
                enhanced_text = enhanced_text[1:-1]

            return enhanced_text

        except Exception as e:
            error_msg = str(e)
            if '429' in error_msg and attempt < max_retries - 1:
                print(f"    配额超限，等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                print(f"    ✗ 增强失败: {error_msg[:50]}")
                return record['text']

    return record['text']

# 加载数据
print("\n正在加载数据...")
with open('natural_language_triplets.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

records = data['records']
event_records = [r for r in records if r['type'] == 'event']

# 测试模式：只处理前10条
TEST_MODE = False  # 改为False运行完整版本
if TEST_MODE:
    event_records = event_records[:10]
    print(f"\n测试模式：只处理前 {len(event_records)} 个事件")
else:
    print(f"\n找到 {len(event_records)} 个事件描述需要增强")
print(f"预计耗时: {len(event_records) * 2 / 60 / 60:.1f} 小时")
print(f"预计成本: ~${len(event_records) * 0.0005:.2f} USD")

# 自动开始（用户已确认）
print("\n关系三元组将保持规则版本不变")
print("开始处理...")

# 开始增强
print("\n开始增强事件描述...\n")
enhanced_count = 0
failed_count = 0

start_time = datetime.now()

for i, record in enumerate(event_records):
    print(f"[{i+1}/{len(event_records)}] {record['id']}")
    print(f"  原文: {record['text'][:80]}...")

    # 增强
    enhanced_text = enhance_event(record)

    # 更新
    if enhanced_text != record['text']:
        record['original_text'] = record['text']  # 保存原文
        record['text'] = enhanced_text
        record['llm_enhanced'] = True
        enhanced_count += 1
        print(f"  增强: {enhanced_text[:80]}...")
    else:
        failed_count += 1
        print(f"  保持原样（增强失败或无变化）")

    # 每100条保存一次进度
    if (i + 1) % 100 == 0:
        temp_output = f'natural_language_triplets_enhanced_temp.json'
        with open(temp_output, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        elapsed = (datetime.now() - start_time).total_seconds()
        remaining = (len(event_records) - i - 1) * (elapsed / (i + 1))
        print(f"\n  >>> 进度保存 ({i+1}/{len(event_records)}) <<<")
        print(f"  >>> 预计剩余时间: {remaining / 60:.1f} 分钟 <<<\n")

    # 速率限制
    time.sleep(2)

# 更新元数据
data['metadata']['llm_enhanced'] = True
data['metadata']['enhancement_stats'] = {
    'enhanced_events': enhanced_count,
    'failed_events': failed_count,
    'total_events': len(event_records),
    'model': MODEL_NAME,
    'enhanced_at': datetime.now().isoformat()
}

# 保存最终结果
output_file = 'natural_language_triplets_enhanced.json'
print(f"\n保存到 {output_file}...")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# 统计
total_time = (datetime.now() - start_time).total_seconds()
file_size = os.path.getsize(output_file) / (1024 * 1024)

print("\n" + "=" * 80)
print("✅ 增强完成！")
print("=" * 80)
print(f"\n增强统计:")
print(f"  成功增强: {enhanced_count}/{len(event_records)} ({enhanced_count/len(event_records)*100:.1f}%)")
print(f"  增强失败: {failed_count}")
print(f"  总耗时: {total_time / 60:.1f} 分钟")
print(f"  平均速度: {total_time / len(event_records):.1f} 秒/条")

print(f"\n文件信息:")
print(f"  输出文件: {output_file}")
print(f"  文件大小: {file_size:.2f} MB")

print(f"\n数据组成:")
print(f"  关系三元组: {len([r for r in records if r['type'] == 'relationship'])} 条 (规则版本)")
print(f"  事件描述: {len(event_records)} 条 (LLM增强版)")
print(f"  总记录数: {len(records)} 条")

print("\n示例对比（前5个事件）:")
for record in event_records[:5]:
    if 'original_text' in record:
        print(f"\n原文: {record['original_text'][:80]}")
        print(f"增强: {record['text'][:80]}")

print("\n" + "=" * 80)
