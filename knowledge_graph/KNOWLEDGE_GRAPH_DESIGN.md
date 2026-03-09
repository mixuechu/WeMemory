# 知识图谱构建完整设计方案

## 📋 总体流程

```
第一阶段：实体提取（当前）
├─ 输入：183K 对话记录（pickle 文件）
├─ 处理：LLM 提取实体
└─ 输出：JSON 文件（每条对话一个提取结果）

第二阶段：实体消歧与融合
├─ 输入：第一阶段的 JSON 结果
├─ 处理：人名消歧、地点合并、公司标准化
└─ 输出：规范化的实体库

第三阶段：关系抽取
├─ 输入：实体库 + 原始对话
├─ 处理：提取人物关系、事件关联
└─ 输出：关系三元组

第四阶段：图数据库构建
├─ 输入：实体库 + 关系三元组
├─ 处理：导入 Neo4j/ArangoDB
└─ 输出：可查询的知识图谱
```

---

## 🔍 当前提取结构的问题

### ❌ 问题 1：缺少时间信息

**当前提取的结构**：
```json
{
  "people": [...],
  "topics": [...],
  "events": [...],
  "locations": [...]
}
```

**问题**：
- ❌ 没有保存对话发生的时间
- ❌ 事件的时间信息丢失
- ❌ 无法回答"我什么时候去过襄阳？"

**原始数据中有的时间信息**：
```json
{
  "start_timestamp": 1572542495,  // Unix 时间戳
  "end_timestamp": 1572542730,
  "year": 2019,
  "month": 11,
  "session_id": "c6ed845e88d1dc1041f366c2eb3b1caf"
}
```

---

### ❌ 问题 2：缺少显式关系

**当前提取的内容**：
```json
{
  "people": [
    {
      "name": "Nick Luo",
      "relationship": "潜在雇主/合作者"  // 这是与"我"的关系
    }
  ]
}
```

**缺失的关系**：
- ❌ 人物之间的关系（Nick Luo 和 Ainia 是什么关系？）
- ❌ 人物与公司的关系（Nick Luo 在哪个公司工作？）
- ❌ 人物与事件的关系（谁参加了哪个会议？）
- ❌ 事件的因果关系（面试 → 接受 offer → 入职）

---

### ❌ 问题 3：缺少对话上下文

**当前提取**：
- ✅ 提取了实体
- ❌ 没有保存对话 ID、原始文本、参与者列表

**问题**：
- 无法追溯"这个信息来自哪条对话？"
- 无法验证提取的准确性
- 无法进行二次分析

---

## ✅ 改进后的数据结构

### 第一阶段：实体提取结果

```json
{
  "extraction_id": "uuid-1234-5678",
  "created_at": "2026-02-26T10:30:00Z",

  // 原始对话上下文
  "conversation": {
    "session_id": "c6ed845e88d1dc1041f366c2eb3b1caf",
    "conversation_name": "Nick Luo",
    "conversation_type": "private",
    "start_timestamp": 1572542495,
    "end_timestamp": 1572542730,
    "year": 2019,
    "month": 11,
    "participants": ["Nick Luo", "米雪川（我）"],
    "message_count": 20,
    "content_sample": "对话内容前 500 字符..."
  },

  // 提取的实体
  "entities": {
    "people": [
      {
        "name": "Nick Luo",
        "relationship_to_user": "潜在雇主/合作者",  // 与"我"的关系
        "occupation": "AI创业者",
        "company": "Ainia",
        "expertise": ["AI创业", "教育科技", "AI产品开发"],
        "personality": [],
        "confidence": 0.95,
        "mentioned_in_context": "Nick Luo 联系我讨论 Ainia 的职位..."
      }
    ],

    "topics": [
      {
        "name": "Ainia项目与招聘",
        "type": "工作项目",
        "keywords": ["Ainia", "招聘", "AI产品"],
        "confidence": 0.9,
        "first_mentioned": 1572542500  // 在对话中首次提到的时间戳
      },
      {
        "name": "AI伦理与能力边界",
        "type": "技术方案",
        "keywords": ["AI伦理", "能力边界", "讨论"],
        "confidence": 0.85,
        "first_mentioned": 1572542600
      }
    ],

    "events": [
      {
        "name": "腾讯会议面试",
        "type": "会议",
        "participants": ["Nick Luo", "米雪川"],
        "description": "通过腾讯会议进行面试，中途中断后恢复",
        "confidence": 0.9,
        "time_mentioned": 1572542550,  // 对话中提到的时间
        "inferred_time": "2019-11",  // 推测的实际发生时间（可能是对话时间）
        "location": null
      },
      {
        "name": "米雪川越南之旅",
        "type": "旅游",
        "participants": ["米雪川"],
        "description": "米雪川去越南旅游",
        "confidence": 0.8,
        "time_mentioned": 1572542650,
        "inferred_time": "2019-10",  // 可能在对话前发生
        "location": "越南"
      }
    ],

    "locations": [
      {
        "name": "越南",
        "type": "旅游目的地",
        "notes": "米雪川旅游地",
        "confidence": 0.8,
        "mentioned_count": 2
      }
    ]
  },

  // 提取的关系（第一阶段先提取简单的）
  "relationships": [
    {
      "type": "WORKS_AT",
      "source": "Nick Luo",
      "source_type": "Person",
      "target": "Ainia",
      "target_type": "Organization",
      "confidence": 0.9,
      "context": "Nick Luo 是 Ainia 创始人"
    },
    {
      "type": "PARTICIPATED_IN",
      "source": "Nick Luo",
      "source_type": "Person",
      "target": "腾讯会议面试",
      "target_type": "Event",
      "confidence": 0.95,
      "context": "Nick Luo 参加了面试"
    },
    {
      "type": "TRAVELED_TO",
      "source": "米雪川",
      "source_type": "Person",
      "target": "越南",
      "target_type": "Location",
      "confidence": 0.8,
      "time": "2019-10"
    }
  ],

  // 提取元数据
  "extraction_metadata": {
    "model": "gemini-2.5-flash",
    "model_version": "2025-02",
    "input_tokens": 306,
    "output_tokens": 450,
    "cost": 0.000158,
    "duration_seconds": 5.9,
    "success": true,
    "error": null
  }
}
```

---

## 🏗️ 图数据库模型设计

### 节点类型（Nodes）

#### 1. Person（人物）
```
属性：
- id: UUID
- name: 姓名
- canonical_name: 规范化姓名（消歧后）
- aliases: [别名列表]
- relationship_to_user: 与我的关系
- occupation: 职业
- expertise: [擅长领域]
- personality: [性格特征]
- first_mentioned: 首次提到时间
- last_mentioned: 最后提到时间
- mention_count: 提到次数
- confidence: 置信度
```

#### 2. Organization（组织/公司）
```
属性：
- id: UUID
- name: 组织名称
- canonical_name: 规范化名称
- type: 公司/学校/政府/其他
- industry: 行业
- first_mentioned: 首次提到
- mention_count: 提到次数
```

#### 3. Topic（主题）
```
属性：
- id: UUID
- name: 主题名称
- type: 分类
- keywords: [关键词]
- first_discussed: 首次讨论时间
- last_discussed: 最后讨论时间
- discussion_count: 讨论次数
```

#### 4. Event（事件）
```
属性：
- id: UUID
- name: 事件名称
- type: 事件类型
- description: 描述
- time: 事件时间
- time_precision: 时间精度（年/月/日）
- location: 地点
- first_mentioned: 首次提到
```

#### 5. Location（地点）
```
属性：
- id: UUID
- name: 地点名称
- canonical_name: 规范化名称
- type: 分类
- coordinates: 坐标（可选）
- first_mentioned: 首次提到
- visit_count: 访问次数（如果是旅游地）
```

#### 6. Conversation（对话会话）
```
属性：
- session_id: 会话ID
- conversation_name: 对话名称
- conversation_type: private/group
- start_time: 开始时间
- end_time: 结束时间
- year: 年份
- month: 月份
- participants: [参与者]
- message_count: 消息数
- content_sample: 内容样本
```

---

### 关系类型（Edges）

#### 人物关系
```
(Person)-[KNOWS]->(Person)
  - relationship_type: 朋友/同事/家人/合作伙伴
  - since: 认识时间
  - confidence: 置信度

(Person)-[WORKS_AT]->(Organization)
  - role: 职位
  - since: 开始时间
  - until: 结束时间（可选）

(Person)-[RELATED_TO_USER]->(Person: 米雪川)
  - relationship: 配偶/父母/朋友/同事/客户
  - closeness: 亲密度（基于对话频率）
```

#### 事件关系
```
(Person)-[PARTICIPATED_IN]->(Event)
  - role: 参与角色（组织者/参与者）

(Event)-[HAPPENED_AT]->(Location)
  - time: 时间

(Event)-[MENTIONS]->(Person)
(Event)-[DISCUSSES]->(Topic)

(Event)-[LEADS_TO]->(Event)  # 因果关系
  - description: 关系描述
```

#### 主题关系
```
(Person)-[INTERESTED_IN]->(Topic)
  - discussion_count: 讨论次数

(Person)-[EXPERT_IN]->(Topic)
  - based_on: [依据]

(Topic)-[RELATED_TO]->(Topic)
  - similarity: 相似度
```

#### 地点关系
```
(Person)-[VISITED]->(Location)
  - when: 访问时间
  - frequency: 访问频率

(Person)-[LIVES_IN]->(Location)
  - since: 开始时间
  - until: 结束时间

(Organization)-[LOCATED_IN]->(Location)
```

#### 对话关系
```
(Conversation)-[MENTIONED]->(Person)
(Conversation)-[MENTIONED]->(Organization)
(Conversation)-[DISCUSSED]->(Topic)
(Conversation)-[MENTIONED]->(Event)
(Conversation)-[MENTIONED]->(Location)

(Conversation)-[HAS_PARTICIPANT]->(Person)
```

---

## 🔄 完整构建流程

### 阶段 1: 实体提取（7.6小时）

```python
# 输入：vector_stores/conversations_complete.pkl
# 输出：extractions/session_*.json（183K 个文件）

for session in all_sessions:
    extraction_result = {
        "extraction_id": uuid4(),
        "conversation": extract_conversation_metadata(session),
        "entities": call_llm_extract(session.content),
        "relationships": extract_simple_relationships(entities),
        "extraction_metadata": {...}
    }
    save_json(f"extractions/session_{session.id}.json", extraction_result)
```

**输出示例**：
```
extractions/
├── session_c6ed845e.json
├── session_a1b2c3d4.json
├── ...
└── session_xyz12345.json
```

---

### 阶段 2: 实体消歧与融合（1-2小时）

```python
# 输入：extractions/*.json
# 输出：entities/canonical_entities.json

# 人名消歧
"Nick Luo" = "Nick" = "Luo" = "罗老师"

# 公司标准化
"奇富科技" = "奇富" = "QiRich"

# 地点合并
"北京" 下包含 "朝阳", "五道口"

# 输出
{
  "people": {
    "person_001": {
      "canonical_name": "Nick Luo",
      "aliases": ["Nick", "Luo", "罗老师"],
      "occurrences": 45,
      "first_mentioned": 1572542495,
      ...
    }
  },
  "organizations": {...},
  "locations": {...},
  "topics": {...}
}
```

---

### 阶段 3: 关系提取（可选，2-4小时）

```python
# 基于实体共现和上下文，提取更复杂的关系

# 例如：
if "Nick Luo" and "Ainia" in same_conversation:
    if context_mentions("创始人"):
        add_relationship("Nick Luo", "FOUNDED", "Ainia")

# 人物关系推断
if person_A and person_B appear in >10 conversations:
    relationship_type = infer_relationship(conversations)
    add_relationship(person_A, "KNOWS", person_B, type=relationship_type)
```

---

### 阶段 4: 图数据库构建（1小时）

```python
# 输入：entities/canonical_entities.json + extractions/*.json
# 输出：Neo4j 数据库

# 创建节点
for person in canonical_entities['people']:
    neo4j.create_node("Person", person)

for org in canonical_entities['organizations']:
    neo4j.create_node("Organization", org)

# 创建关系
for extraction in all_extractions:
    for relationship in extraction['relationships']:
        neo4j.create_edge(relationship)

# 创建索引
neo4j.create_index("Person", "canonical_name")
neo4j.create_index("Event", "time")
neo4j.create_index("Conversation", "start_time")
```

---

## 📊 数据量预估

### 实体数量（基于测试结果）

假设 183K 对话，平均 12 实体/对话（Gemini 2.5 Flash）：

| 实体类型 | 原始数量 | 消歧后数量 | 估算 |
|---------|---------|-----------|------|
| **People** | ~360K | ~5,000 | 去重后剩 1.4% |
| **Organizations** | ~100K | ~2,000 | 去重后剩 2% |
| **Topics** | ~620K | ~10,000 | 去重后剩 1.6% |
| **Events** | ~370K | ~100,000 | 大部分是独特事件 |
| **Locations** | ~380K | ~3,000 | 去重后剩 0.8% |
| **Conversations** | 183K | 183K | 无去重 |
| **总计** | ~2.2M | ~303K | - |

### 关系数量

| 关系类型 | 估算数量 |
|---------|---------|
| (Conversation)-[MENTIONED]->(*) | ~2.2M |
| (Person)-[WORKS_AT]->(Org) | ~5K |
| (Person)-[KNOWS]->(Person) | ~15K |
| (Person)-[PARTICIPATED_IN]->(Event) | ~150K |
| (Event)-[HAPPENED_AT]->(Location) | ~50K |
| **总计** | ~2.4M |

---

## 🎯 优先级与决策

### 必须做的（Phase 1）

1. ✅ **改进提取 prompt**：
   - 添加时间提取（事件发生时间）
   - 添加简单关系提取（WORKS_AT, PARTICIPATED_IN）
   - 保存对话上下文

2. ✅ **完整的保存结构**：
   - 每条对话保存为独立 JSON
   - 包含原始数据引用（session_id）

3. ✅ **实体提取**：
   - 使用 Gemini 2.5 Flash
   - 并行处理（20 workers）
   - 成本 ~$38

### 可以延后的（Phase 2）

4. ⏳ **实体消歧**：
   - 可以先构建图，再逐步消歧
   - 使用嵌入模型辅助（相似名称聚类）

5. ⏳ **复杂关系提取**：
   - 人物之间的社交关系
   - 事件的因果链
   - 可以后续通过图算法推断

### 可选的（Phase 3）

6. 📌 **时序分析**：
   - 人物关系演化
   - 主题趋势变化

7. 📌 **高级查询**：
   - 路径查询（A认识B是通过谁？）
   - 推荐系统（基于我的兴趣，可能认识谁？）

---

## ❓ 需要你确认的问题

### 问题 1: 提取粒度

**选项 A**（推荐）：一次性提取所有信息
```
优点：只需要调用一次 LLM
缺点：prompt 更复杂，可能影响准确性
```

**选项 B**：分两阶段
```
阶段1：提取实体（当前）
阶段2：基于实体提取关系（再调用一次 LLM）
优点：每个任务更聚焦
缺点：成本翻倍（$38 → $76）
```

### 问题 2: 时间提取策略

**选项 A**：让 LLM 推断事件时间
```
prompt: "请推断事件发生的具体时间（年月日）"
优点：可能得到更精确的时间
缺点：LLM 容易猜错
```

**选项 B**（推荐）：使用对话时间 + 时态标记
```
如果事件用过去时描述 → 时间 = 对话时间之前
如果事件用将来时描述 → 时间 = 对话时间之后
优点：更可靠
缺点：精度较低（只到月份）
```

### 问题 3: 存储方式

**选项 A**（推荐）：每条对话一个 JSON 文件
```
优点：增量处理，失败后可恢复
缺点：文件数量多（183K 个）
```

**选项 B**：批量保存（每 1000 条一个文件）
```
优点：文件数量少（183 个）
缺点：失败后损失较大
```

### 问题 4: 图数据库选择

**选项 A**：Neo4j（推荐）
```
优点：成熟、查询语言强大（Cypher）
缺点：内存消耗大
```

**选项 B**：ArangoDB
```
优点：支持多模型（图+文档+K/V）
缺点：社区较小
```

**选项 C**：SQLite + 自定义图查询
```
优点：轻量、无需额外服务
缺点：图查询性能差
```

---

## 📝 你的选择是？

请告诉我：

1. **提取粒度**：A（一次性）还是 B（分阶段）？
2. **时间提取**：A（LLM 推断）还是 B（对话时间+时态）？
3. **存储方式**：A（每条一文件）还是 B（批量）？
4. **图数据库**：A（Neo4j）还是 B（ArangoDB）还是 C（SQLite）？

我会根据你的选择，调整 prompt 和代码，然后开始全量提取！
