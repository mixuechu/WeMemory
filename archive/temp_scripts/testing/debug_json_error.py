#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('../extractions/test_three_users/session_3e0d5a69c21f26009f4122d033601431.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    raw = data['raw_response']

# 提取JSON
json_str = raw.split('```json')[1].split('```')[0].strip()

# 尝试解析
try:
    parsed = json.loads(json_str)
    print('JSON可以正常解析')
except json.JSONDecodeError as e:
    print(f'JSON错误: {e}')
    lines = json_str.split('\n')
    print(f'\n错误位置 line {e.lineno}:')

    # 显示错误行及前后2行
    for i in range(max(0, e.lineno-3), min(len(lines), e.lineno+2)):
        marker = ' >>> ' if i == e.lineno - 1 else '     '
        print(f'{marker}Line {i+1}: {lines[i]}')

    # 显示错误字符附近
    print(f'\n字符位置 {e.pos}:')
    start = max(0, e.pos - 50)
    end = min(len(json_str), e.pos + 50)
    print(f'...{json_str[start:e.pos]}[ERROR HERE]{json_str[e.pos:end]}...')
