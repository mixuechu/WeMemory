#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试 JSON 解析失败的案例"""

import json
from pathlib import Path
from collections import Counter

OUTPUT_DIR = Path("extractions")


def analyze_failures():
    """分析所有失败的提取"""
    print("=" * 80)
    print("JSON Parsing Failures Analysis")
    print("=" * 80)
    print()

    files = list(OUTPUT_DIR.glob("session_*.json"))

    failed_cases = []
    error_types = Counter()

    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                result = json.load(f)

            if not result.get('success'):
                error = result.get('error', 'Unknown')
                raw_response = result.get('raw_response')

                failed_cases.append({
                    'filepath': filepath,
                    'conversation_name': result['conversation']['conversation_name'],
                    'error': error,
                    'raw_response': raw_response
                })

                # 统计错误类型
                if 'JSON解析错误' in error:
                    if 'Unterminated string' in error:
                        error_types['Unterminated string'] += 1
                    elif 'Expecting value' in error:
                        error_types['Expecting value'] += 1
                    elif 'Invalid control character' in error:
                        error_types['Invalid control character'] += 1
                    elif 'Extra data' in error:
                        error_types['Extra data'] += 1
                    else:
                        error_types['Other JSON error'] += 1
                else:
                    error_types[error] += 1

        except Exception as e:
            print(f"WARNING: Cannot read {filepath.name}: {e}")

    print(f"Total failures: {len(failed_cases)}")
    print()

    if error_types:
        print("Error type distribution:")
        for error_type, count in error_types.most_common():
            print(f"  - {error_type}: {count}")
        print()

    # 显示前3个失败案例的原始输出
    print("=" * 80)
    print("Sample Failed Cases (with raw response)")
    print("=" * 80)
    print()

    for i, case in enumerate(failed_cases[:3], 1):
        print(f"Case {i}: {case['conversation_name']}")
        print(f"  File: {case['filepath'].name}")
        print(f"  Error: {case['error']}")
        print()

        if case['raw_response']:
            print("  Raw Response (first 1000 chars):")
            print("  " + "-" * 76)
            print("  " + case['raw_response'][:1000].replace('\n', '\n  '))
            print("  " + "-" * 76)
            print()

            # 尝试分析问题
            raw = case['raw_response']

            # 检查常见问题
            issues = []

            # 1. 检查是否有未闭合的字符串
            if raw.count('"') % 2 != 0:
                issues.append("Odd number of quotes (missing closing quote)")

            # 2. 检查是否有换行符在字符串中
            if '\\n' not in raw and '\n' in raw[raw.find('"'):]:
                issues.append("Literal newline in string (should be \\n)")

            # 3. 检查是否有非法字符
            if '\t' in raw and '\\t' not in raw:
                issues.append("Literal tab in string (should be \\t)")

            # 4. 检查是否截断
            if not raw.rstrip().endswith('}'):
                issues.append("Response truncated (doesn't end with })")

            # 5. 检查是否有多余文本
            if raw.strip().endswith('}') and len(raw.strip()) > len(raw.strip().rstrip('}')) + 1:
                issues.append("Extra text after closing }")

            if issues:
                print("  Detected issues:")
                for issue in issues:
                    print(f"    - {issue}")
                print()

    print("=" * 80)


def suggest_fixes():
    """建议修复方案"""
    print()
    print("=" * 80)
    print("Suggested Fixes for JSON Parsing Failures")
    print("=" * 80)
    print()

    fixes = [
        {
            "issue": "Unterminated string (missing closing quote)",
            "cause": "LLM generated incomplete JSON due to max_tokens limit",
            "fix": [
                "1. Increase max_output_tokens (currently 8000)",
                "2. Simplify prompt to reduce output length",
                "3. Post-process: auto-close unterminated strings"
            ]
        },
        {
            "issue": "Literal newline/tab in string",
            "cause": "LLM didn't escape special characters",
            "fix": [
                "1. Add to prompt: 'Escape all newlines as \\n and tabs as \\t'",
                "2. Post-process: replace literal \\n with \\\\n, \\t with \\\\t"
            ]
        },
        {
            "issue": "Invalid control character",
            "cause": "Raw text contains control characters (0x00-0x1F)",
            "fix": [
                "1. Pre-process input: remove/escape control characters",
                "2. Post-process output: remove control characters from JSON"
            ]
        },
        {
            "issue": "Response truncated",
            "cause": "Hit max_output_tokens limit",
            "fix": [
                "1. Increase max_output_tokens to 16000",
                "2. Simplify prompt (fewer examples, shorter instructions)",
                "3. Post-process: auto-complete truncated JSON"
            ]
        }
    ]

    for fix in fixes:
        print(f"Issue: {fix['issue']}")
        print(f"  Cause: {fix['cause']}")
        print("  Fixes:")
        for solution in fix['fix']:
            print(f"    {solution}")
        print()

    print("=" * 80)
    print()
    print("Recommended immediate action:")
    print("  1. Increase max_output_tokens from 8000 to 12000")
    print("  2. Add JSON post-processing to auto-fix common errors")
    print("  3. Simplify prompt by removing verbose examples")
    print()
    print("=" * 80)


if __name__ == '__main__':
    analyze_failures()
    suggest_fixes()
