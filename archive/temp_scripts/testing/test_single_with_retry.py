#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试单条对话提取，包含失败记录和重试机制"""

import os
import json
import pickle
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

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

# 导入提取相关函数
import sys
sys.path.append(str(Path(__file__).parent))
from full_extraction import (
    EXTRACTION_PROMPT,
    format_conversation_for_extraction,
    call_gemini_extract,
    build_extraction_result,
    extract_with_retry
)

VECTOR_STORE_PATH = "vector_stores/conversations_complete.pkl"
DEBUG_DIR = Path("knowledge_graph/debug")
DEBUG_DIR.mkdir(exist_ok=True)


def load_sample_conversation():
    """加载一条有代表性的对话"""
    print("Loading conversation data...")

    with open(VECTOR_STORE_PATH, 'rb') as f:
        data = pickle.load(f)

    metadata = data.get('metadata', [])

    # 找一条合适的对话（6-10条消息，有内容）
    suitable = []
    for item in metadata:
        content = item.get('content_text', '')
        msg_count = item.get('message_count', 0)

        if 6 <= msg_count <= 10 and len(content) > 200:
            suitable.append(item)

    if not suitable:
        print("ERROR: No suitable conversation found")
        return None

    # 选择第一个
    selected = suitable[0]

    print(f"Selected conversation: {selected.get('conversation_name', 'Unknown')}")
    print(f"  Messages: {selected.get('message_count', 0)}")
    print(f"  Time: {selected.get('year', '?')}-{selected.get('month', '?')}")
    print(f"  Type: {selected.get('conversation_type', '?')}")

    return selected


def test_extraction_with_retry():
    """测试提取（包含失败记录和重试）"""
    print("=" * 80)
    print("Single Conversation Extraction Test (with Retry)")
    print("=" * 80)
    print()

    # 加载样本对话
    session = load_sample_conversation()
    if not session:
        return

    session_id = session.get('session_id', 'unknown')
    conv_name = session.get('conversation_name', 'Unknown')

    print()
    print("Conversation Preview:")
    print("-" * 80)
    content = session.get('content_text', '')
    print(content[:500] + "..." if len(content) > 500 else content)
    print("-" * 80)

    # 尝试提取（最多3次）
    max_attempts = 3
    all_results = []

    for attempt in range(1, max_attempts + 1):
        print()
        print("=" * 80)
        print(f"Attempt {attempt}/{max_attempts}")
        print("=" * 80)
        print()

        print(f"Starting extraction (attempt {attempt})...")

        # 提取
        extraction_result = call_gemini_extract(session)
        result = build_extraction_result(session, extraction_result)

        # 保存本次结果
        all_results.append({
            'attempt': attempt,
            'success': result['success'],
            'result': result
        })

        # 如果失败，保存原始输出用于分析
        if not result['success']:
            print()
            print(f"FAILED on attempt {attempt}")
            print(f"Error: {result.get('error', 'Unknown')}")

            # 保存失败的原始JSON
            if result.get('raw_response'):
                raw_file = DEBUG_DIR / f"failed_attempt_{attempt}_{session_id}.txt"
                with open(raw_file, 'w', encoding='utf-8') as f:
                    f.write(result['raw_response'])
                print(f"Raw response saved to: {raw_file}")

                # 显示原始输出的前500字符
                print()
                print("Raw response preview (first 500 chars):")
                print("-" * 80)
                print(result['raw_response'][:500])
                print("-" * 80)

                # 分析失败原因
                print()
                print("Analyzing failure...")
                raw = result['raw_response']

                issues = []

                # 检查常见问题
                if raw.count('"') % 2 != 0:
                    issues.append("Odd number of quotes (missing closing quote)")

                if not raw.strip().endswith('}'):
                    issues.append(f"Response doesn't end with }} (ends with: {repr(raw.strip()[-20:])})")

                if '\\n' not in raw and '\n' in raw[raw.find('"'):] if '"' in raw else False:
                    issues.append("Literal newline in string (should be \\n)")

                if issues:
                    print("Detected issues:")
                    for issue in issues:
                        print(f"  - {issue}")
                else:
                    print("No obvious issues detected (may be complex JSON structure problem)")

            print()
            print(f"Will retry (attempt {attempt + 1})...")

        else:
            # 成功了
            print()
            print(f"SUCCESS on attempt {attempt}!")

            # 保存成功的结果
            success_file = DEBUG_DIR / f"success_attempt_{attempt}_{session_id}.json"
            with open(success_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"Result saved to: {success_file}")

            # 显示摘要
            entities = result['entities']
            print()
            print("Entity Statistics:")
            print(f"  - People: {len(entities.get('people', []))}")
            print(f"  - Organizations: {len(entities.get('organizations', []))}")
            print(f"  - Topics: {len(entities.get('topics', []))}")
            print(f"  - Events: {len(entities.get('events', []))}")
            print(f"  - Locations: {len(entities.get('locations', []))}")
            print(f"  - Relationships: {len(entities.get('relationships', []))}")

            metadata = result.get('extraction_metadata', {})
            if metadata:
                print()
                print("Performance:")
                print(f"  - Duration: {metadata.get('duration_seconds', 0):.2f} seconds")
                print(f"  - Input tokens: {metadata.get('input_tokens', 0):,}")
                print(f"  - Output tokens: {metadata.get('output_tokens', 0):,}")
                print(f"  - Thoughts tokens: {metadata.get('thoughts_tokens', 0):,}")
                print(f"  - Cost: ${metadata.get('cost', 0):.6f}")

            # 成功就退出
            break

    # 最终总结
    print()
    print("=" * 80)
    print("Final Summary")
    print("=" * 80)
    print()

    print(f"Total attempts: {len(all_results)}")
    success_count = sum(1 for r in all_results if r['success'])
    print(f"Successful: {success_count}/{len(all_results)}")

    if success_count > 0:
        # 找到第一次成功的尝试
        first_success = next(r for r in all_results if r['success'])
        print(f"First success on attempt: {first_success['attempt']}")

        if first_success['attempt'] > 1:
            print()
            print("INSIGHT: Retry mechanism worked!")
            print(f"  - Failed {first_success['attempt'] - 1} time(s) before success")
            print(f"  - This demonstrates the 87.5% success rate issue")
    else:
        print()
        print("WARNING: All attempts failed!")
        print("  - Check the saved raw responses in debug/ folder")
        print(f"  - Files: {list(DEBUG_DIR.glob(f'failed_attempt_*_{session_id}.txt'))}")

    print()
    print("Debug files location:")
    print(f"  {DEBUG_DIR}/")
    print()
    print("=" * 80)


if __name__ == '__main__':
    test_extraction_with_retry()
