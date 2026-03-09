#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面模型对比测试
对比所有可用模型的实体提取质量和成本
"""
import sys
import os
import json
import pickle
import random
import time
import requests
from pathlib import Path
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

# Google Auth
from google.oauth2 import service_account
from google.auth import default
from google.auth.transport.requests import Request
import vertexai
from vertexai.generative_models import GenerativeModel

PROJECT_ID = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
LOCATION_GEMINI = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
credentials_json = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

creds_dict = json.loads(credentials_json)
credentials = service_account.Credentials.from_service_account_info(creds_dict)

# 初始化 Vertex AI for Gemini
vertexai.init(project=PROJECT_ID, location=LOCATION_GEMINI, credentials=credentials)


def get_access_token() -> str:
    """获取 access token for Claude"""
    credentials, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    credentials.refresh(Request())
    return credentials.token


# 模型配置
MODELS = [
    {
        "name": "claude-sonnet-4",
        "type": "claude",
        "display_name": "Claude Sonnet 4",
        "cost_input": 3.0,   # $/1M tokens
        "cost_output": 15.0,
    },
    {
        "name": "claude-opus-4",
        "type": "claude",
        "display_name": "Claude Opus 4",
        "cost_input": 15.0,
        "cost_output": 75.0,
    },
    {
        "name": "gemini-2.5-flash",
        "type": "gemini",
        "display_name": "Gemini 2.5 Flash",
        "cost_input": 0.075,
        "cost_output": 0.30,
    },
    {
        "name": "gemini-2.5-pro",
        "type": "gemini",
        "display_name": "Gemini 2.5 Pro",
        "cost_input": 1.25,
        "cost_output": 5.0,
    },
    {
        "name": "gemini-2.0-flash",
        "type": "gemini",
        "display_name": "Gemini 2.0 Flash",
        "cost_input": 0.075,
        "cost_output": 0.30,
    },
]


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


def load_test_conversations(vector_store_path: str, count: int = 8) -> List[Dict]:
    """加载测试对话"""
    with open(vector_store_path, 'rb') as f:
        data = pickle.load(f)

    metadata = data.get('metadata', [])

    # 按对话分组
    conversations = {}
    for item in metadata:
        content = item.get('content_text', '')
        if not content or len(content) < 50:
            continue

        conv_name = item.get('conversation_name', 'Unknown')
        if conv_name not in conversations:
            conversations[conv_name] = []
        conversations[conv_name].append(item)

    # 选择合适的对话（6-10条消息）
    suitable = []
    for conv_name, sessions in conversations.items():
        if 6 <= len(sessions) <= 10:
            suitable.append({
                'conversation_name': conv_name,
                'sessions': sessions
            })

    # 随机选择
    selected = random.sample(suitable, min(count, len(suitable)))
    return selected


def call_claude_model(model_name: str, prompt: str) -> Dict:
    """调用 Claude 模型（REST API）"""
    url = f"https://aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/global/publishers/anthropic/models/{model_name}:rawPredict"

    access_token = get_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    request_body = {
        "anthropic_version": "vertex-2023-10-16",
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}]
            }
        ],
        "max_tokens": 2000
    }

    try:
        response = requests.post(url, headers=headers, json=request_body, timeout=60)

        if response.ok:
            result = response.json()
            content = result.get('content', [{}])[0].get('text', '')

            # 解析 JSON
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            return {
                "result": json.loads(content.strip()),
                "usage": result.get('usage', {}),
                "error": None
            }
        else:
            return {"result": None, "usage": {}, "error": f"{response.status_code}: {response.text[:200]}"}

    except Exception as e:
        return {"result": None, "usage": {}, "error": str(e)}


def call_gemini_model(model_name: str, prompt: str) -> Dict:
    """调用 Gemini 模型（SDK）"""
    try:
        model = GenerativeModel(model_name)

        # Gemini 2.5 有思考过程，需要更多 tokens
        max_tokens = 8000 if "2.5" in model_name else 2000

        response = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": max_tokens}
        )

        result_text = response.text

        # 解析 JSON
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]

        return {
            "result": json.loads(result_text.strip()),
            "usage": {
                # Gemini 的 usage 信息在 response 中，暂时估算
                "input_tokens": len(prompt) // 4,  # 粗略估算
                "output_tokens": len(result_text) // 4,
            },
            "error": None
        }

    except Exception as e:
        return {"result": None, "usage": {}, "error": str(e)}


def extract_with_model(model_config: Dict, conversation: Dict) -> Dict:
    """使用指定模型提取实体"""
    # 构建对话文本
    conversation_text = ""
    for session in conversation['sessions']:
        content = session.get('content_text', '')
        conversation_text += f"{content}\n\n"

    # 限制长度
    conversation_text = conversation_text[:4000]

    # 构建 prompt
    prompt = EXTRACTION_PROMPT.format(
        conversation_name=conversation['conversation_name'],
        conversation_text=conversation_text
    )

    # 调用模型
    if model_config['type'] == 'claude':
        response = call_claude_model(model_config['name'], prompt)
    else:
        response = call_gemini_model(model_config['name'], prompt)

    return response


def extract_task(model_config: Dict, conversation: Dict, conv_idx: int, total_convs: int) -> Dict:
    """单个提取任务（用于并行）"""
    start_time = time.time()
    response = extract_with_model(model_config, conversation)
    elapsed = time.time() - start_time

    return {
        'model_name': model_config['name'],
        'conversation': conversation,
        'extraction': response['result'],
        'usage': response['usage'],
        'error': response['error'],
        'time': elapsed
    }


def main():
    """主测试流程（并行版本）"""
    print("=" * 100)
    print("全面模型对比测试（并行）")
    print("=" * 100)

    # 加载测试对话
    print("\n加载测试对话...")
    conversations = load_test_conversations("vector_stores/conversations_complete.pkl", count=8)
    print(f"已加载 {len(conversations)} 个测试对话")

    # 创建所有任务
    tasks = []
    for model_config in MODELS:
        for idx, conv in enumerate(conversations, 1):
            tasks.append((model_config, conv, idx, len(conversations)))

    print(f"\n总共 {len(tasks)} 个任务（{len(MODELS)} 个模型 × {len(conversations)} 个对话）")
    print("开始并行执行...\n")

    # 并行执行所有任务
    all_results = {model['name']: {'config': model, 'results': []} for model in MODELS}

    start_time = time.time()
    completed = 0

    with ThreadPoolExecutor(max_workers=10) as executor:
        # 提交所有任务
        future_to_task = {
            executor.submit(extract_task, model_config, conv, idx, total): (model_config['name'], idx)
            for model_config, conv, idx, total in tasks
        }

        # 收集结果
        for future in as_completed(future_to_task):
            model_name, conv_idx = future_to_task[future]
            try:
                result = future.result()
                all_results[result['model_name']]['results'].append(result)

                completed += 1
                if result['error']:
                    status = "FAIL"
                else:
                    status = f"OK ({result['time']:.1f}s)"

                print(f"[{completed}/{len(tasks)}] {result['model_name'][:20]:20s} 对话#{conv_idx} - {status}")

            except Exception as e:
                print(f"[{completed}/{len(tasks)}] 任务失败: {str(e)[:50]}")
                completed += 1

    total_time = time.time() - start_time
    print(f"\n并行执行完成！总耗时: {total_time:.1f}秒")

    # 对每个模型的结果排序（按对话顺序）
    for model_name in all_results:
        all_results[model_name]['results'].sort(
            key=lambda x: conversations.index(x['conversation'])
        )

    # 保存详细结果
    output_file = "knowledge_graph/model_comparison_results.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("全面模型对比测试 - 详细结果\n")
        f.write("=" * 100 + "\n\n")

        for model_name, data in all_results.items():
            model_config = data['config']
            results = data['results']

            f.write(f"\n{'='*100}\n")
            f.write(f"模型: {model_config['display_name']}\n")
            f.write(f"{'='*100}\n\n")

            # 统计
            success_count = sum(1 for r in results if not r['error'])
            total_input_tokens = sum(r['usage'].get('input_tokens', 0) for r in results)
            total_output_tokens = sum(r['usage'].get('output_tokens', 0) for r in results)

            f.write(f"成功率: {success_count}/{len(results)}\n")
            f.write(f"总 Tokens: {total_input_tokens + total_output_tokens:,}\n")
            f.write(f"  - 输入: {total_input_tokens:,}\n")
            f.write(f"  - 输出: {total_output_tokens:,}\n\n")

            # 详细结果
            for idx, result in enumerate(results, 1):
                conv = result['conversation']
                extraction = result['extraction']
                error = result['error']

                f.write(f"\n--- 样本 #{idx}: {conv['conversation_name']} ---\n\n")

                if error:
                    f.write(f"❌ 提取失败: {error}\n")
                    continue

                # People
                people = extraction.get('people', []) if extraction else []
                f.write(f"人物 ({len(people)} 个):\n")
                for p in people:
                    f.write(f"  - {p.get('name', '?')} ({p.get('relationship', '?')})\n")
                    if p.get('occupation'):
                        f.write(f"    职业: {p['occupation']}\n")
                    if p.get('expertise'):
                        f.write(f"    擅长: {', '.join(p['expertise'])}\n")
                if not people:
                    f.write("  (无)\n")

                # Topics
                topics = extraction.get('topics', []) if extraction else []
                f.write(f"\n主题 ({len(topics)} 个):\n")
                for t in topics:
                    f.write(f"  - {t.get('name', '?')} ({t.get('type', '?')})\n")
                if not topics:
                    f.write("  (无)\n")

                # Events
                events = extraction.get('events', []) if extraction else []
                f.write(f"\n事件 ({len(events)} 个):\n")
                for e in events:
                    f.write(f"  - {e.get('name', '?')} ({e.get('type', '?')})\n")
                if not events:
                    f.write("  (无)\n")

                # Locations
                locations = extraction.get('locations', []) if extraction else []
                f.write(f"\n地点 ({len(locations)} 个):\n")
                for l in locations:
                    f.write(f"  - {l.get('name', '?')} ({l.get('type', '?')})\n")
                if not locations:
                    f.write("  (无)\n")

                f.write("\n")

    print(f"\n\n详细结果已保存到: {output_file}")

    # 保存汇总统计（JSON）
    summary_file = "knowledge_graph/model_comparison_summary.json"
    summary = {}

    for model_name, data in all_results.items():
        model_config = data['config']
        results = data['results']

        success_results = [r for r in results if not r['error']]

        # 统计提取的实体数量
        total_people = sum(len(r['extraction'].get('people', [])) for r in success_results if r['extraction'])
        total_topics = sum(len(r['extraction'].get('topics', [])) for r in success_results if r['extraction'])
        total_events = sum(len(r['extraction'].get('events', [])) for r in success_results if r['extraction'])
        total_locations = sum(len(r['extraction'].get('locations', [])) for r in success_results if r['extraction'])

        total_input_tokens = sum(r['usage'].get('input_tokens', 0) for r in results)
        total_output_tokens = sum(r['usage'].get('output_tokens', 0) for r in results)

        # 计算成本
        cost = (total_input_tokens / 1_000_000 * model_config['cost_input'] +
                total_output_tokens / 1_000_000 * model_config['cost_output'])

        summary[model_name] = {
            'display_name': model_config['display_name'],
            'success_rate': len(success_results) / len(results) if results else 0,
            'total_samples': len(results),
            'success_samples': len(success_results),
            'entities': {
                'people': total_people,
                'topics': total_topics,
                'events': total_events,
                'locations': total_locations,
                'total': total_people + total_topics + total_events + total_locations
            },
            'tokens': {
                'input': total_input_tokens,
                'output': total_output_tokens,
                'total': total_input_tokens + total_output_tokens
            },
            'cost': {
                'input_cost': total_input_tokens / 1_000_000 * model_config['cost_input'],
                'output_cost': total_output_tokens / 1_000_000 * model_config['cost_output'],
                'total_cost': cost
            },
            'avg_entities_per_conversation': (total_people + total_topics + total_events + total_locations) / len(success_results) if success_results else 0
        }

    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"汇总统计已保存到: {summary_file}")

    # 打印简要对比
    print("\n" + "=" * 100)
    print("简要对比")
    print("=" * 100)
    print(f"{'模型':<25} {'成功率':<10} {'总实体':<10} {'成本':<15} {'平均实体/对话':<15}")
    print("-" * 100)

    for model_name, stats in summary.items():
        print(f"{stats['display_name']:<25} "
              f"{stats['success_rate']*100:>6.1f}%   "
              f"{stats['entities']['total']:>8}   "
              f"${stats['cost']['total_cost']:>8.4f}      "
              f"{stats['avg_entities_per_conversation']:>8.1f}")

    print("\n" + "=" * 100)
    print("测试完成！请查看详细结果文件进行人工评估。")
    print("=" * 100)


if __name__ == "__main__":
    main()
