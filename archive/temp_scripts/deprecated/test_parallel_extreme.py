#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试极限并行度"""

import os
import sys
import io
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

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
    print(f'\n🧪 测试 {num_workers} workers 处理 {num_batches} 个批次...')

    start_time = time.time()
    results = []
    error_429 = 0
    error_other = 0

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(process_one, i): i for i in range(num_batches)}

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            if result['status'] == 'failed':
                if '429' in result.get('error', ''):
                    error_429 += 1
                else:
                    error_other += 1

    total_time = time.time() - start_time
    success_count = sum(1 for r in results if r['status'] == 'success')
    avg_batch_time = sum(r['time'] for r in results) / len(results)

    rate = num_batches / total_time
    theoretical_rate = num_workers / avg_batch_time
    efficiency = (rate / theoretical_rate) * 100

    return {
        'workers': num_workers,
        'batches': num_batches,
        'total_time': total_time,
        'rate': rate,
        'avg_batch_time': avg_batch_time,
        'theoretical_rate': theoretical_rate,
        'efficiency': efficiency,
        'success': success_count,
        'error_429': error_429,
        'error_other': error_other
    }


def main():
    print('='*70)
    print('🔬 极限并行度测试')
    print('='*70)
    print(f'\n测试范围: 10-100 workers')
    print(f'每个配置测试: 50个批次\n')

    # 测试不同并行度
    test_configs = [10, 20, 30, 40, 50, 60, 80, 100]

    results = []
    for workers in test_configs:
        result = test_parallel(workers, 50)
        results.append(result)

        print(f'  ✓ {workers} workers: {result["rate"]:.1f}批次/秒 | '
              f'效率{result["efficiency"]:.0f}% | '
              f'成功:{result["success"]}/{result["batches"]} | '
              f'429错误:{result["error_429"]}')

        time.sleep(1)  # 短暂休息

    # 找到最佳配置
    print(f'\n{"="*70}')
    print('📊 结果汇总')
    print(f'{"="*70}\n')
    print(f'{"Workers":<10} {"速度":<15} {"效率":<10} {"429错误":<10} {"评分"}')
    print('-'*70)

    best_rate = max(r['rate'] for r in results)
    no_error_results = [r for r in results if r['error_429'] == 0]
    best_efficiency = max(r['efficiency'] for r in no_error_results) if no_error_results else 100

    for r in results:
        # 综合评分：速度 - 错误惩罚
        score = r['rate'] - (r['error_429'] * 0.5) - (r['error_other'] * 0.2)

        if r['rate'] >= best_rate * 0.95 and r['error_429'] == 0:
            marker = '🏆 最佳'
        elif r['error_429'] > 0:
            marker = '⚠️  有429'
        elif r['rate'] < best_rate * 0.5:
            marker = '❌ 太慢'
        else:
            marker = '✓'

        print(f'{r["workers"]:<10} {r["rate"]:.1f}批次/秒{"":<4} '
              f'{r["efficiency"]:.0f}%{"":<5} '
              f'{r["error_429"]:<10} {marker}')

    # 推荐配置
    print(f'\n💡 推荐配置:')

    # 找到无429错误且速度最快的配置
    valid_results = [r for r in results if r['error_429'] == 0]
    if valid_results:
        best = max(valid_results, key=lambda x: x['rate'])
        speedup_vs_10 = best['rate'] / results[0]['rate']

        print(f'  🎯 PARALLEL_WORKERS = {best["workers"]}')
        print(f'  ')
        print(f'  预期效果:')
        print(f'    - 速度: {best["rate"]:.1f} 批次/秒')
        print(f'    - 相比10workers提速: {speedup_vs_10:.1f}倍')
        print(f'    - 剩余时间: {(49214-10600)/best["rate"]/3600:.1f} 小时')
        print(f'    - 预计完成: 今天晚上' if (49214-10600)/best["rate"]/3600 < 12 else '明天')
    else:
        print(f'  ⚠️  所有配置都有429错误，保持当前10 workers')


if __name__ == '__main__':
    main()
