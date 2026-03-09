#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试不同并行度的实际速度"""

import os
import sys
import io
import json
import time
import hashlib
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 加载环境变量
load_dotenv(dotenv_path='../.env')
creds_json = os.getenv('VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON')
if not creds_json:
    print("错误: 未找到VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")
    sys.exit(1)

creds_dict = json.loads(creds_json)

from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel

credentials = service_account.Credentials.from_service_account_info(creds_dict)
vertexai.init(project=creds_dict['project_id'], location="us-central1", credentials=credentials)

MODEL_NAME = "gemini-2.0-flash-exp"

# 简化的提取prompt（只提取People）
SIMPLE_PROMPT = """分析以下对话，提取人物。

对话：
{conversation_text}

返回JSON格式：
```json
{{
  "people": [
    {{
      "name": "人名",
      "is_user": true/false
    }}
  ]
}}
```
"""


def extract_simple(text: str) -> dict:
    """简化的提取函数"""
    model = GenerativeModel(MODEL_NAME)
    prompt = SIMPLE_PROMPT.format(conversation_text=text)
    response = model.generate_content(prompt)
    result_text = response.text.strip()

    if '```json' in result_text:
        result_text = result_text.split('```json')[1].split('```')[0].strip()
    elif '```' in result_text:
        result_text = result_text.split('```')[1].split('```')[0].strip()

    return json.loads(result_text)


def process_one(idx: int) -> dict:
    """处理一个测试批次"""
    test_text = f"米雪川: 测试消息{idx}\n对方: 好的收到"
    start = time.time()
    try:
        result = extract_simple(test_text)
        elapsed = time.time() - start
        return {'status': 'success', 'time': elapsed, 'idx': idx}
    except Exception as e:
        elapsed = time.time() - start
        return {'status': 'failed', 'time': elapsed, 'idx': idx, 'error': str(e)}


def test_parallel(num_workers: int, num_batches: int):
    """测试指定并行度"""
    print(f'\n{"="*70}')
    print(f'🧪 测试 {num_workers} workers 处理 {num_batches} 个批次')
    print(f'{"="*70}')

    start_time = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(process_one, i): i for i in range(num_batches)}

        completed_count = 0
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed_count += 1

            # 每10个打印一次进度
            if completed_count % 10 == 0 or completed_count == num_batches:
                elapsed = time.time() - start_time
                rate = completed_count / elapsed
                print(f'  进度: {completed_count}/{num_batches} | '
                      f'耗时: {elapsed:.1f}秒 | '
                      f'速度: {rate:.2f}批次/秒')

    total_time = time.time() - start_time
    success_count = sum(1 for r in results if r['status'] == 'success')
    avg_batch_time = sum(r['time'] for r in results) / len(results)

    print(f'\n📊 结果统计:')
    print(f'  总耗时: {total_time:.2f}秒')
    print(f'  成功: {success_count}/{num_batches}')
    print(f'  平均速度: {num_batches/total_time:.2f} 批次/秒')
    print(f'  平均每批次API时间: {avg_batch_time:.2f}秒')
    print(f'  理论最大速度: {num_workers/avg_batch_time:.2f} 批次/秒')
    print(f'  实际/理论: {(num_batches/total_time)/(num_workers/avg_batch_time)*100:.1f}%')

    return {
        'workers': num_workers,
        'batches': num_batches,
        'total_time': total_time,
        'rate': num_batches / total_time,
        'avg_batch_time': avg_batch_time,
        'theoretical_rate': num_workers / avg_batch_time,
        'efficiency': (num_batches/total_time) / (num_workers/avg_batch_time) * 100
    }


def main():
    print('='*70)
    print('🔬 并行度速度测试')
    print('='*70)
    print(f'\n⚠️  注意: 这个测试会调用Gemini API，会消耗少量配额')
    print(f'预计测试时间: 2-3分钟\n')

    # 测试配置
    test_configs = [
        (10, 30),  # 10 workers, 30 batches
        (20, 30),  # 20 workers, 30 batches
        (30, 30),  # 30 workers, 30 batches
    ]

    results = []
    for workers, batches in test_configs:
        result = test_parallel(workers, batches)
        results.append(result)
        time.sleep(2)  # 短暂休息避免API限速

    # 对比结果
    print(f'\n{"="*70}')
    print('📈 对比结果')
    print(f'{"="*70}')
    print(f'\n{"Workers":<10} {"速度":<15} {"效率":<15} {"结论"}')
    print('-'*70)

    baseline = results[0]['rate']
    for r in results:
        speedup = r['rate'] / baseline
        efficiency = r['efficiency']

        if speedup > 1.5:
            conclusion = f'✅ 提速{speedup:.1f}x'
        elif speedup > 1.1:
            conclusion = f'⚠️  小幅提速{speedup:.1f}x'
        else:
            conclusion = f'❌ 无提速'

        print(f'{r["workers"]:<10} {r["rate"]:.2f}批次/秒{"":<3} {efficiency:.1f}%{"":<9} {conclusion}')

    print(f'\n💡 结论:')
    if results[-1]['rate'] / results[0]['rate'] > 1.5:
        print(f'  ✅ 提高并行度有效！可以将PARALLEL_WORKERS提高到{results[-1]["workers"]}')
        print(f'  预期提速: {results[-1]["rate"] / results[0]["rate"]:.1f}倍')
    elif results[-1]['rate'] / results[0]['rate'] > 1.1:
        print(f'  ⚠️  提高并行度有小幅帮助，建议提高到{results[1]["workers"]}')
        print(f'  预期提速: {results[1]["rate"] / results[0]["rate"]:.1f}倍')
    else:
        print(f'  ❌ 提高并行度无效，存在API或SDK限制')
        print(f'  建议: 保持当前10 workers配置')


if __name__ == '__main__':
    main()
