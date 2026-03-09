#!/usr/bin/env python3
"""检查可用的Claude模型"""

import json
import os
import tempfile
from pathlib import Path

# 加载.env
env_file = Path(__file__).parent.parent / '.env'
with open(env_file, 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ[key] = value

PROJECT_ID = os.getenv('VITE_GOOGLE_CLOUD_PROJECT')
LOCATION = os.getenv('VITE_GOOGLE_CLOUD_LOCATION', 'us-central1')
CREDENTIALS_JSON = os.getenv('VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON')

credentials_dict = json.loads(CREDENTIALS_JSON)
temp_creds_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
json.dump(credentials_dict, temp_creds_file)
temp_creds_file.close()
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_creds_file.name

print(f"Project: {PROJECT_ID}")
print(f"Location: {LOCATION}")
print("\n尝试的模型版本:")

from anthropic import AnthropicVertex

# 可能的模型名称
models_to_try = [
    "claude-3-5-sonnet@20240620",
    "claude-3-5-sonnet-v2@20241022",
    "claude-3-sonnet@20240229",
    "claude-sonnet-4-20250514",
]

regions_to_try = [
    "us-central1",
    "us-east5",
    "europe-west1",
]

for region in regions_to_try:
    print(f"\n测试 region: {region}")
    for model in models_to_try:
        try:
            client = AnthropicVertex(region=region, project_id=PROJECT_ID)
            message = client.messages.create(
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
                model=model,
            )
            print(f"  ✓ {model} - 可用!")
            break  # 找到一个可用的就停止
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                print(f"  ✗ {model} - 不可用 (404)")
            else:
                print(f"  ✗ {model} - 错误: {error_msg[:100]}")

try:
    os.unlink(temp_creds_file.name)
except:
    pass
