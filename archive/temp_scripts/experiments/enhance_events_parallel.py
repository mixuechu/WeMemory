#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并行版本：20个worker同时处理
"""

import json
import os
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

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

print("=" * 80)
print("并行版本：20个worker同时增强事件")
print("=" * 80)
print(f"\n✓ Gemini模型: {MODEL_NAME}")
sys.stdout.flush()

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

    max_retries = 2
    retry_delay = 1

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

            return record['id'], enhanced_text, None

        except Exception as e:
            error_msg = str(e)
            if '429' in error_msg and attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                return record['id'], None, str(e)[:100]

    return record['id'], None, "重试失败"

# 加载数据
print("\n正在加载数据...")
with open('natural_language_triplets.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

records = data['records']
event_records = [r for r in records if r['type'] == 'event']

print(f"找到 {len(event_records)} 个事件描述需要增强")
print(f"使用 20 个并行worker")
print(f"预计耗时: {len(event_records) / 20 / 60 * 1.5:.1f} 分钟（理论值）")
sys.stdout.flush()

# 并行处理
print("\n开始并行增强...\n")
sys.stdout.flush()

start_time = datetime.now()
enhanced_count = 0
failed_count = 0

# 创建索引字典
record_dict = {r['id']: r for r in event_records}

with ThreadPoolExecutor(max_workers=20) as executor:
    # 提交所有任务
    future_to_record = {executor.submit(enhance_event, record): record for record in event_records}

    # 处理完成的任务
    for i, future in enumerate(as_completed(future_to_record)):
        record_id, enhanced_text, error = future.result()

        if enhanced_text:
            # 更新记录
            record = record_dict[record_id]
            record['original_text'] = record['text']
            record['text'] = enhanced_text
            record['llm_enhanced'] = True
            enhanced_count += 1
        else:
            failed_count += 1

        # 每100条输出进度
        if (i + 1) % 100 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            speed = (i + 1) / elapsed
            remaining = (len(event_records) - i - 1) / speed if speed > 0 else 0

            print(f"[{i+1}/{len(event_records)}] 成功:{enhanced_count} 失败:{failed_count} "
                  f"速度:{speed:.1f}条/秒 剩余:{remaining/60:.1f}分钟")
            sys.stdout.flush()

            # 保存临时文件
            temp_output = 'natural_language_triplets_enhanced_temp.json'
            with open(temp_output, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

# 更新元数据
data['metadata']['llm_enhanced'] = True
data['metadata']['enhancement_stats'] = {
    'enhanced_events': enhanced_count,
    'failed_events': failed_count,
    'total_events': len(event_records),
    'model': MODEL_NAME,
    'enhanced_at': datetime.now().isoformat(),
    'parallel_workers': 20
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
print(f"  平均速度: {len(event_records) / total_time:.1f} 条/秒")

print(f"\n文件信息:")
print(f"  输出文件: {output_file}")
print(f"  文件大小: {file_size:.2f} MB")

print(f"\n数据组成:")
print(f"  关系三元组: {len([r for r in records if r['type'] == 'relationship'])} 条 (规则版本)")
print(f"  事件描述: {len(event_records)} 条 (LLM增强版)")
print(f"  总记录数: {len(records)} 条")

print("\n" + "=" * 80)
