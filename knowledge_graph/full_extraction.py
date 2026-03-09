#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整知识图谱实体提取系统
- 提取实体（People, Topics, Events, Locations）
- 提取关系（WORKS_AT, PARTICIPATED_IN, VISITED, etc.）
- 保存对话时间和上下文
- 每条对话保存为一个 JSON 文件
"""

import os
import sys
import io
import json
import pickle
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

load_dotenv()

from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel

# 配置
PROJECT_ID = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
credentials_json = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

creds_dict = json.loads(credentials_json)
credentials = service_account.Credentials.from_service_account_info(creds_dict)
vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

# 路径配置
VECTOR_STORE_PATH = "vector_stores/conversations_complete.pkl"
OUTPUT_DIR = Path("extractions")
OUTPUT_DIR.mkdir(exist_ok=True)

# 提取配置
MODEL_NAME = "gemini-2.5-flash"
MAX_OUTPUT_TOKENS = 16000  # 增加到16000，防止输出被截断
MAX_RETRIES = 2
PARALLEL_WORKERS = 20

# 成本配置（$/1M tokens）
COST_INPUT = 0.075
COST_OUTPUT = 0.30

# 黑名单：已删除的群聊
BLACKLIST = [
    "🦄 西安留学生聚集地™🗿②",
    "📍XA留学生活动中心3⃣️群🌟",
    "鹏程.盘古α技术交流群①",
    "多伦多租房＋闲置群🇨🇦",
    "📍XA留学生活动中心2⃣️群💫",
    "二手家具5️⃣",
    "警民共建金水湾网格管理群",
    "租房群-13",
    "DT租房群",
    "停车群",
    "姜溪花都4号楼业主群",
    "多伦多区块链六群",
    "Cursor 号池105会员群",
    "大二～大三课本交易1️⃣",
    "GTA二手闲置租房求职考证互助群",
    "VIP 2群|一支烟花AI社区",
    "一支烟花AI 广州社区",
    "GAIDN广州AI社群",
    "Austin 的 AI 产品交流群",
    "628～29深圳站→已报名朋友进群",
    "河津年轻人创业交流群",
    "牛米之 🏠，平安永远"
]


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
- 米雪川/我：如果米雪川参与对话，必须提取（标记 is_user: true）
- 对话参与者：如果对话名称是"张三"，必须提取"张三"
- 提到的第三方人物：对话中提到的其他人

**⚠️ 命名规范（严格执行，避免错误合并）**：

**✅ 正确格式：**
- 有明确姓名：直接用中文姓名（"张三"、"李四"、"Hunter"）
- 家人无姓名：必须用"XX的{关系}"格式（"吉月的弟弟"、"米雪川的妈妈"）
- 复杂关系：逐级用"的"连接（"吉月的弟弟的女朋友"、"张三的妈妈的姐姐"）
- 间接关系：完整表达（"吉月的阿姨的姥姥"，不能写"吉月姨的姥姥"）

**❌ 严格禁止提取（会被删除）：**

**1. 代词和泛指词**：
- 代词：他、她、你、我、他们、她们、人家、别人、有人、谁、那个人
- 泛指：某人、某女士、某男士、某个人、某位、第三方、第三方人物、未知人物、匿名人士
- 描述性泛指：对话中的对方、那位朋友、某个同事、那个同学、某位亲戚、一个朋友

**2. 占位符和无意义标识**：
- 英文占位符：Unnamed Person、Unnamed Male、Unnamed Female、Someone、Person A、Person B
- 中文占位符：无名氏、不明人士、未指明人物、神秘人、匿名者
- 带编号：朋友A、朋友B、同学A、室友A、女性A、男士B（永远不要用编号区分人）

**3. 泛指关系词**：
- 亲戚、家人、爱人、对象、男友、女友、恋人（太模糊无法区分具体是谁）
- 朋友、同事、同学、室友、老师、医生、律师、司机（缺少所属者时不提取）

**4. 单独关系词（缺少所属者）**：
- 弟弟、妈妈、我弟、我妈、他妈、她弟（必须写成"XX的妈妈"）
- 老板、上司、下属、员工、客户、合作方（单独出现时不提取）

**5. 格式错误**：
- 英文格式：吉月's mother、吉月's Mom、mother、brother
- 异常标点：吉月.的妈妈、吉月_的妈妈、吉月之弟弟、吉月她的妈妈
- 缺"的"连接：吉月母亲、吉月儿子、吉月弟弟（必须是"吉月的母亲"）
- 同义词混用：母亲、父亲、brother、sister（统一用：妈妈、爸爸、弟弟、姐姐）

**负样本示例（这些都不要提取）**：
```
❌ 代词泛指：她、他、某人、第三方、那个人、有人、别人、人家
❌ 描述性：对话中的对方、某位同事、那位朋友、一个女性、某个男的、不知道谁
❌ 占位符：Unnamed Male、Person A、朋友B、无名氏、匿名人士、第三方女士
❌ 单独关系词：朋友、同事、老师、医生、妈妈、弟弟、老板、客户
❌ 格式错误：吉月mother、我妈、他弟、吉月儿子、张三's sister
```

**正确示例对比：**
```
✅ 正确：吉月的妈妈、米雪川的弟弟、张三的弟弟的女朋友、吉月的阿姨的姥姥、Hunter、李明
❌ 错误：妈妈、我妈、吉月母亲、吉月's mother、吉月姨的姥姥、他、某人、对话中的对方、朋友A
```

### 2. Organizations（组织/公司）
提取提到的公司、学校、政府机构等

### 3. Topics（主题）⚠️ 重要
**提取概括性主题，不提取具体细节**：
- ✅ 提取讨论的方向、领域（如："技术书籍售卖"、"职业规划"、"前端开发"）
- ❌ 不提取具体条目（如：每本书名、具体技术栈版本、餐厅名）
- ❌ **禁止提取氛围、情绪类**（如："轻松幽默交流"、"友好沟通"、"愉快聊天"）
- **原则**: 图谱记录"讨论了什么方向"，细节由向量库负责
- **示例**:
  - ✅ 讨论了5本编程书 → Topic: "编程书籍售卖"
  - ❌ 对话很轻松愉快 → 不提取（这是氛围不是主题）

### 4. Events（事件）⚠️ 重要
**只提取有意义的活动，不提取聊天过程**：
- ✅ 提取：会议、聚会、旅游、重要决策、计划、项目讨论
- ❌ 不提取：发送消息、等待回复、打开文件、查看照片等操作细节
- **判断标准**: 这件事值得在时间线上标注吗？如果只是聊天过程，不提取

**⚠️ 必须填写participants字段**：
- participants必须包含所有参与此事件的Person名称
- 示例："JY和米雪川参加了聚会" → participants: ["JY", "米雪川"]
- 即使只有一个人参与也要填写
- **每个participant都会自动建立PARTICIPATED_IN关系**

### 5. Locations（地点）
提取提到的地点（城市、餐厅、景点等）

### 6. Relationships（关系）⚠️ 重要
**必须完整提取**所有人物、组织、事件之间的关系
不要遗漏关系，即使很明显也要明确提取

---

## 返回格式（必须是合法JSON）

{{
  "people": [
    {{
      "name": "姓名",
      "is_user": false,
      "aliases": ["别名1", "别名2"],
      "relationship_to_user": "配偶/父母/子女/朋友/同事/客户/上级/下属/自己/其他",
      "occupation": "职业或null",
      "company": "公司名或null",
      "expertise": ["擅长领域1", "擅长领域2"],
      "personality": ["性格特征"],
      "disambiguation_hints": {{
        "co_occurs_with": ["经常一起出现的人名"],
        "distinctive_features": "区分性特征（如：阿里的算法工程师）"
      }},
      "confidence": 0.9,
      "context": "提到此人的上下文（1-2句话）"
    }}
  ],

  说明：
  - name: 人物姓名
  - 如果 name 是"米雪川"或对话中的"我"，设置 is_user: true, relationship_to_user: "自己"
  - 其他人设置 is_user: false
  - aliases: 提取对话中对该人的所有称呼（如：["老张", "张工", "张三"]）
  - disambiguation_hints: 帮助区分重名的人（co_occurs_with: 常一起出现的人；distinctive_features: 独特特征）

  "organizations": [
    {{
      "name": "组织名称",
      "type": "公司/学校/政府/医院/其他",
      "industry": "行业或null",
      "confidence": 0.85,
      "context": "提到此组织的上下文"
    }}
  ],

  "topics": [
    {{
      "name": "主题名称",
      "type": "工作项目/技术方案/家庭决策/旅游/健康/理财/兴趣爱好/学习/情感/其他",
      "keywords": ["关键词1", "关键词2"],
      "confidence": 0.8,
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
      "inferred_time": "推断的绝对时间（如：2019-10、2019-11-15、2019-W45），null表示无法推断",
      "time_precision": "时间精度：year/month/week/day/hour，null表示无法推断",
      "confidence": 0.85,
      "context": "提到此事件的上下文"
    }}
  ],

  "locations": [
    {{
      "name": "地点名称",
      "type": "城市/餐厅/景点/医院/公司/住址/学校/其他",
      "parent_location": "上级地点（如：北京->朝阳区->五道口）或null",
      "notes": "补充说明",
      "confidence": 0.75,
      "context": "提到此地点的上下文"
    }}
  ],

  "relationships": [
    {{
      "type": "关系类型（见下方说明）",
      "source": "源实体名称",
      "source_type": "Person/Organization/Event",
      "target": "目标实体名称",
      "target_type": "Person/Organization/Location/Event/Topic",
      "properties": {{}},
      "confidence": 0.9,
      "context": "关系的上下文依据"
    }}
  ]
}}

## 关系类型说明（精简版，只提取核心关系）

**人物关系**:
- KNOWS: (Person) 认识 (Person)
- FAMILY_OF: (Person) 和 (Person) 是家人
- WORKS_AT: (Person) 在 (Organization) 工作

**讨论关系**（高层次，替代大量Event关系）:
- DISCUSSED_WITH: (Person) 和 (Person) 讨论过某事
  示例：type: "DISCUSSED_WITH", source: "米雪川", target: "1900", properties: {{{{topic: "书籍售卖"}}}}
- DISCUSSED_TOPIC: (Person) 讨论过 (Topic)
  示例：type: "DISCUSSED_TOPIC", source: "米雪川", target: "技术书籍售卖"

**事件关系** ⚠️ 重要 - 必须提取:
- PARTICIPATED_IN: (Person) 参与了 (Event)
  示例：type: "PARTICIPATED_IN", source: "米雪川", source_type: "Person", target: "社交聚会", target_type: "Event"
  **规则**：Event的participants字段中的每个人，都必须创建一个PARTICIPATED_IN关系

**地点关系**:
- LIVES_IN: (Person) 居住在 (Location)
- HAPPENED_AT: (Event) 发生在 (Location)

**专长关系**:
- EXPERT_IN: (Person) 擅长 (Topic)

---

## 重要规则

1. **只提取明确提到的信息**，不要推测
2. **提取米雪川**：
   - 如果米雪川参与对话（在参与者列表中），必须提取
   - 标记：is_user: true, relationship_to_user: "自己"
   - 如果对话是对方独白/米雪川未参与，可以不提取
3. **必须提取对话参与者**：如果对话名称是"张三"，那么"张三"必须被提取为 Person
4. **Event的participants必须完整**：
   - 每个Event必须在participants字段中列出所有参与者的名称
   - 名称必须和people数组中提取的name完全一致
   - 每个participant都需要在relationships中创建PARTICIPATED_IN关系
   - 示例：Event "聚会", participants: ["米雪川", "Hunter"] → 必须创建2个PARTICIPATED_IN关系
5. **Topics 概括性原则**：
   - ✅ 正确：讨论了5本编程书 → Topic: "技术书籍售卖"
   - ❌ 错误：讨论了5本编程书 → 提取5个Topic（书名）
   - ❌ **禁止**：轻松幽默交流、友好沟通、愉快聊天等氛围描述
   - **原则**：提取讨论方向，不提取具体条目或氛围。细节由向量库负责
6. **People 命名规范（严格执行，违反会被删除）**：
   - ✅ 正确格式：
     * 有明确姓名：用中文姓名（"张三"、"李四"、"Hunter"）
     * 家人无姓名：必须用"XX的{关系}"（"吉月的弟弟"、"米雪川的妈妈"）
     * 复杂关系：逐级用"的"连接（"吉月的弟弟的女朋友"）
     * 间接关系：完整表达（"吉月的阿姨的姥姥"，不能写"吉月姨的姥姥"）
   - ❌ **严格禁止（会被删除）**：
     * 代词泛指：他、她、某人、第三方人物、未成年人、小孩
     * 泛指关系：亲戚、家人、爱人、对象、男友、女友
     * 单独关系词：弟弟、妈妈、我弟、我妈、朋友、同事
     * 英文格式：吉月's mother、mother、brother
     * 异常标点：吉月.的妈妈、吉月_的妈妈、吉月之弟弟
     * 缺"的"连接：吉月母亲、吉月儿子（必须是"吉月的母亲"）
     * 同义词混用：母亲、父亲、brother（统一用：妈妈、爸爸、弟弟）
   - 示例：✅ 吉月的妈妈 ❌ 妈妈、我妈、吉月母亲、吉月's mother、他、亲戚
6. **Events 有意义原则**：
   - ✅ 提取：会议、聚会、决策、重要讨论
   - ❌ 不提取：发消息、等待回复、打开文件等聊天过程
   - **判断**：这件事值得在时间线标注吗？
7. **Relationships 完整性原则**：
   - 必须提取的关系：KNOWS, WORKS_AT, FAMILY_OF, DISCUSSED_WITH, DISCUSSED_TOPIC
   - ⚠️ **Event关系（必需）**：每个Event的participants都必须创建PARTICIPATED_IN关系
   - 示例：Event有3个participants → 必须创建3个PARTICIPATED_IN关系
   - 不要遗漏关系，即使很明显也要明确提取
8. **时间参考 (time_reference)**:
   - "past": 过去发生的事（已经、昨天、上周、去年）
   - "present": 正在发生的事（现在、今天）
   - "future": 将来的事（明天、下周、计划）
9. **时间推断 (inferred_time 和 time_precision)**:
   - 根据 conversation_time 和 time_description 推断绝对时间
   - 例如：对话时间是"2019年11月01日"，提到"上周" → inferred_time: "2019-10-W4", time_precision: "week"
   - 例如：对话时间是"2019年11月01日"，提到"去年10月" → inferred_time: "2018-10", time_precision: "month"
   - 格式：year → "2019", month → "2019-10", week → "2019-W45", day → "2019-11-15"
   - 如果无法推断，设置为 null
10. **别名 (aliases) 和消歧提示 (disambiguation_hints)**:
   - 提取所有对同一人的不同称呼（如：["老张", "张工", "张三"]）
   - 记录有助于区分重名的信息（常一起出现的人、独特特征）
11. **置信度 (confidence)**: 根据上下文明确程度评估（0-1）
12. **如果某类实体为空，返回 []**
13. **务必返回合法的 JSON**：
    - 所有字符串必须在一对引号内，不要分段：✅ "context": "文本1。文本2" ❌ "context": "文本1", "文本2"
    - 注释必须在引号内：✅ "context": "text (注释)" ❌ "context": "text" (注释)
    - 数组中不能有括号注释：✅ ["值"] ❌ ["值" (注释)]
    - 不要有多余的文字、markdown标记
14. **知识图谱与向量库互补**：
    - 图谱负责：高层次结构、人物关系网、时间线、核心事件
    - 向量库负责：细节内容、语义搜索、全文检索
    - **不要在图谱中存储细节**：具体书名、餐厅名、技术栈版本等留给向量搜索
14. **这是米雪川的个人知识图谱**：
    - 重点关注米雪川做了什么、认识谁、讨论过什么方向
    - 目标：帮助米雪川快速回忆"和谁聊过什么主题"

请开始提取：
"""


def load_all_conversations(vector_store_path: str) -> List[Dict]:
    """加载所有对话记录"""
    print(f"📂 加载对话数据: {vector_store_path}")

    with open(vector_store_path, 'rb') as f:
        data = pickle.load(f)

    metadata = data.get('metadata', [])
    print(f"✅ 加载完成，共 {len(metadata)} 条对话记录")

    return metadata


def fix_json_format(json_str: str) -> str:
    """修复常见的JSON格式错误

    主要修复：
    1. context字段多引号片段："context": "text1", "text2" → "context": "text1。text2"
    """
    # 修复模式：匹配 "context": "xxx", "yyy", "zzz" 这种多段引号
    pattern = r'"context":\s*"([^"]*)"(?:,\s*"([^"]*)")+'

    def replace_func(match):
        # 获取所有匹配的文本片段
        first = match.group(1)
        # 查找所有后续的引号片段
        remaining = re.findall(r',\s*"([^"]*)"', match.group(0))
        all_parts = [first] + remaining
        # 合并所有片段，用句号连接
        merged = '。'.join(all_parts)
        return f'"context": "{merged}"'

    fixed = re.sub(pattern, replace_func, json_str)
    return fixed


def format_conversation_for_extraction(session: Dict) -> Dict:
    """格式化对话数据用于提取"""
    conversation_name = session.get('conversation_name', 'Unknown')
    conversation_type = session.get('conversation_type', 'unknown')
    start_timestamp = session.get('start_timestamp', 0)
    participants = session.get('participants', [])
    content_text = session.get('content_text', '')

    # 格式化时间
    if start_timestamp > 0:
        dt = datetime.fromtimestamp(start_timestamp)
        conversation_time = dt.strftime('%Y年%m月%d日')
    else:
        conversation_time = "未知"

    # 格式化参与者
    participants_str = ", ".join(participants) if participants else "未知"

    # 截断过长的对话内容（防止 token 超限）
    max_content_length = 8000
    if len(content_text) > max_content_length:
        content_text = content_text[:max_content_length] + "\n...[内容过长，已截断]"

    return {
        'conversation_name': conversation_name,
        'conversation_time': conversation_time,
        'conversation_type': conversation_type,
        'participants': participants_str,
        'conversation_text': content_text
    }


def call_gemini_extract(session: Dict, model_name: str = MODEL_NAME) -> Dict:
    """调用 Gemini 进行实体提取"""
    formatted = format_conversation_for_extraction(session)

    prompt = EXTRACTION_PROMPT.format(
        conversation_name=formatted['conversation_name'],
        conversation_time=formatted['conversation_time'],
        conversation_type=formatted['conversation_type'],
        participants=formatted['participants'],
        conversation_text=formatted['conversation_text']
    )

    model = GenerativeModel(model_name)

    try:
        start_time = time.time()

        response = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": MAX_OUTPUT_TOKENS}
        )

        duration = time.time() - start_time

        # 提取响应文本（原始输出）
        raw_response = response.text
        response_text = raw_response.strip()

        # 清理 JSON（移除可能的 markdown 标记）
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        # 解析 JSON（失败时尝试修复）
        try:
            entities = json.loads(response_text)
        except json.JSONDecodeError:
            # 尝试修复JSON格式
            fixed_text = fix_json_format(response_text)
            entities = json.loads(fixed_text)  # 如果还失败，会抛出异常到外层

        # 提取 token 使用情况
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count
        output_tokens = usage.candidates_token_count
        thoughts_tokens = getattr(usage, 'thoughts_token_count', 0)

        # 计算成本
        input_cost = (input_tokens / 1_000_000) * COST_INPUT
        output_cost = (output_tokens / 1_000_000) * COST_OUTPUT
        total_cost = input_cost + output_cost

        return {
            'success': True,
            'entities': entities,
            'raw_response': None,  # 成功时不保存原始输出（节省空间）
            'metadata': {
                'model': model_name,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'thoughts_tokens': thoughts_tokens,
                'duration_seconds': round(duration, 2),
                'cost': round(total_cost, 6)
            },
            'error': None
        }

    except json.JSONDecodeError as e:
        # 保存原始输出用于调试
        return {
            'success': False,
            'entities': None,
            'raw_response': raw_response if 'raw_response' in locals() else None,
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


def extract_with_retry(session: Dict, max_retries: int = MAX_RETRIES) -> Dict:
    """带重试的提取"""
    for attempt in range(max_retries):
        result = call_gemini_extract(session)

        if result['success']:
            return result

        if attempt < max_retries - 1:
            print(f"  ⚠️ 重试 {attempt + 1}/{max_retries - 1}...")
            time.sleep(1)

    return result


def build_extraction_result(session: Dict, extraction_result: Dict) -> Dict:
    """构建完整的提取结果（包含对话上下文）"""
    extraction_id = str(uuid4())

    # 提取对话元数据
    conversation_metadata = {
        'session_id': session.get('session_id'),
        'conversation_name': session.get('conversation_name'),
        'conversation_type': session.get('conversation_type'),
        'start_timestamp': session.get('start_timestamp'),
        'end_timestamp': session.get('end_timestamp'),
        'year': session.get('year'),
        'month': session.get('month'),
        'participants': session.get('participants', []),
        'message_count': session.get('message_count'),
        'content_sample': session.get('content_text', '')[:500]  # 保存前500字符作为样本
    }

    # 构建完整结果
    result = {
        'extraction_id': extraction_id,
        'created_at': datetime.now().isoformat(),
        'conversation': conversation_metadata,
        'entities': extraction_result.get('entities') if extraction_result['success'] else None,
        'extraction_metadata': extraction_result.get('metadata'),
        'success': extraction_result['success'],
        'error': extraction_result.get('error'),
        'raw_response': extraction_result.get('raw_response')  # 失败时保存原始输出
    }

    return result


def save_extraction(result: Dict, output_dir: Path) -> str:
    """保存提取结果到 JSON 文件"""
    session_id = result['conversation']['session_id']
    filename = f"session_{session_id}.json"
    filepath = output_dir / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return str(filepath)


def process_single_conversation(session: Dict, index: int, total: int, output_dir: Path) -> Dict:
    """处理单条对话"""
    session_id = session.get('session_id', 'unknown')
    conv_name = session.get('conversation_name', 'Unknown')

    # 检查是否已处理
    output_file = output_dir / f"session_{session_id}.json"
    if output_file.exists():
        print(f"  ⏭️ [{index}/{total}] 跳过（已存在）: {conv_name}")
        return {'status': 'skipped', 'session_id': session_id}

    print(f"  🔄 [{index}/{total}] 处理中: {conv_name}")

    # 提取实体
    extraction_result = extract_with_retry(session)

    # 构建完整结果
    result = build_extraction_result(session, extraction_result)

    # 保存
    save_extraction(result, output_dir)

    status = 'success' if extraction_result['success'] else 'failed'
    print(f"  {'✅' if status == 'success' else '❌'} [{index}/{total}] 完成: {conv_name}")

    return {
        'status': status,
        'session_id': session_id,
        'cost': extraction_result.get('metadata', {}).get('cost', 0) if extraction_result['success'] else 0,
        'duration': extraction_result.get('metadata', {}).get('duration_seconds', 0) if extraction_result['success'] else 0
    }


def main():
    """主函数：全量提取"""
    print("=" * 80)
    print("🚀 知识图谱全量提取开始")
    print("=" * 80)

    # 加载数据
    all_sessions = load_all_conversations(VECTOR_STORE_PATH)
    total_count = len(all_sessions)

    print(f"\n📊 提取配置:")
    print(f"  - 模型: {MODEL_NAME}")
    print(f"  - 总对话数: {total_count:,}")
    print(f"  - 并行度: {PARALLEL_WORKERS}")
    print(f"  - 重试次数: {MAX_RETRIES}")
    print(f"  - 输出目录: {OUTPUT_DIR}")

    # 检查已完成的数量
    existing_files = list(OUTPUT_DIR.glob("session_*.json"))
    existing_count = len(existing_files)
    remaining_count = total_count - existing_count

    print(f"\n📁 进度状态:")
    print(f"  - 已完成: {existing_count:,}")
    print(f"  - 剩余: {remaining_count:,}")
    print(f"  - 进度: {existing_count / total_count * 100:.1f}%")

    if remaining_count == 0:
        print("\n✅ 所有对话已提取完成！")
        return

    # 确认开始
    print(f"\n⚠️ 预估成本: ~${remaining_count * 0.0002:.2f}")
    print(f"⚠️ 预估时间: ~{remaining_count * 5.9 / PARALLEL_WORKERS / 3600:.1f} 小时")

    response = input("\n是否开始全量提取？(yes/no): ")
    if response.lower() != 'yes':
        print("❌ 已取消")
        return

    print("\n" + "=" * 80)
    print("🔥 开始并行提取...")
    print("=" * 80 + "\n")

    start_time = time.time()

    # 统计
    stats = {
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'total_cost': 0.0,
        'total_duration': 0.0
    }

    # 并行处理
    with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:
        futures = {
            executor.submit(process_single_conversation, session, idx + 1, total_count, OUTPUT_DIR): session
            for idx, session in enumerate(all_sessions)
        }

        for future in as_completed(futures):
            result = future.result()

            stats[result['status']] += 1
            stats['total_cost'] += result.get('cost', 0)
            stats['total_duration'] += result.get('duration', 0)

            # 每100条打印一次进度
            completed = stats['success'] + stats['failed'] + stats['skipped']
            if completed % 100 == 0:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                eta = (total_count - completed) / rate if rate > 0 else 0

                print(f"\n📊 进度: {completed}/{total_count} ({completed/total_count*100:.1f}%)")
                print(f"   成功: {stats['success']}, 失败: {stats['failed']}, 跳过: {stats['skipped']}")
                print(f"   速度: {rate:.1f} 条/秒, 预计剩余: {eta/60:.1f} 分钟")
                print(f"   累计成本: ${stats['total_cost']:.2f}\n")

    # 完成
    total_time = time.time() - start_time

    print("\n" + "=" * 80)
    print("🎉 全量提取完成！")
    print("=" * 80)

    print(f"\n📊 最终统计:")
    print(f"  - 总耗时: {total_time/3600:.2f} 小时")
    print(f"  - 成功: {stats['success']:,}")
    print(f"  - 失败: {stats['failed']:,}")
    print(f"  - 跳过: {stats['skipped']:,}")
    print(f"  - 成功率: {stats['success']/(stats['success']+stats['failed'])*100:.1f}%")
    print(f"  - 总成本: ${stats['total_cost']:.2f}")
    print(f"  - 平均速度: {total_count/total_time:.1f} 条/秒")

    print(f"\n💾 输出目录: {OUTPUT_DIR}")
    print(f"📁 文件数量: {len(list(OUTPUT_DIR.glob('session_*.json'))):,}")


if __name__ == '__main__':
    main()
