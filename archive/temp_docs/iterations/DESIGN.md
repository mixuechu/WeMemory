# 知识图谱设计文档

## 概述

从微信聊天记录中构建知识图谱，提取实体、关系和事件，为长期记忆提供结构化支持。

## 核心理念

**好友标签 = 人物实体的属性**

不需要单独的"好友标签"模块，而是作为知识图谱中"人物实体"的属性提取。

## 1. 实体类型设计

### 1.1 Person (人物实体)

**核心属性**:
```python
{
    "entity_id": "person_xxx",
    "entity_type": "Person",

    # 基础信息
    "name": "张三",                    # 主要姓名
    "aliases": ["老张", "张工"],        # 别名列表

    # 关系属性（这就是之前的"好友标签"）
    "relationship_with_user": "同事",   # 与用户的关系
    "relationship_strength": 0.85,     # 关系强度 (0-1)

    # 描述属性
    "occupation": "软件工程师",         # 职业
    "company": "XX科技公司",           # 公司
    "interests": ["AI", "技术", "爬山"], # 兴趣爱好
    "personality_traits": ["认真", "靠谱"], # 性格特征

    # 联系信息
    "wechat_name": "1900",            # 微信名称（对话名称）
    "phone": null,                     # 电话（如果提到）
    "email": null,                     # 邮箱（如果提到）

    # 时序信息
    "first_met_time": 1704067200,      # 初次见面时间（从对话推断）
    "last_contact_time": 1735689600,   # 最后联系时间
    "total_conversations": 152,        # 总对话数
    "total_messages": 3420,            # 总消息数

    # 上下文信息
    "mentioned_in": ["对话1", "对话2"], # 被提及的对话
    "direct_conversations": ["对话3"],  # 直接对话

    # 元数据
    "confidence": 0.92,                # 提取置信度
    "source": "llm_extraction",        # 来源
    "last_updated": 1708012800,        # 最后更新时间
    "tags": ["技术", "可靠"]            # 自定义标签
}
```

**提取策略**:
- 从对话名称识别人物
- 从消息内容中识别提到的人物
- 使用 LLM 分析对话内容提取属性
- 多次出现时聚合和验证信息

### 1.2 Organization (组织实体)

```python
{
    "entity_id": "org_xxx",
    "entity_type": "Organization",
    "name": "XX科技公司",
    "type": "company",  # company/school/club/government
    "industry": "互联网",
    "location": "北京",
    "mentioned_in": [...],
    "related_people": ["person_xxx", ...]
}
```

### 1.3 Location (地点实体)

```python
{
    "entity_id": "loc_xxx",
    "entity_type": "Location",
    "name": "香山",
    "type": "scenic_spot",  # city/restaurant/scenic_spot/building
    "address": "北京市海淀区",
    "visited_times": 3,
    "mentioned_in": [...]
}
```

### 1.4 Event (事件实体)

```python
{
    "entity_id": "event_xxx",
    "entity_type": "Event",
    "name": "团建爬山",
    "type": "social",  # meeting/social/travel/milestone
    "time": 1708012800,
    "participants": ["person_xxx", ...],
    "location": "loc_香山",
    "description": "公司团建活动，爬香山",
    "mentioned_in": [...]
}
```

### 1.5 Topic (主题实体)

```python
{
    "entity_id": "topic_xxx",
    "entity_type": "Topic",
    "name": "AI项目",
    "category": "work",  # work/tech/life/entertainment
    "keywords": ["AI", "模型", "部署"],
    "discussion_count": 25,
    "related_people": [...],
    "related_events": [...]
}
```

## 2. 关系类型设计

### 2.1 Person-Person 关系

```python
{
    "relation_id": "rel_xxx",
    "relation_type": "FRIEND_OF",
    "source": "person_张三",
    "target": "person_李四",

    # 关系属性
    "strength": 0.8,           # 关系强度
    "interaction_count": 156,  # 互动次数
    "first_interaction": timestamp,
    "last_interaction": timestamp,

    # 上下文
    "context": "通过工作认识",
    "evidence": ["对话1", "对话2"]
}
```

**关系类型**:
- `FRIEND_OF`: 朋友
- `COLLEAGUE_OF`: 同事
- `FAMILY_OF`: 亲属
- `CLASSMATE_OF`: 同学
- `KNOWS`: 认识（一般关系）
- `INTRODUCED_BY`: 由谁介绍认识

### 2.2 Person-Organization 关系

```python
{
    "relation_type": "WORKS_AT",  # WORKS_AT/STUDIES_AT/MEMBER_OF
    "source": "person_xxx",
    "target": "org_xxx",
    "role": "软件工程师",
    "start_time": timestamp,
    "end_time": null,  # null表示当前
    "is_current": true
}
```

### 2.3 Person-Event 关系

```python
{
    "relation_type": "PARTICIPATED_IN",  # PARTICIPATED_IN/ORGANIZED
    "source": "person_xxx",
    "target": "event_xxx",
    "role": "参与者",  # 参与者/组织者
}
```

### 2.4 Person-Location 关系

```python
{
    "relation_type": "LIVES_IN",  # LIVES_IN/VISITED/WORKS_IN
    "source": "person_xxx",
    "target": "loc_xxx",
    "frequency": 5,  # 访问频率
    "first_visit": timestamp,
    "last_visit": timestamp
}
```

## 3. 时序事件链

### 3.1 事件序列

按时间顺序组织事件，构建时间线：

```python
{
    "timeline_id": "timeline_xxx",
    "person": "person_张三",
    "events": [
        {
            "time": timestamp,
            "event": "event_xxx",
            "type": "meeting",
            "description": "项目启动会议"
        },
        {
            "time": timestamp + 86400,
            "event": "event_yyy",
            "type": "discussion",
            "description": "讨论技术方案"
        }
    ]
}
```

### 3.2 因果关系

```python
{
    "relation_type": "LEADS_TO",
    "source": "event_项目启动",
    "target": "event_技术方案讨论",
    "confidence": 0.85,
    "evidence": "时间顺序 + 主题连贯性"
}
```

## 4. LLM 提取 Prompt 设计

### 4.1 人物实体提取

```
你是一个信息提取专家。请从以下微信对话中提取人物信息。

对话信息：
- 对话名称：{conversation_name}
- 参与者：{participants}
- 时间范围：{time_range}
- 对话内容：{content}

请提取以下信息（JSON格式）：
{
  "people": [
    {
      "name": "人物姓名",
      "relationship": "与用户的关系（同事/朋友/家人/客户/其他）",
      "occupation": "职业（如果提到）",
      "company": "公司（如果提到）",
      "interests": ["兴趣1", "兴趣2"],
      "personality": ["性格特征1", "性格特征2"],
      "evidence": "支持这些信息的对话片段"
    }
  ]
}

注意：
1. 只提取明确提到的信息，不确定的字段填 null
2. 用户通常是"我"，不要把用户自己作为人物实体
3. 关系类型限定为：同事/朋友/家人/客户/同学/其他
4. 提供证据支持你的判断
```

### 4.2 关系提取

```
从以下对话中识别人物之间的关系：

对话内容：{content}
已识别人物：{people_list}

请识别关系（JSON格式）：
{
  "relationships": [
    {
      "person1": "张三",
      "person2": "李四",
      "relationship": "同事",
      "evidence": "对话片段",
      "confidence": 0.9
    }
  ]
}
```

### 4.3 事件提取

```
提取对话中提到的事件：

对话内容：{content}

请提取事件（JSON格式）：
{
  "events": [
    {
      "event_name": "团建活动",
      "type": "social",  # meeting/social/travel/milestone
      "time": "2024-03-15或null",
      "participants": ["张三", "李四"],
      "location": "香山",
      "description": "简短描述",
      "evidence": "对话片段"
    }
  ]
}
```

## 5. 技术架构

### 5.1 模型抽象

```python
# 基础接口
class BaseLLM(ABC):
    @abstractmethod
    def extract_entities(self, prompt: str, text: str) -> dict:
        """提取实体"""
        pass

    @abstractmethod
    def extract_relations(self, prompt: str, text: str) -> dict:
        """提取关系"""
        pass

# 具体实现
class GeminiExtractor(BaseLLM):
    """Google Gemini 实现"""
    pass

class OpenAIExtractor(BaseLLM):
    """OpenAI GPT 实现"""
    pass

class LocalLLMExtractor(BaseLLM):
    """本地模型实现"""
    pass
```

### 5.2 处理流程

```
1. 数据准备
   ├─ 加载对话数据
   ├─ 按对话分组
   └─ 准备上下文

2. 实体提取 (Phase 3.1)
   ├─ 人物实体提取 (优先)
   │  ├─ 从对话名称识别
   │  ├─ 从消息内容识别
   │  ├─ LLM 属性提取
   │  └─ 实体消歧和合并
   │
   ├─ 组织实体提取
   ├─ 地点实体提取
   └─ 主题实体提取

3. 关系抽取 (Phase 3.2)
   ├─ Person-Person 关系
   ├─ Person-Organization 关系
   └─ 其他关系

4. 事件抽取 (Phase 3.3)
   ├─ 识别事件
   ├─ 构建时间线
   └─ 因果关系

5. 图谱存储 (Phase 3.4)
   ├─ 图数据库写入 (Neo4j)
   └─ 或 NetworkX + 序列化
```

### 5.3 增量更新

```python
def incremental_update(new_conversations):
    """增量更新图谱"""
    # 1. 提取新对话的实体和关系
    new_entities = extract_entities(new_conversations)
    new_relations = extract_relations(new_conversations)

    # 2. 与现有实体合并
    for entity in new_entities:
        existing = find_entity(entity.name)
        if existing:
            merge_entity(existing, entity)
        else:
            add_entity(entity)

    # 3. 更新关系
    for relation in new_relations:
        update_or_add_relation(relation)
```

## 6. 数据库选型

### 方案 A: Neo4j (推荐)

**优点**:
- 专业图数据库
- Cypher 查询语言强大
- 可视化工具完善
- 性能好

**缺点**:
- 需要额外服务
- 学习曲线

**使用场景**: 生产环境，复杂图查询

### 方案 B: NetworkX + Pickle

**优点**:
- 轻量级，无需额外服务
- Python 原生支持
- 快速开发

**缺点**:
- 性能有限
- 查询功能较弱

**使用场景**: 快速原型，小规模数据

### 方案 C: SQLite + JSON (折中)

**优点**:
- 单文件数据库
- SQL 查询
- 易于部署

**缺点**:
- 不是真正的图数据库
- 图遍历性能差

**使用场景**: 中等规模，简单查询

## 7. 实现计划

### Phase 3.1: 实体识别 (5-7天)

**Week 1**:
- [ ] Day 1-2: 设计 Entity Schema 和 LLM Prompt
- [ ] Day 3-4: 实现人物实体提取器
- [ ] Day 5: 实现实体消歧和合并
- [ ] Day 6-7: 测试和优化

**输出**:
- `knowledge_graph/extractors/entity_extractor.py`
- `knowledge_graph/models/entities.py`
- `knowledge_graph/prompts/entity_extraction.txt`

### Phase 3.2: 关系抽取 (4-6天)

**Week 2**:
- [ ] Day 1-2: 设计关系 Schema 和 Prompt
- [ ] Day 3-4: 实现关系提取器
- [ ] Day 5-6: 测试和优化

### Phase 3.3: 时序事件链 (3-5天)

**Week 2-3**:
- [ ] Day 1-2: 事件提取
- [ ] Day 3: 时间线构建
- [ ] Day 4-5: 因果关系推理

### Phase 3.4: 图谱存储 (3-4天)

**Week 3**:
- [ ] Day 1-2: 选择并配置数据库
- [ ] Day 3: CRUD 接口
- [ ] Day 4: 测试和文档

## 8. 评估指标

### 8.1 实体提取质量

- **准确率**: 提取的实体有多少是正确的
- **召回率**: 真实存在的实体有多少被提取到
- **F1 分数**: 准确率和召回率的调和平均

### 8.2 关系提取质量

- **关系准确率**: 提取的关系有多少是正确的
- **关系完整性**: 重要关系的覆盖率

### 8.3 属性提取质量

- **属性准确率**: 人物属性（职业、兴趣等）的准确性
- **置信度校准**: 模型给出的置信度与实际准确率的匹配度

### 8.4 系统性能

- **处理速度**: 每个对话的处理时间
- **成本**: LLM API 调用成本
- **内存占用**: 图谱存储大小

## 9. 风险和挑战

### 9.1 实体消歧

**问题**: "张三" 可能指多个人
**解决**:
- 使用上下文（公司、职位）区分
- 计算相似度合并
- 人工审核接口

### 9.2 LLM 幻觉

**问题**: LLM 可能编造不存在的信息
**解决**:
- 要求提供证据
- 多次提取验证
- 置信度阈值过滤

### 9.3 隐私问题

**问题**: 敏感信息提取
**解决**:
- 脱敏处理
- 访问控制
- 用户审核机制

## 10. 下一步行动

1. **确认技术选型**:
   - LLM 选择: Gemini / GPT-4 / 混合
   - 数据库选择: Neo4j / NetworkX / SQLite

2. **开始 Phase 3.1**:
   - 创建目录结构
   - 实现人物实体提取
   - 设计 Prompt 模板

3. **准备测试数据**:
   - 选择 10-20 个代表性对话
   - 人工标注实体和关系
   - 作为评估基准

**准备好开始了吗？有什么想讨论的技术选型问题？**
