#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速测试：只提取JY的对话（66个sessions）"""

import os
import sys
import io
import json
import pickle
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

load_dotenv()

from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel

# 配置
PROJECT_ID = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
credentials_json = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

creds_dict = json.loads(credentials_json)
credentials = service_account.Credentials.from_service_account_info(creds_dict)
vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

# 导入提取函数
sys.path.append(str(Path(__file__).parent))
from full_extraction import (
    call_gemini_extract,
    build_extraction_result,
    save_extraction,
    BLACKLIST
)

VECTOR_STORE_PATH = Path(__file__).parent.parent / "vector_stores" / "conversations_complete.pkl"
OUTPUT_DIR = Path(__file__).parent.parent / "extractions" / "test_jy_only"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_USER = "JY"
PARALLEL_WORKERS = 20


def main():
    """主函数：只提取JY的对话"""
    print("=" * 80)
    print(f"快速测试: 只提取 {TARGET_USER}")
    print("=" * 80)
    print()

    # 加载数据
    print(f"📂 加载数据: {VECTOR_STORE_PATH}")
    with open(VECTOR_STORE_PATH, 'rb') as f:
        data = pickle.load(f)

    metadata = data.get('metadata', [])
    print(f"✅ 总对话数: {len(metadata):,}")
    print()

    # 过滤目标用户的对话
    target_sessions = []

    for item in metadata:
        conv_name = item.get('conversation_name', '')

        # 跳过黑名单
        if conv_name in BLACKLIST:
            continue

        # 只提取目标用户
        if conv_name == TARGET_USER:
            target_sessions.append(item)

    print(f"📊 {TARGET_USER} 对话统计:")
    print("=" * 60)
    print(f"  对话数: {len(target_sessions):,}")

    # 统计消息数
    total_messages = sum(s.get('message_count', 0) for s in target_sessions)
    print(f"  消息数: {total_messages:,}")
    print(f"  平均: {total_messages/len(target_sessions):.1f} 条/对话")
    print()

    if len(target_sessions) == 0:
        print("❌ 没有找到目标用户的对话！")
        return

    # 预估
    avg_time = 28  # 秒/对话
    total_time_seconds = len(target_sessions) * avg_time / PARALLEL_WORKERS
    total_time_minutes = total_time_seconds / 60
    estimated_cost = len(target_sessions) * 0.001434

    print("⏱️ 预估:")
    print(f"  - 耗时: {total_time_minutes:.1f} 分钟")
    print(f"  - 成本: ${estimated_cost:.2f}")
    print()

    # 自动开始（测试模式）
    print("⚡ 自动开始提取...")
    print()
    print("=" * 80)
    print("🔥 开始并行提取...")
    print("=" * 80)
    print()

    start_time = time.time()

    # 统计
    stats = {
        'success': 0,
        'failed': 0,
        'total_cost': 0.0,
        'total_duration': 0.0
    }

    # 并行处理
    with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:
        futures = {}
        for idx, session in enumerate(target_sessions):
            future = executor.submit(process_single, session, idx + 1, len(target_sessions))
            futures[future] = session

        for future in as_completed(futures):
            result = future.result()

            stats[result['status']] += 1
            stats['total_cost'] += result.get('cost', 0)
            stats['total_duration'] += result.get('duration', 0)

    # 完成
    total_time = time.time() - start_time

    print("\n" + "=" * 80)
    print("🎉 提取完成！")
    print("=" * 80)

    print(f"\n📊 最终统计:")
    print(f"  - 总耗时: {total_time/60:.1f} 分钟 ({total_time:.0f} 秒)")
    print(f"  - 成功: {stats['success']:,}")
    print(f"  - 失败: {stats['failed']:,}")
    if stats['success'] + stats['failed'] > 0:
        print(f"  - 成功率: {stats['success']/(stats['success']+stats['failed'])*100:.1f}%")
    print(f"  - 总成本: ${stats['total_cost']:.4f}")
    print(f"  - 平均速度: {len(target_sessions)/total_time:.1f} 对话/秒")
    print(f"  - 平均耗时: {total_time/len(target_sessions):.1f} 秒/对话")

    print(f"\n💾 输出目录: {OUTPUT_DIR}")
    print(f"📁 文件数量: {len(list(OUTPUT_DIR.glob('*.json'))):,}")


def process_single(session, index, total):
    """处理单条对话"""
    session_id = session.get('session_id', 'unknown')
    conv_name = session.get('conversation_name', 'Unknown')

    print(f"  [{index}/{total}] 处理中: {conv_name}")

    # 提取
    extraction_result = call_gemini_extract(session)

    # 构建完整结果
    result = build_extraction_result(session, extraction_result)

    # 保存
    save_extraction(result, OUTPUT_DIR)

    status = 'success' if extraction_result['success'] else 'failed'
    print(f"  {'✅' if status == 'success' else '❌'} [{index}/{total}] 完成: {conv_name}")

    return {
        'status': status,
        'session_id': session_id,
        'cost': extraction_result.get('metadata', {}).get('cost', 0) if extraction_result['success'] else 0,
        'duration': extraction_result.get('metadata', {}).get('duration_seconds', 0) if extraction_result['success'] else 0
    }


if __name__ == '__main__':
    main()
