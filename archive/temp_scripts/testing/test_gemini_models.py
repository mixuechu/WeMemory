#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试不同的Gemini模型"""

import json
import os
import requests
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# 设置代理
proxies = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890',
}

# 加载.env
env_file = Path(__file__).parent.parent / '.env'
load_dotenv(env_file)

PROJECT_ID = os.getenv('VITE_GOOGLE_CLOUD_PROJECT')
LOCATION = os.getenv('VITE_GOOGLE_CLOUD_LOCATION', 'us-central1')
CREDENTIALS_JSON = os.getenv('VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON')

# 获取access token
creds_dict = json.loads(CREDENTIALS_JSON)
credentials = service_account.Credentials.from_service_account_info(
    creds_dict,
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
credentials.refresh(Request())
access_token = credentials.token

print(f"Project: {PROJECT_ID}")
print(f"Location: {LOCATION}\n")

# 测试多个模型
models_to_test = [
    "gemini-2.5-flash",
    "gemini-2.0-flash-exp",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-pro",
]

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

payload = {
    "contents": [{
        "role": "user",
        "parts": [{"text": "Say hello"}]
    }],
    "generationConfig": {
        "temperature": 0.1,
        "maxOutputTokens": 50
    }
}

for model in models_to_test:
    print(f"测试 {model}...")
    url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{model}:generateContent"

    try:
        response = requests.post(url, headers=headers, json=payload, proxies=proxies, timeout=30)

        if response.status_code == 200:
            result = response.json()
            text = result['candidates'][0]['content']['parts'][0]['text']
            print(f"  ✓ 成功: {text}\n")
            break  # 找到可用的模型就停止
        elif response.status_code == 404:
            print(f"  ✗ 404 模型不存在\n")
        else:
            error = response.json().get('error', {})
            print(f"  ✗ {response.status_code}: {error.get('message', response.text[:100])}\n")
    except Exception as e:
        print(f"  ✗ 异常: {str(e)[:100]}\n")
