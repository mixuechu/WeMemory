#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 Gemini 2.5 Flash 的实际响应速度"""
import os
import json
import time
from dotenv import load_dotenv
load_dotenv()

from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel

PROJECT_ID = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
credentials_json = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

creds_dict = json.loads(credentials_json)
credentials = service_account.Credentials.from_service_account_info(creds_dict)

vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

# 简单测试 prompt
simple_prompt = "请用一句话介绍北京"

# 复杂测试 prompt（类似实体提取任务）
complex_prompt = """你是一个信息提取专家。请从以下微信对话中提取结构化信息。

对话名称: 测试对话

对话内容:
小明: 周末一起去颐和园玩吧
小红: 好啊，几点出发？
小明: 早上9点，在地铁站见面
小红: 行，那我带点吃的
小明: 我带相机，可以拍照

请提取以下信息（返回JSON）:

{
  "people": [
    {
      "name": "姓名",
      "relationship": "朋友",
      "confidence": 0.9
    }
  ],
  "topics": [
    {
      "name": "主题名称",
      "type": "旅游",
      "keywords": ["关键词"],
      "confidence": 0.85
    }
  ],
  "events": [
    {
      "name": "事件名称",
      "type": "旅游",
      "participants": ["参与者"],
      "description": "简短描述",
      "confidence": 0.8
    }
  ],
  "locations": [
    {
      "name": "地点名称",
      "type": "景点",
      "notes": "备注",
      "confidence": 0.75
    }
  ]
}

注意：务必返回合法JSON"""

models_to_test = [
    ("gemini-2.5-flash", 8000),
    ("gemini-2.5-pro", 8000),
    ("gemini-2.0-flash", 2000)
]

print("Gemini 速度对比测试")
print("=" * 80)

for model_name, max_tokens in models_to_test:
    print(f"\n{model_name}:")
    print("-" * 80)

    model = GenerativeModel(model_name)

    # 测试1: 简单任务
    start = time.time()
    response = model.generate_content(
        simple_prompt,
        generation_config={"max_output_tokens": max_tokens}
    )
    simple_time = time.time() - start

    simple_output = len(response.text)
    simple_thoughts = 0
    if hasattr(response, 'usage_metadata'):
        simple_thoughts = getattr(response.usage_metadata, 'thoughts_token_count', 0)

    print(f"  简单任务: {simple_time:.2f}秒")
    print(f"    - 输出长度: {simple_output} 字符")
    if simple_thoughts > 0:
        print(f"    - 思考 tokens: {simple_thoughts}")

    # 测试2: 复杂任务（实体提取）
    start = time.time()
    response = model.generate_content(
        complex_prompt,
        generation_config={"max_output_tokens": max_tokens}
    )
    complex_time = time.time() - start

    complex_output = len(response.text)
    complex_thoughts = 0
    if hasattr(response, 'usage_metadata'):
        complex_thoughts = getattr(response.usage_metadata, 'thoughts_token_count', 0)
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        total_tokens = getattr(response.usage_metadata, 'total_token_count', 0)

    print(f"  复杂任务（实体提取）: {complex_time:.2f}秒")
    print(f"    - 输入 tokens: {input_tokens}")
    print(f"    - 输出 tokens: {output_tokens}")
    if complex_thoughts > 0:
        print(f"    - 思考 tokens: {complex_thoughts}")
        print(f"    - 思考占比: {complex_thoughts / total_tokens * 100:.1f}%")
    print(f"    - 输出长度: {complex_output} 字符")
    print(f"    - 平均速度: {output_tokens / complex_time:.0f} tokens/秒")

# 计算全量处理时间预估
print("\n" + "=" * 80)
print("全量处理时间预估（183,000 条对话）:")
print("-" * 80)

for model_name, _ in models_to_test:
    if "2.5" in model_name:
        avg_time = 3.0  # 保守估计
    else:
        avg_time = 2.0

    # 单线程
    total_hours_single = 183000 * avg_time / 3600

    # 并行（10 workers）
    total_hours_parallel_10 = total_hours_single / 10

    # 并行（20 workers）
    total_hours_parallel_20 = total_hours_single / 20

    print(f"\n{model_name}（假设 {avg_time:.1f}秒/对话）:")
    print(f"  单线程: {total_hours_single:.1f} 小时")
    print(f"  并行10: {total_hours_parallel_10:.1f} 小时")
    print(f"  并行20: {total_hours_parallel_20:.1f} 小时")
