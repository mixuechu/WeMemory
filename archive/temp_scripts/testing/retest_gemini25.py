#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重新测试 Gemini 2.5 系列"""
import sys
import os
import json
import pickle
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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

EXTRACTION_PROMPT = """你是一个信息提取专家。请从以下微信对话中提取结构化信息。

对话名称: {conversation_name}

对话内容:
{conversation_text}

请提取以下信息（返回JSON）:

{{
  "people": [
    {{
      "name": "姓名",
      "relationship": "配偶/父母/子女/朋友/同事/客户/其他",
      "occupation": "职业或null",
      "company": "公司或null",
      "personality": ["性格特征"],
      "expertise": ["擅长领域"],
      "confidence": 0.9
    }}
  ],
  "topics": [
    {{
      "name": "主题名称",
      "type": "工作项目/技术方案/家庭决策/旅游/健康/理财/兴趣爱好/其他",
      "keywords": ["关键词"],
      "confidence": 0.85
    }}
  ],
  "events": [
    {{
      "name": "事件名称",
      "type": "会议/聚会/旅游/就医/购物/其他",
      "participants": ["参与者"],
      "description": "简短描述",
      "confidence": 0.8
    }}
  ],
  "locations": [
    {{
      "name": "地点名称",
      "type": "餐厅/景点/医院/公司/住址/其他",
      "notes": "备注",
      "confidence": 0.75
    }}
  ]
}}

注意：
1. 只提取明确提到的信息
2. 不要把"我"、"米雪川"作为Person实体（这是用户本人）
3. confidence表示置信度（0-1）
4. 如果没有某类实体，返回[]
5. 务必返回合法JSON"""


def load_test_conversations(vector_store_path: str, count: int = 3) -> list:
    """加载测试对话"""
    with open(vector_store_path, 'rb') as f:
        data = pickle.load(f)

    metadata = data.get('metadata', [])

    conversations = {}
    for item in metadata:
        content = item.get('content_text', '')
        if not content or len(content) < 50:
            continue

        conv_name = item.get('conversation_name', 'Unknown')
        if conv_name not in conversations:
            conversations[conv_name] = []
        conversations[conv_name].append(item)

    suitable = []
    for conv_name, sessions in conversations.items():
        if 6 <= len(sessions) <= 10:
            suitable.append({
                'conversation_name': conv_name,
                'sessions': sessions
            })

    selected = random.sample(suitable, min(count, len(suitable)))
    return selected


def call_gemini_model(model_name: str, prompt: str) -> dict:
    """调用 Gemini 模型"""
    try:
        model = GenerativeModel(model_name)

        response = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": 8000}  # 足够包含思考过程
        )

        result_text = response.text

        # 解析 JSON
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]

        parsed = json.loads(result_text.strip())

        # 获取 token 使用情况
        usage = {}
        if hasattr(response, 'usage_metadata'):
            usage = {
                "input_tokens": response.usage_metadata.prompt_token_count,
                "output_tokens": response.usage_metadata.candidates_token_count,
                "thoughts_tokens": getattr(response.usage_metadata, 'thoughts_token_count', 0)
            }

        return {
            "result": parsed,
            "usage": usage,
            "error": None
        }

    except Exception as e:
        return {"result": None, "usage": {}, "error": str(e)}


def extract_task(model_name: str, conversation: dict) -> dict:
    """提取任务"""
    conversation_text = ""
    for session in conversation['sessions']:
        content = session.get('content_text', '')
        conversation_text += f"{content}\n\n"

    conversation_text = conversation_text[:4000]

    prompt = EXTRACTION_PROMPT.format(
        conversation_name=conversation['conversation_name'],
        conversation_text=conversation_text
    )

    response = call_gemini_model(model_name, prompt)

    return {
        'model_name': model_name,
        'conversation': conversation,
        'extraction': response['result'],
        'usage': response['usage'],
        'error': response['error']
    }


# 测试
models = ["gemini-2.5-flash", "gemini-2.5-pro"]
conversations = load_test_conversations("vector_stores/conversations_complete.pkl", count=3)

print(f"测试 {len(models)} 个模型 × {len(conversations)} 个对话 = {len(models) * len(conversations)} 个任务\n")

results = {m: [] for m in models}

with ThreadPoolExecutor(max_workers=6) as executor:
    tasks = []
    for model_name in models:
        for conv in conversations:
            tasks.append(executor.submit(extract_task, model_name, conv))

    for future in as_completed(tasks):
        result = future.result()
        results[result['model_name']].append(result)

        status = "OK" if not result['error'] else f"FAIL: {result['error'][:50]}"
        thoughts = result['usage'].get('thoughts_tokens', 0)
        print(f"{result['model_name']:20s} - {status} (思考tokens: {thoughts})")

# 汇总
print("\n" + "="*80)
for model_name, model_results in results.items():
    success = sum(1 for r in model_results if not r['error'])
    total_entities = sum(
        len(r['extraction'].get('people', [])) +
        len(r['extraction'].get('topics', [])) +
        len(r['extraction'].get('events', [])) +
        len(r['extraction'].get('locations', []))
        for r in model_results if r['extraction']
    )

    print(f"{model_name:20s}: {success}/{len(model_results)} 成功, 提取实体: {total_entities}")
