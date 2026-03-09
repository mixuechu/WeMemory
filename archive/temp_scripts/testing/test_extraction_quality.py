#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实体提取质量测试 - 人工评估

随机抽取对话，用 Gemini Flash 提取实体，展示结果供人工评估
"""
import sys
import os
import json
import pickle
import random
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

# Google Vertex AI
import vertexai
from vertexai.generative_models import GenerativeModel

# 初始化 Vertex AI
project_id = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
credentials_json = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

if credentials_json:
    import json
    import tempfile
    from google.oauth2 import service_account

    creds_dict = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(creds_dict)
    vertexai.init(project=project_id, credentials=credentials)
else:
    vertexai.init(project=project_id)


class ExtractionTester:
    """实体提取测试器"""

    def __init__(self, model_name: str = "gemini-2.0-flash-exp"):
        self.model = GenerativeModel(model_name)
        self.model_name = model_name

    def load_sample_conversations(self, vector_store_path: str, sample_size: int = 20) -> List[Dict]:
        """加载样本对话"""
        print(f"加载向量库: {vector_store_path}")

        with open(vector_store_path, 'rb') as f:
            data = pickle.load(f)

        metadata = data.get('metadata', [])
        print(f"总共 {len(metadata)} 个记忆片段")

        # 随机抽取
        samples = random.sample(metadata, min(sample_size, len(metadata)))

        # 按对话名称分组（避免碎片）
        conversations = {}
        for item in samples:
            conv_name = item.get('conversation_name', 'Unknown')
            if conv_name not in conversations:
                conversations[conv_name] = {
                    'conversation_name': conv_name,
                    'messages': []
                }
            conversations[conv_name]['messages'].append(item)

        # 转换为列表
        conv_list = list(conversations.values())

        # 只保留消息数量适中的（3-15条，太短没意义，太长看不过来）
        conv_list = [c for c in conv_list if 3 <= len(c['messages']) <= 15]

        # 排序并取前N个
        conv_list.sort(key=lambda x: len(x['messages']), reverse=True)
        conv_list = conv_list[:10]  # 只取10个对话，方便人工评估

        print(f"抽取 {len(conv_list)} 个对话用于测试")
        return conv_list

    def extract_entities(self, conversation: Dict) -> Dict[str, Any]:
        """使用 Gemini Flash 提取实体"""

        # 构建对话文本
        messages = conversation['messages']
        conversation_text = self._build_conversation_text(messages)

        # 提取 Prompt
        prompt = self._build_extraction_prompt(conversation_text, conversation['conversation_name'])

        # 调用 LLM
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text

            # 解析 JSON
            # 去掉 markdown 代码块标记
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            result = json.loads(result_text.strip())
            return result

        except Exception as e:
            print(f"提取失败: {e}")
            return {"error": str(e)}

    def _build_conversation_text(self, messages: List[Dict]) -> str:
        """构建对话文本"""
        lines = []
        for msg in messages:
            sender = msg.get('sender', 'Unknown')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', 0)

            # 格式化时间
            from datetime import datetime
            time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')

            lines.append(f"[{time_str}] {sender}: {content}")

        return "\n".join(lines)

    def _build_extraction_prompt(self, conversation_text: str, conversation_name: str) -> str:
        """构建提取 Prompt"""
        return f"""你是一个信息提取专家。请从以下微信对话中提取结构化信息。

对话名称: {conversation_name}

对话内容:
{conversation_text}

请提取以下信息（返回 JSON 格式）:

{{
  "people": [
    {{
      "name": "人物姓名",
      "aliases": ["别名1", "别名2"],
      "relationship": "与用户的关系（配偶/父母/子女/朋友/同事/客户/其他）",
      "occupation": "职业（如果提到）",
      "company": "公司（如果提到）",
      "personality": ["性格特征1", "性格特征2"],
      "interests": ["兴趣1", "兴趣2"],
      "expertise": ["擅长领域1", "擅长领域2"],
      "confidence": 0.9
    }}
  ],
  "topics": [
    {{
      "name": "主题名称",
      "type": "工作项目/技术方案/家庭决策/旅游计划/健康管理/理财投资/兴趣爱好/其他",
      "keywords": ["关键词1", "关键词2"],
      "confidence": 0.85
    }}
  ],
  "events": [
    {{
      "name": "事件名称",
      "type": "会议/聚会/旅游/就医/购物/活动/其他",
      "time": "2024-01-15 或 null（如果未提到具体时间）",
      "participants": ["参与者1", "参与者2"],
      "location": "地点（如果提到）",
      "description": "简短描述",
      "confidence": 0.8
    }}
  ],
  "locations": [
    {{
      "name": "地点名称",
      "type": "餐厅/景点/医院/公司/住址/其他",
      "address": "详细地址（如果提到）",
      "notes": "备注（如推荐原因等）",
      "confidence": 0.75
    }}
  ]
}}

注意：
1. 只提取明确提到的信息，不确定的字段填 null
2. 不要把"我"作为 Person 实体（我是用户本人）
3. confidence 表示你对提取结果的信心（0-1）
4. 如果对话中没有某类实体，返回空数组 []
5. 务必返回合法的 JSON 格式
"""

    def display_result(self, idx: int, conversation: Dict, extraction: Dict):
        """展示提取结果供人工评估"""
        print("\n" + "=" * 100)
        print(f"【测试样本 #{idx+1}】")
        print("=" * 100)

        # 1. 显示原始对话
        print("\n【原始对话】")
        print(f"对话名称: {conversation['conversation_name']}")
        print(f"消息数量: {len(conversation['messages'])}")
        print("\n对话内容:")
        print("-" * 80)

        for msg in conversation['messages']:
            sender = msg.get('sender', 'Unknown')
            content = msg.get('content', '')
            from datetime import datetime
            time_str = datetime.fromtimestamp(msg.get('timestamp', 0)).strftime('%m-%d %H:%M')
            print(f"[{time_str}] {sender}: {content}")

        print("-" * 80)

        # 2. 显示提取结果
        print("\n【提取结果】")

        if "error" in extraction:
            print(f"❌ 提取失败: {extraction['error']}")
            return

        # People
        people = extraction.get('people', [])
        if people:
            print(f"\n人物实体 ({len(people)} 个):")
            for i, p in enumerate(people, 1):
                print(f"  {i}. {p.get('name', 'Unknown')}")
                if p.get('aliases'):
                    print(f"     别名: {', '.join(p['aliases'])}")
                if p.get('relationship'):
                    print(f"     关系: {p['relationship']}")
                if p.get('occupation'):
                    print(f"     职业: {p['occupation']}")
                if p.get('company'):
                    print(f"     公司: {p['company']}")
                if p.get('personality'):
                    print(f"     性格: {', '.join(p['personality'])}")
                if p.get('interests'):
                    print(f"     兴趣: {', '.join(p['interests'])}")
                if p.get('expertise'):
                    print(f"     擅长: {', '.join(p['expertise'])}")
                print(f"     置信度: {p.get('confidence', 0)}")
        else:
            print("\n人物实体: (无)")

        # Topics
        topics = extraction.get('topics', [])
        if topics:
            print(f"\n主题 ({len(topics)} 个):")
            for i, t in enumerate(topics, 1):
                print(f"  {i}. {t.get('name', 'Unknown')} ({t.get('type', 'Unknown')})")
                if t.get('keywords'):
                    print(f"     关键词: {', '.join(t['keywords'])}")
                print(f"     置信度: {t.get('confidence', 0)}")
        else:
            print("\n主题: (无)")

        # Events
        events = extraction.get('events', [])
        if events:
            print(f"\n事件 ({len(events)} 个):")
            for i, e in enumerate(events, 1):
                print(f"  {i}. {e.get('name', 'Unknown')} ({e.get('type', 'Unknown')})")
                if e.get('time'):
                    print(f"     时间: {e['time']}")
                if e.get('participants'):
                    print(f"     参与者: {', '.join(e['participants'])}")
                if e.get('location'):
                    print(f"     地点: {e['location']}")
                if e.get('description'):
                    print(f"     描述: {e['description']}")
                print(f"     置信度: {e.get('confidence', 0)}")
        else:
            print("\n事件: (无)")

        # Locations
        locations = extraction.get('locations', [])
        if locations:
            print(f"\n地点 ({len(locations)} 个):")
            for i, l in enumerate(locations, 1):
                print(f"  {i}. {l.get('name', 'Unknown')} ({l.get('type', 'Unknown')})")
                if l.get('address'):
                    print(f"     地址: {l['address']}")
                if l.get('notes'):
                    print(f"     备注: {l['notes']}")
                print(f"     置信度: {l.get('confidence', 0)}")
        else:
            print("\n地点: (无)")

        print("\n" + "=" * 100)


def main():
    """主测试流程"""
    print("\n" + "=" * 100)
    print("Gemini Flash 实体提取质量测试")
    print("=" * 100)

    # 配置
    vector_store_path = "vector_stores/conversations_complete.pkl"
    sample_size = 50  # 先抽取 50 个片段，组合成 ~10 个对话

    print(f"\n模型: gemini-2.0-flash-exp")
    print(f"向量库: {vector_store_path}")
    print(f"样本量: 随机抽取，最终评估约 10 个对话")

    # 初始化测试器
    tester = ExtractionTester()

    # 加载样本
    print("\n" + "-" * 100)
    conversations = tester.load_sample_conversations(vector_store_path, sample_size)

    print(f"\n将测试 {len(conversations)} 个对话")

    # 开始测试
    print("\n开始提取实体...")

    results = []

    for idx, conv in enumerate(conversations):
        print(f"处理 [{idx+1}/{len(conversations)}]...", end=" ", flush=True)

        extraction = tester.extract_entities(conv)

        if "error" not in extraction:
            print("OK")
        else:
            print("FAIL")

        results.append({
            'conversation': conv,
            'extraction': extraction
        })

    # 保存详细结果到文本文件（供人工查看）
    output_txt = "knowledge_graph/extraction_test_results.txt"
    with open(output_txt, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("Gemini Flash 实体提取质量测试结果\n")
        f.write("=" * 100 + "\n\n")

        for idx, result in enumerate(results):
            conv = result['conversation']
            extraction = result['extraction']

            f.write("\n" + "=" * 100 + "\n")
            f.write(f"【测试样本 #{idx+1}】\n")
            f.write("=" * 100 + "\n\n")

            # 原始对话
            f.write("【原始对话】\n")
            f.write(f"对话名称: {conv['conversation_name']}\n")
            f.write(f"消息数量: {len(conv['messages'])}\n\n")
            f.write("对话内容:\n")
            f.write("-" * 80 + "\n")

            for msg in conv['messages']:
                sender = msg.get('sender', 'Unknown')
                content = msg.get('content', '')
                from datetime import datetime
                time_str = datetime.fromtimestamp(msg.get('timestamp', 0)).strftime('%m-%d %H:%M')
                f.write(f"[{time_str}] {sender}: {content}\n")

            f.write("-" * 80 + "\n\n")

            # 提取结果
            f.write("【提取结果】\n\n")

            if "error" in extraction:
                f.write(f"❌ 提取失败: {extraction['error']}\n")
                continue

            # People
            people = extraction.get('people', [])
            if people:
                f.write(f"人物实体 ({len(people)} 个):\n")
                for i, p in enumerate(people, 1):
                    f.write(f"  {i}. {p.get('name', 'Unknown')}\n")
                    if p.get('aliases'):
                        f.write(f"     别名: {', '.join(p['aliases'])}\n")
                    if p.get('relationship'):
                        f.write(f"     关系: {p['relationship']}\n")
                    if p.get('occupation'):
                        f.write(f"     职业: {p['occupation']}\n")
                    if p.get('company'):
                        f.write(f"     公司: {p['company']}\n")
                    if p.get('personality'):
                        f.write(f"     性格: {', '.join(p['personality'])}\n")
                    if p.get('interests'):
                        f.write(f"     兴趣: {', '.join(p['interests'])}\n")
                    if p.get('expertise'):
                        f.write(f"     擅长: {', '.join(p['expertise'])}\n")
                    f.write(f"     置信度: {p.get('confidence', 0)}\n")
            else:
                f.write("人物实体: (无)\n")

            # Topics
            topics = extraction.get('topics', [])
            if topics:
                f.write(f"\n主题 ({len(topics)} 个):\n")
                for i, t in enumerate(topics, 1):
                    f.write(f"  {i}. {t.get('name', 'Unknown')} ({t.get('type', 'Unknown')})\n")
                    if t.get('keywords'):
                        f.write(f"     关键词: {', '.join(t['keywords'])}\n")
                    f.write(f"     置信度: {t.get('confidence', 0)}\n")
            else:
                f.write("\n主题: (无)\n")

            # Events
            events = extraction.get('events', [])
            if events:
                f.write(f"\n事件 ({len(events)} 个):\n")
                for i, e in enumerate(events, 1):
                    f.write(f"  {i}. {e.get('name', 'Unknown')} ({e.get('type', 'Unknown')})\n")
                    if e.get('time'):
                        f.write(f"     时间: {e['time']}\n")
                    if e.get('participants'):
                        f.write(f"     参与者: {', '.join(e['participants'])}\n")
                    if e.get('location'):
                        f.write(f"     地点: {e['location']}\n")
                    if e.get('description'):
                        f.write(f"     描述: {e['description']}\n")
                    f.write(f"     置信度: {e.get('confidence', 0)}\n")
            else:
                f.write("\n事件: (无)\n")

            # Locations
            locations = extraction.get('locations', [])
            if locations:
                f.write(f"\n地点 ({len(locations)} 个):\n")
                for i, l in enumerate(locations, 1):
                    f.write(f"  {i}. {l.get('name', 'Unknown')} ({l.get('type', 'Unknown')})\n")
                    if l.get('address'):
                        f.write(f"     地址: {l['address']}\n")
                    if l.get('notes'):
                        f.write(f"     备注: {l['notes']}\n")
                    f.write(f"     置信度: {l.get('confidence', 0)}\n")
            else:
                f.write("\n地点: (无)\n")

            f.write("\n")

    # 也保存 JSON 格式
    output_json = "knowledge_graph/extraction_test_results.json"
    with open(output_json, 'w', encoding='utf-8') as f:
        # 简化保存（不保存完整对话，太大）
        simplified = []
        for r in results:
            simplified.append({
                'conversation_name': r['conversation']['conversation_name'],
                'message_count': len(r['conversation']['messages']),
                'extraction': r['extraction']
            })
        json.dump(simplified, f, ensure_ascii=False, indent=2)

    print(f"\n\n详细结果已保存到: {output_txt}")
    print(f"JSON 结果已保存到: {output_json}")
    print("\n请打开文本文件查看详细提取结果并人工评估质量。")
    print("\n请人工评估以上提取结果，评估维度：")
    print("1. 人物识别准确率")
    print("2. 关系类型准确率")
    print("3. 主题提取准确率")
    print("4. 事件识别准确率")
    print("5. 地点提取准确率")
    print("6. 遗漏率（应该提取但没提取的）")
    print("7. 错误率（提取错误或幻觉的）")
    print("\n总体评估：Flash 模型是否足够用于实体提取？")
    print("=" * 100)


if __name__ == "__main__":
    main()
