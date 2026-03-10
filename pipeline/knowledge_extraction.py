#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Knowledge Extraction Pipeline - COMPLETE IMPLEMENTATION

Uses Claude on Vertex AI to extract:
- Entities: People, Organizations, Topics, Events, Locations
- Relationships: Between all extracted entities
- Temporal information: Event timing and sequencing
"""
import sys
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pipeline.base import BasePipeline
from config.loader import load_config

# Vertex AI imports
from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel


# Complete extraction prompt
EXTRACTION_PROMPT = """你是一个知识图谱构建专家。请从以下微信对话中提取完整的结构化信息。

## 对话信息

对话名称: {conversation_name}
对话时间: {conversation_time}
对话类型: {conversation_type}
参与者: {participants}

## 对话内容

{conversation_text}

---

## 提取任务

请提取以下信息并返回 JSON 格式：

### 1. People（人物）⚠️ 重要
**提取所有人物**：
- 对话参与者：必须提取
- 提到的第三方人物：对话中提到的其他人

**命名规范（严格执行）**：
- 有明确姓名：直接用中文姓名（"张三"、"李四"、"Hunter"）
- 家人无姓名：必须用"XX的{{关系}}"格式（"张三的弟弟"、"用户的妈妈"）
- 复杂关系：逐级用"的"连接（"张三的弟弟的女朋友"）

**严格禁止提取**：
- 代词：他、她、某人、第三方
- 泛指：朋友、同事（单独出现时）
- 占位符：Unnamed Person、Person A

### 2. Organizations（组织/公司）
提取提到的公司、学校、政府机构等

### 3. Topics（主题）⚠️ 重要
**提取概括性主题，不提取具体细节**：
- ✅ 正确：讨论了5本编程书 → Topic: "技术书籍售卖"
- ❌ 错误：讨论了5本编程书 → 提取5个Topic（书名）
- ❌ 禁止：轻松幽默交流、友好沟通（氛围描述）

### 4. Events（事件）⚠️ 重要
**只提取有意义的活动，不提取聊天过程**：
- ✅ 提取：会议、聚会、旅游、重要决策、计划、项目讨论
- ❌ 不提取：发送消息、等待回复、打开文件等操作细节
- **必须填写participants字段**：包含所有参与此事件的Person名称

### 5. Locations（地点）
提取提到的地点（城市、餐厅、景点等）

### 6. Relationships（关系）⚠️ 重要
**必须完整提取**所有人物、组织、事件之间的关系

---

## 返回格式（必须是合法JSON）

{{
  "people": [
    {{
      "name": "姓名",
      "aliases": ["别名1", "别名2"],
      "relationship_to_user": "配偶/父母/子女/朋友/同事/客户/上级/下属/其他",
      "occupation": "职业或null",
      "company": "公司名或null",
      "expertise": ["擅长领域1"],
      "context": "提到此人的上下文（1-2句话）"
    }}
  ],

  "organizations": [
    {{
      "name": "组织名称",
      "type": "公司/学校/政府/医院/其他",
      "industry": "行业或null",
      "context": "提到此组织的上下文"
    }}
  ],

  "topics": [
    {{
      "name": "主题名称",
      "type": "工作项目/技术方案/家庭决策/旅游/健康/理财/兴趣爱好/学习/情感/其他",
      "keywords": ["关键词1", "关键词2"],
      "context": "讨论此主题的上下文"
    }}
  ],

  "events": [
    {{
      "name": "事件名称",
      "type": "会议/聚会/旅游/就医/购物/面试/考试/婚礼/生日/其他",
      "participants": ["参与者1", "参与者2"],
      "location": "地点或null",
      "description": "事件简短描述（1-2句话）",
      "time_reference": "past/present/future",
      "time_description": "对话中提到的时间表述（如：昨天、下周、去年10月）",
      "context": "提到此事件的上下文"
    }}
  ],

  "locations": [
    {{
      "name": "地点名称",
      "type": "城市/餐厅/景点/医院/公司/住址/学校/其他",
      "parent_location": "上级地点（如：北京市朝阳区）或null",
      "context": "提到此地点的上下文"
    }}
  ],

  "relationships": [
    {{
      "type": "关系类型",
      "source": "源实体名称",
      "source_type": "Person/Organization/Event",
      "target": "目标实体名称",
      "target_type": "Person/Organization/Location/Event/Topic",
      "context": "关系的上下文依据"
    }}
  ]
}}

## 关系类型说明

**人物关系**:
- KNOWS: (Person) 认识 (Person)
- FAMILY_OF: (Person) 和 (Person) 是家人
- WORKS_AT: (Person) 在 (Organization) 工作
- WORKS_WITH: (Person) 和 (Person) 是同事

**讨论关系**:
- DISCUSSED_WITH: (Person) 和 (Person) 讨论过某事
- DISCUSSED_TOPIC: (Person) 讨论过 (Topic)

**事件关系** ⚠️ 重要:
- PARTICIPATED_IN: (Person) 参与了 (Event)
  **规则**：Event的participants字段中的每个人，都必须创建一个PARTICIPATED_IN关系

**地点关系**:
- LIVES_IN: (Person) 居住在 (Location)
- HAPPENED_AT: (Event) 发生在 (Location)

**专长关系**:
- EXPERT_IN: (Person) 擅长 (Topic)

---

## 重要规则

1. **只提取明确提到的信息**，不要推测
2. **必须提取对话参与者**：如果对话名称是"张三"，那么"张三"必须被提取为 Person
3. **Event的participants必须完整**：
   - 每个Event必须在participants字段中列出所有参与者的名称
   - 名称必须和people数组中提取的name完全一致
   - 每个participant都需要在relationships中创建PARTICIPATED_IN关系
4. **Topics 概括性原则**：提取讨论方向，不提取具体条目或氛围
5. **People 命名规范（严格执行）**：
   - ✅ 正确格式：有明确姓名用中文姓名、家人无姓名用"XX的{{关系}}"（如："张三的妈妈"）
   - ❌ 严格禁止：代词、泛指、占位符、单独关系词
6. **Events 有意义原则**：只提取值得在时间线标注的事件
7. **Relationships 完整性原则**：不要遗漏关系，即使很明显也要明确提取
8. **如果某类实体为空，返回 []**
9. **务必返回合法的 JSON**：
    - 所有字符串必须在一对引号内
    - 不要有多余的文字、markdown标记

请开始提取：
"""


class KnowledgeExtractionPipeline(BasePipeline):
    """知识抽取 Pipeline - 完整实现"""

    def __init__(self, config=None, config_file: str = None, **kwargs):
        """初始化 Pipeline

        Args:
            config: 配置字典（可选）
            config_file: 配置文件路径（可选）
            **kwargs: 额外参数
        """
        # 加载配置
        if config is None:
            config = load_config(config_file)

        super().__init__(
            name="knowledge_extraction",
            config=config,
            **kwargs
        )

        self.config = config
        self.results = []

        # 设置路径
        self.input_dir = Path(config.get('paths', {}).get('cleaned_data', 'data/conversations/cleaned'))
        self.output_dir = Path(config.get('paths', {}).get('knowledge_graph', 'data/knowledge_graph'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 提取配置
        extraction_config = config.get('vertex_ai', {}).get('extraction', {})
        self.model_name = extraction_config.get('model', 'claude-3-5-sonnet-20241022')
        self.max_tokens = extraction_config.get('max_tokens', 8192)
        self.temperature = extraction_config.get('temperature', 0.0)
        self.max_retries = extraction_config.get('max_retries', 3)

        # 初始化 Vertex AI
        self._init_vertex_ai()

        print(f"[Knowledge Extraction Pipeline] 初始化完成")
        print(f"  输入目录: {self.input_dir}")
        print(f"  输出目录: {self.output_dir}")
        print(f"  模型: {self.model_name}")
        print(f"  最大Token: {self.max_tokens}")
        print(f"  温度: {self.temperature}")
        print(f"  最大重试: {self.max_retries}")

    def _init_vertex_ai(self):
        """初始化 Vertex AI"""
        import os

        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        region = os.getenv('GOOGLE_REGION', 'us-central1')

        # 获取凭证
        creds_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if creds_json:
            creds_dict = json.loads(creds_json)
            credentials = service_account.Credentials.from_service_account_info(creds_dict)
            vertexai.init(project=project_id, location=region, credentials=credentials)
        else:
            vertexai.init(project=project_id, location=region)

        print(f"[INFO] Vertex AI initialized: {project_id}, {region}")

    def get_items(self) -> List[Path]:
        """获取待处理的文件列表

        Returns:
            文件路径列表
        """
        if not self.input_dir.exists():
            print(f"[ERROR] 输入目录不存在: {self.input_dir}")
            return []

        items = list(self.input_dir.glob("*.json"))
        print(f"[Knowledge Extraction] 找到 {len(items)} 个对话文件")
        return items

    def _format_conversation(self, conversation: Dict) -> str:
        """格式化对话内容为文本

        Args:
            conversation: 对话数据

        Returns:
            格式化的对话文本
        """
        messages = conversation.get('messages', [])
        lines = []

        for msg in messages:
            sender = msg.get('accountName', msg.get('sender', 'Unknown'))
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')

            if isinstance(timestamp, (int, float)):
                dt = datetime.fromtimestamp(timestamp)
                time_str = dt.strftime('%Y-%m-%d %H:%M')
            else:
                time_str = str(timestamp)

            lines.append(f"[{time_str}] {sender}: {content}")

        return '\n'.join(lines)

    def _call_claude_extract(self, conversation: Dict, file_name: str) -> Dict:
        """调用 Claude 进行实体提取

        Args:
            conversation: 对话数据
            file_name: 文件名

        Returns:
            提取结果
        """
        # 格式化对话
        meta = conversation.get('meta', {})
        conversation_name = meta.get('name', file_name.replace('.json', ''))
        conversation_type = meta.get('type', 'unknown')

        # 提取参与者
        participants = set()
        for msg in conversation.get('messages', []):
            if 'sender' in msg:
                participants.add(msg['sender'])
            if 'accountName' in msg:
                participants.add(msg['accountName'])

        # 获取时间
        messages = conversation.get('messages', [])
        if messages:
            first_ts = messages[0].get('timestamp', 0)
            if isinstance(first_ts, (int, float)):
                conversation_time = datetime.fromtimestamp(first_ts).strftime('%Y年%m月%d日')
            else:
                conversation_time = '未知'
        else:
            conversation_time = '未知'

        conversation_text = self._format_conversation(conversation)

        # 构建提示
        prompt = EXTRACTION_PROMPT.format(
            conversation_name=conversation_name,
            conversation_time=conversation_time,
            conversation_type=conversation_type,
            participants=', '.join(participants) if participants else '未知',
            conversation_text=conversation_text
        )

        # 调用 Gemini
        model = GenerativeModel(self.model_name)

        try:
            start_time = time.time()

            response = model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": self.max_tokens,
                    "temperature": self.temperature
                }
            )

            duration = time.time() - start_time

            # 提取响应文本
            response_text = response.text.strip()

            # 清理 JSON（移除可能的 markdown 标记）
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            # 解析 JSON
            entities = json.loads(response_text)

            # 获取 token 使用情况
            usage = response.usage_metadata
            input_tokens = usage.prompt_token_count
            output_tokens = usage.candidates_token_count

            return {
                'success': True,
                'entities': entities,
                'metadata': {
                    'model': self.model_name,
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'duration_seconds': round(duration, 2),
                    'conversation_name': conversation_name
                },
                'error': None
            }

        except json.JSONDecodeError as e:
            return {
                'success': False,
                'entities': None,
                'metadata': None,
                'error': f'JSON解析错误: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'entities': None,
                'metadata': None,
                'error': f'提取失败: {str(e)}'
            }

    def _extract_with_retry(self, conversation: Dict, file_name: str) -> Dict:
        """带重试的提取

        Args:
            conversation: 对话数据
            file_name: 文件名

        Returns:
            提取结果
        """
        for attempt in range(self.max_retries):
            result = self._call_claude_extract(conversation, file_name)

            if result['success']:
                return result

            if attempt < self.max_retries - 1:
                print(f"  重试 {attempt + 1}/{self.max_retries - 1}...")
                time.sleep(2)  # 等待2秒后重试

        return result

    def process_item(self, item: Path) -> Dict[str, Any]:
        """处理单个对话文件

        Args:
            item: 对话文件路径

        Returns:
            处理结果字典
        """
        result = None
        try:
            # 加载对话数据
            with open(item, 'r', encoding='utf-8') as f:
                conversation = json.load(f)

            if not conversation or 'messages' not in conversation:
                result = {
                    'status': 'skipped',
                    'reason': 'invalid_format',
                    'file': item.name
                }
                self.results.append(result)
                return result

            print(f"\n[提取] {item.name}")

            # 调用 Claude 提取
            extraction_result = self._extract_with_retry(conversation, item.name)

            if not extraction_result['success']:
                print(f"  ❌ 提取失败: {extraction_result['error']}")
                result = {
                    'status': 'failed',
                    'file': item.name,
                    'error': extraction_result['error']
                }
                self.results.append(result)
                return result

            # 提取成功
            entities = extraction_result['entities']
            metadata = extraction_result['metadata']

            print(f"  ✅ 提取成功")
            print(f"    - People: {len(entities.get('people', []))}")
            print(f"    - Organizations: {len(entities.get('organizations', []))}")
            print(f"    - Topics: {len(entities.get('topics', []))}")
            print(f"    - Events: {len(entities.get('events', []))}")
            print(f"    - Locations: {len(entities.get('locations', []))}")
            print(f"    - Relationships: {len(entities.get('relationships', []))}")
            print(f"    - Tokens: {metadata['input_tokens']} in / {metadata['output_tokens']} out")
            print(f"    - Duration: {metadata['duration_seconds']}s")

            result = {
                'status': 'success',
                'file': item.name,
                'conversation_name': metadata['conversation_name'],
                'entities': entities,
                'token_usage': {
                    'input': metadata['input_tokens'],
                    'output': metadata['output_tokens']
                },
                'duration': metadata['duration_seconds']
            }

        except Exception as e:
            print(f"[ERROR] 处理文件失败 {item.name}: {e}")
            import traceback
            traceback.print_exc()
            result = {
                'status': 'failed',
                'file': item.name,
                'error': str(e)
            }

        self.results.append(result)
        return result

    def run(self, resume: bool = True, checkpoint_interval: int = 10):
        """运行 Pipeline 并调用 on_complete

        Args:
            resume: 是否从检查点恢复
            checkpoint_interval: 检查点保存间隔

        Returns:
            执行统计信息
        """
        # Run parent pipeline
        stats = super().run(resume=resume, checkpoint_interval=checkpoint_interval)

        # Call on_complete with results
        self.on_complete(self.results)

        return stats

    def on_complete(self, results: List[Dict[str, Any]]) -> None:
        """Pipeline 完成后的处理

        Args:
            results: 所有处理结果
        """
        # 统计
        success = sum(1 for r in results if r.get('status') == 'success')
        failed = sum(1 for r in results if r.get('status') == 'failed')
        skipped = sum(1 for r in results if r.get('status') == 'skipped')

        # 汇总所有实体
        all_people = []
        all_organizations = []
        all_topics = []
        all_events = []
        all_locations = []
        all_relationships = []

        total_input_tokens = 0
        total_output_tokens = 0
        total_duration = 0

        for r in results:
            if r.get('status') == 'success':
                entities = r.get('entities', {})

                # 为每个实体添加来源信息
                for person in entities.get('people', []):
                    person['source_conversation'] = r['conversation_name']
                    person['source_file'] = r['file']
                    all_people.append(person)

                for org in entities.get('organizations', []):
                    org['source_conversation'] = r['conversation_name']
                    org['source_file'] = r['file']
                    all_organizations.append(org)

                for topic in entities.get('topics', []):
                    topic['source_conversation'] = r['conversation_name']
                    topic['source_file'] = r['file']
                    all_topics.append(topic)

                for event in entities.get('events', []):
                    event['source_conversation'] = r['conversation_name']
                    event['source_file'] = r['file']
                    all_events.append(event)

                for location in entities.get('locations', []):
                    location['source_conversation'] = r['conversation_name']
                    location['source_file'] = r['file']
                    all_locations.append(location)

                for rel in entities.get('relationships', []):
                    rel['source_conversation'] = r['conversation_name']
                    rel['source_file'] = r['file']
                    all_relationships.append(rel)

                # 累计token使用
                token_usage = r.get('token_usage', {})
                total_input_tokens += token_usage.get('input', 0)
                total_output_tokens += token_usage.get('output', 0)
                total_duration += r.get('duration', 0)

        print(f"\n{'='*70}")
        print(f"知识抽取统计")
        print(f"{'='*70}")
        print(f"总对话数: {len(results)}")
        print(f"处理成功: {success}")
        print(f"处理失败: {failed}")
        print(f"跳过: {skipped}")
        print()
        print(f"提取结果:")
        print(f"  - People: {len(all_people)}")
        print(f"  - Organizations: {len(all_organizations)}")
        print(f"  - Topics: {len(all_topics)}")
        print(f"  - Events: {len(all_events)}")
        print(f"  - Locations: {len(all_locations)}")
        print(f"  - Relationships: {len(all_relationships)}")
        print()
        print(f"Token 使用:")
        print(f"  - Input: {total_input_tokens:,}")
        print(f"  - Output: {total_output_tokens:,}")
        print(f"  - Total: {total_input_tokens + total_output_tokens:,}")
        print(f"  - Duration: {total_duration:.2f}s")

        # 保存知识图谱
        if success > 0:
            knowledge_graph = {
                'people': all_people,
                'organizations': all_organizations,
                'topics': all_topics,
                'events': all_events,
                'locations': all_locations,
                'relationships': all_relationships,
                'metadata': {
                    'total_conversations': success,
                    'total_entities': len(all_people) + len(all_organizations) + len(all_topics) + len(all_events) + len(all_locations),
                    'total_relationships': len(all_relationships),
                    'extraction_model': self.model_name,
                    'total_input_tokens': total_input_tokens,
                    'total_output_tokens': total_output_tokens,
                    'extraction_time': datetime.now().isoformat()
                }
            }

            output_file = self.output_dir / "curated_kg.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(knowledge_graph, f, ensure_ascii=False, indent=2)

            print(f"\n[Knowledge Extraction] 保存知识图谱...")
            print(f"  输出文件: {output_file}")
            print(f"  ✅ 知识图谱已保存")
        else:
            print(f"\n[WARNING] 没有成功处理任何对话，跳过保存")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Knowledge Extraction Pipeline")
    parser.add_argument('--config', type=str, help='配置文件路径')
    parser.add_argument('--fresh', action='store_true', help='从头开始（清除检查点）')

    args = parser.parse_args()

    # 创建并运行 Pipeline
    pipeline = KnowledgeExtractionPipeline(config_file=args.config)
    pipeline.run(resume=not args.fresh)


if __name__ == "__main__":
    main()
