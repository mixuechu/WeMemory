#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude 4.5 实体提取质量测试
"""
import sys
import os
import json
import pickle
import random
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

import anthropic


def load_test_conversations(vector_store_path: str, count: int = 10):
    """加载测试对话"""
    with open(vector_store_path, 'rb') as f:
        data = pickle.load(f)

    metadata = data.get('metadata', [])

    # 按对话分组
    conversations = {}
    for item in metadata:
        content = item.get('content_text', '')
        if not content or len(content) < 20:
            continue

        conv_name = item.get('conversation_name', 'Unknown')
        if conv_name not in conversations:
            conversations[conv_name] = []
        conversations[conv_name].append(item)

    # 选择5-12条消息的对话
    suitable = []
    for conv_name, sessions in conversations.items():
        if 5 <= len(sessions) <= 12:
            suitable.append({
                'conversation_name': conv_name,
                'sessions': sessions
            })

    # 随机选择
    selected = random.sample(suitable, min(count, len(suitable)))
    return selected


def extract_entities(conversation: dict, client: anthropic.Anthropic, model: str) -> dict:
    """使用Claude提取实体"""
    # 构建对话文本
    conversation_text = ""
    for session in conversation['sessions']:
        content = session.get('content_text', '')
        conversation_text += f"{content}\n\n"

    # Prompt
    prompt = f"""你是一个信息提取专家。请从以下微信对话中提取结构化信息。

对话名称: {conversation['conversation_name']}

对话内容:
{conversation_text[:4000]}

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
5. 务必返回合法JSON，不要有其他说明文字"""

    try:
        message = client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        result_text = message.content[0].text

        # 解析JSON
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]

        result = json.loads(result_text.strip())
        return result
    except Exception as e:
        return {"error": str(e)}


def main():
    """主流程"""
    print("=" * 80)
    print("Claude 4.5 实体提取质量测试")
    print("=" * 80)

    # 初始化Claude客户端
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("错误: 缺少 ANTHROPIC_API_KEY 环境变量")
        print("请在.env文件中添加: ANTHROPIC_API_KEY=your-api-key")
        return

    client = anthropic.Anthropic(api_key=api_key)
    model = "claude-sonnet-4-5-20250926"  # 最新的Sonnet 4.5
    print(f"模型: {model}")

    # 加载测试对话
    print("\n加载测试对话...")
    conversations = load_test_conversations("vector_stores/conversations_complete.pkl", count=10)
    print(f"已加载 {len(conversations)} 个对话")

    # 提取
    print("\n开始提取...")
    results = []

    for idx, conv in enumerate(conversations):
        print(f"  [{idx+1}/{len(conversations)}]...", end=" ", flush=True)

        extraction = extract_entities(conv, client, model)

        if "error" not in extraction:
            print("OK")
        else:
            print(f"FAIL")

        results.append({
            'conversation': conv,
            'extraction': extraction
        })

    # 保存结果
    output_file = "knowledge_graph/claude_extraction_results.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("Claude Sonnet 4.5 实体提取质量测试\n")
        f.write("=" * 100 + "\n\n")

        for idx, result in enumerate(results):
            conv = result['conversation']
            extraction = result['extraction']

            f.write("\n" + "=" * 100 + "\n")
            f.write(f"【样本 #{idx+1}】\n")
            f.write("=" * 100 + "\n\n")

            # 对话信息
            f.write(f"对话名称: {conv['conversation_name']}\n")
            f.write(f"会话数: {len(conv['sessions'])}\n\n")

            # 对话内容
            f.write("【对话内容】\n")
            f.write("-" * 80 + "\n")
            for session in conv['sessions']:
                content = session.get('content_text', '')
                f.write(content[:500] + "...\n\n" if len(content) > 500 else content + "\n\n")
            f.write("-" * 80 + "\n\n")

            # 提取结果
            f.write("【提取结果】\n\n")

            if "error" in extraction:
                f.write(f"❌ 提取失败: {extraction['error']}\n")
                continue

            # People
            people = extraction.get('people', [])
            f.write(f"人物 ({len(people)} 个):\n")
            for i, p in enumerate(people, 1):
                f.write(f"  {i}. {p.get('name', '?')}\n")
                f.write(f"     关系: {p.get('relationship', '?')}\n")
                if p.get('occupation'):
                    f.write(f"     职业: {p['occupation']}\n")
                if p.get('company'):
                    f.write(f"     公司: {p['company']}\n")
                if p.get('personality'):
                    f.write(f"     性格: {', '.join(p['personality'])}\n")
                if p.get('expertise'):
                    f.write(f"     擅长: {', '.join(p['expertise'])}\n")
                f.write(f"     置信度: {p.get('confidence', 0)}\n")
            if not people:
                f.write("  (无)\n")

            # Topics
            topics = extraction.get('topics', [])
            f.write(f"\n主题 ({len(topics)} 个):\n")
            for i, t in enumerate(topics, 1):
                f.write(f"  {i}. {t.get('name', '?')} ({t.get('type', '?')})\n")
                if t.get('keywords'):
                    f.write(f"     关键词: {', '.join(t['keywords'])}\n")
                f.write(f"     置信度: {t.get('confidence', 0)}\n")
            if not topics:
                f.write("  (无)\n")

            # Events
            events = extraction.get('events', [])
            f.write(f"\n事件 ({len(events)} 个):\n")
            for i, e in enumerate(events, 1):
                f.write(f"  {i}. {e.get('name', '?')} ({e.get('type', '?')})\n")
                if e.get('participants'):
                    f.write(f"     参与者: {', '.join(e['participants'])}\n")
                if e.get('description'):
                    f.write(f"     描述: {e['description']}\n")
                f.write(f"     置信度: {e.get('confidence', 0)}\n")
            if not events:
                f.write("  (无)\n")

            # Locations
            locations = extraction.get('locations', [])
            f.write(f"\n地点 ({len(locations)} 个):\n")
            for i, l in enumerate(locations, 1):
                f.write(f"  {i}. {l.get('name', '?')} ({l.get('type', '?')})\n")
                if l.get('notes'):
                    f.write(f"     备注: {l['notes']}\n")
                f.write(f"     置信度: {l.get('confidence', 0)}\n")
            if not locations:
                f.write("  (无)\n")

            f.write("\n")

    print(f"\n结果已保存到: {output_file}")
    print("\n请打开文件查看详细结果并人工评估质量。")
    print("=" * 80)


if __name__ == "__main__":
    main()
