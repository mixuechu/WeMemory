# 知识图谱构建完整方案

## 📋 核心设计原则

### 1. aliases 重名问题的解决方案

**问题**：
- "老哥"、"老张"、"老婆" 等称呼会指向不同的人
- 跨度多年，同一称呼在不同时期可能指不同人

**解决方案**：
```json
// 提取阶段：每个 Person 都有 aliases 列表
{
  "name": "张三",
  "aliases": ["老张", "张工"],
  "disambiguation_hints": {
    "occupation": "算法工程师",
    "company": "阿里",
    "context": "公司同事，搞机器学习的",
    "co_occurs_with": ["李四", "王五"]  // 经常一起出现的人
  }
}

// 消歧阶段：构建 alias → persons 映射
{
  "老张": [
    {
      "person_id": "person_001",
      "canonical_name": "张三",
      "evidence": [
        {"session": "conv_123", "context": "老张在阿里"},
        {"session": "conv_456", "context": "老张搞算法"}
      ]
    },
    {
      "person_id": "person_089",
      "canonical_name": "张伟",
      "evidence": [
        {"session": "conv_789", "context": "老张在腾讯"},
        {"session": "conv_999", "context": "老张是产品经理"}
      ]
    }
  ]
}

// 人工干预阶段：
// 系统提示："老张 可能指 2 个不同的人，请确认是否合并"
// 用户选择：
//   - 合并 person_001 和 person_089（如果确认是同一人）
//   - 保持分离（如果确认是不同人）
//   - 标记为"需要更多信息"
```

---

## 🏗️ 完整流程

### 阶段1: 实体提取（LLM）

**输入**：183K 对话 JSON
**输出**：183K 提取结果 JSON

**每个提取结果包含**：

```json
{
  "extraction_id": "uuid",
  "created_at": "2026-02-26T...",

  "conversation": {
    "session_id": "xxx",
    "conversation_name": "张三",
    "start_timestamp": 1573776800,
    "year": 2019,
    "month": 11,
    "participants": ["张三", "米雪川"]
  },

  "entities": {
    "people": [{
      "name": "张三",
      "is_user": false,
      "aliases": ["老张", "张工"],  // ← 所有称呼
      "relationship_to_user": "同事",
      "occupation": "算法工程师",
      "company": "阿里",
      "expertise": ["机器学习", "推荐系统"],
      "personality": ["技术宅"],
      "confidence": 0.9,
      "context": "公司同事，经常讨论算法问题",
      "disambiguation_hints": {
        "co_occurs_with": ["李四", "王五"],
        "distinctive_features": "阿里的算法工程师"
      }
    }],

    "topics": [{
      "name": "机器学习",
      "type": "技术方案",
      "keywords": ["算法", "模型", "训练"],
      "confidence": 0.9,
      "context": "讨论推荐系统中的机器学习应用"
    }],

    "events": [{
      "name": "讨论推荐算法",
      "type": "会议",
      "participants": ["米雪川", "张三"],
      "location": "阿里办公室",
      "description": "讨论新的推荐算法方案",
      "time_reference": "past",
      "time_description": "上周",
      "inferred_time": "2019-11-W1",  // ← LLM推断（基于对话时间2019-11）
      "time_precision": "week",       // ← year/quarter/month/week/day/hour
      "confidence": 0.8,
      "context": "对话中提到上周和张三讨论了推荐算法"
    }],

    "locations": [{
      "name": "阿里办公室",
      "type": "公司",
      "parent_location": "杭州",
      "confidence": 0.8,
      "context": "张三工作的地方"
    }],

    "relationships": [{
      "type": "WORKS_AT",
      "source": "张三",
      "source_type": "Person",
      "target": "阿里",
      "target_type": "Organization",
      "properties": {
        "role": "算法工程师"
      },
      "confidence": 0.9,
      "context": "对话中提到张三在阿里做算法"
    }]
  }
}
```

**关键改进**：
1. ✅ `aliases`：所有称呼（列表）
2. ✅ `disambiguation_hints`：消歧线索
   - `co_occurs_with`：经常一起出现的人
   - `distinctive_features`：区分特征
3. ✅ `inferred_time`：LLM推断的时间
4. ✅ `time_precision`：时间精度

---

### 阶段2: 实体消歧（自动 + 人工）

**输入**：183K 提取结果 JSON
**输出**：实体映射表 + 消歧报告

#### 2.1 自动聚类

```python
# 1. 收集所有提到的人物
all_person_mentions = []
for extraction in all_extractions:
    for person in extraction.entities.people:
        all_person_mentions.append({
            "session_id": extraction.conversation.session_id,
            "name": person.name,
            "aliases": person.aliases,
            "hints": person.disambiguation_hints,
            "context": person.context
        })

# 2. 按名字和aliases分组
name_groups = defaultdict(list)
for mention in all_person_mentions:
    # 主名字
    name_groups[mention.name].append(mention)
    # 所有别名
    for alias in mention.aliases:
        name_groups[alias].append(mention)

# 3. 对每个组进行聚类
disambiguated_persons = {}
for name, mentions in name_groups.items():
    clusters = cluster_mentions(mentions)  # 基于上下文相似度、时间、共现等

    for cluster_id, cluster in enumerate(clusters):
        person_id = f"person_{hash(name)}_{cluster_id}"
        disambiguated_persons[person_id] = {
            "canonical_name": most_common_name(cluster),
            "all_names": set([m.name for m in cluster]),
            "all_aliases": set([a for m in cluster for a in m.aliases]),
            "evidence": cluster,
            "confidence": calculate_confidence(cluster),
            "needs_review": len(clusters) > 1  # 如果同名有多个聚类，需要人工review
        }
```

#### 2.2 聚类算法（基于多维度）

```python
def should_merge(mention1, mention2):
    """判断两个提及是否应该合并为同一人"""
    score = 0

    # 1. 名字匹配（50分）
    if mention1.name == mention2.name:
        score += 50
    elif mention1.name in mention2.aliases or mention2.name in mention1.aliases:
        score += 40

    # 2. 公司匹配（30分）
    if mention1.company and mention2.company:
        if mention1.company == mention2.company:
            score += 30
        else:
            score -= 50  # 不同公司，很可能不是同一人

    # 3. 职业匹配（20分）
    if mention1.occupation and mention2.occupation:
        if similar(mention1.occupation, mention2.occupation):
            score += 20

    # 4. 共现人物（20分）
    common_cooccurs = set(mention1.hints.co_occurs_with) & set(mention2.hints.co_occurs_with)
    score += len(common_cooccurs) * 5

    # 5. 时间距离（-10分 if 相隔很远）
    time_gap = abs(mention1.time - mention2.time)
    if time_gap > 3 * 365 * 24 * 3600:  # 3年
        score -= 10

    # 6. 上下文相似度（30分）
    context_similarity = embedding_similarity(mention1.context, mention2.context)
    score += context_similarity * 30

    return score >= 60  # 阈值
```

#### 2.3 人工干预界面（需要构建）

```
消歧报告：
==================
需要人工确认的案例：52 个

案例1: "老张"
  可能的人物：
    [ ] person_001: 张三（阿里算法工程师）
        - 出现次数: 45次
        - 时间范围: 2018-2020
        - 共现: 李四、王五
        - 特征: 讨论机器学习

    [ ] person_089: 张伟（腾讯产品经理）
        - 出现次数: 12次
        - 时间范围: 2019-2021
        - 共现: 刘六
        - 特征: 讨论产品设计

  操作：
    [合并为同一人] [保持分离] [需要更多证据]

案例2: "老婆"
  可能的人物：
    [ ] person_234: 李梅
        - 出现次数: 230次
        - 时间范围: 2015-2018
        - 特征: 讨论家庭、旅游

    [ ] person_567: 王芳
        - 出现次数: 450次
        - 时间范围: 2019-2025
        - 特征: 讨论工作、生活

  操作：
    [合并] [分离] √ （已自动判断：时间不重叠，应为不同人）
```

---

### 阶段3: 图谱构建

**输入**：
- 183K 提取结果 JSON
- 实体映射表（消歧结果）

**输出**：Neo4j 图数据库

#### 3.1 节点创建

```python
# 1. Person 节点
for person_id, person_data in disambiguated_persons.items():
    create_node("Person", {
        "id": person_id,
        "canonical_name": person_data.canonical_name,
        "all_names": list(person_data.all_names),
        "all_aliases": list(person_data.all_aliases),
        "mention_count": len(person_data.evidence),
        "first_mentioned": min(e.time for e in person_data.evidence),
        "last_mentioned": max(e.time for e in person_data.evidence),
        "is_user": any(e.is_user for e in person_data.evidence)
    })

# 2. Conversation 节点（作为一等公民）
for extraction in all_extractions:
    conv = extraction.conversation
    create_node("Conversation", {
        "id": conv.session_id,
        "name": conv.conversation_name,
        "type": conv.conversation_type,
        "time": conv.start_timestamp,
        "year": conv.year,
        "month": conv.month,
        "message_count": conv.message_count
    })

# 3. Topic 节点（消歧后）
for topic in disambiguated_topics:
    create_node("Topic", {...})

# 4. Event 节点
for event in all_events:
    create_node("Event", {
        "id": event.id,
        "name": event.name,
        "type": event.type,
        "inferred_time": event.inferred_time,
        "time_precision": event.time_precision,
        "description": event.description
    })

# 5. Location 节点（消歧后）
for location in disambiguated_locations:
    create_node("Location", {...})

# 6. Organization 节点（消歧后）
for org in disambiguated_organizations:
    create_node("Organization", {...})
```

#### 3.2 关系创建

```python
for extraction in all_extractions:
    conv_id = extraction.conversation.session_id

    # 1. Person <-> Conversation
    for participant in extraction.conversation.participants:
        person_id = resolve_person(participant)  # 查映射表
        create_edge(person_id, "PARTICIPATED_IN", conv_id, {
            "time": extraction.conversation.start_timestamp
        })

    # 2. Conversation -> Topic
    for topic in extraction.entities.topics:
        topic_id = resolve_topic(topic.name)
        create_edge(conv_id, "DISCUSSED", topic_id, {
            "confidence": topic.confidence
        })

    # 3. Person -> Event
    for event in extraction.entities.events:
        event_id = create_event_node(event)
        for participant in event.participants:
            person_id = resolve_person(participant)
            create_edge(person_id, "PARTICIPATED_IN", event_id, {
                "time": event.inferred_time
            })

    # 4. 提取的关系
    for rel in extraction.entities.relationships:
        source_id = resolve_entity(rel.source, rel.source_type)
        target_id = resolve_entity(rel.target, rel.target_type)
        create_edge(source_id, rel.type, target_id, {
            "confidence": rel.confidence,
            "observed_in": conv_id,
            "observed_at": extraction.conversation.start_timestamp
        })

    # 5. 属性转关系
    for person in extraction.entities.people:
        person_id = resolve_person(person.name)

        # expertise -> EXPERT_IN
        for skill in person.expertise:
            skill_id = resolve_topic(skill)
            create_edge(person_id, "EXPERT_IN", skill_id)

        # company -> WORKS_AT
        if person.company:
            org_id = resolve_organization(person.company)
            create_edge(person_id, "WORKS_AT", org_id, {
                "role": person.occupation
            })
```

---

### 阶段4: 查询示例

有了完整图谱，可以支持：

```cypher
-- 1. 我和张三聊过什么？
MATCH (me:Person {is_user: true})-[:PARTICIPATED_IN]->(c:Conversation)<-[:PARTICIPATED_IN]-(张三:Person)
WHERE 张三.canonical_name = "张三" OR "张三" IN 张三.all_aliases
MATCH (c)-[:DISCUSSED]->(t:Topic)
RETURN t.name, c.time
ORDER BY c.time DESC

-- 2. 谁擅长机器学习？
MATCH (p:Person)-[:EXPERT_IN]->(t:Topic {name: "机器学习"})
RETURN p.canonical_name, p.all_aliases

-- 3. 我什么时候去过襄阳？
MATCH (me:Person {is_user: true})-[:PARTICIPATED_IN]->(e:Event)-[:HAPPENED_AT]->(l:Location)
WHERE l.name = "襄阳"
RETURN e.name, e.inferred_time, e.time_precision

-- 4. "老张"可能是谁？（消歧辅助）
MATCH (p:Person)
WHERE "老张" IN p.all_aliases
RETURN p.canonical_name, p.all_names, p.mention_count

-- 5. 我和谁聊天最多？
MATCH (me:Person {is_user: true})-[:PARTICIPATED_IN]->(c:Conversation)<-[:PARTICIPATED_IN]-(other:Person)
WHERE other.is_user = false
RETURN other.canonical_name, count(c) as chat_count
ORDER BY chat_count DESC
LIMIT 10

-- 6. 2019年我主要讨论什么话题？
MATCH (me:Person {is_user: true})-[:PARTICIPATED_IN]->(c:Conversation)-[:DISCUSSED]->(t:Topic)
WHERE c.year = 2019
RETURN t.name, t.type, count(*) as frequency
ORDER BY frequency DESC
```

---

## 📊 数据量预估

| 阶段 | 输入 | 输出 | 耗时 | 成本 |
|------|------|------|------|------|
| 阶段1: 提取 | 183K 对话 | 183K JSON | 7.6h | $38 |
| 阶段2: 消歧 | 183K JSON | 实体映射表 | 2h | - |
| 阶段3: 构图 | JSON + 映射表 | Neo4j | 1h | - |
| 阶段4: 人工干预 | 消歧报告 | 确认结果 | 用户决定 | - |

**节点预估**：
- Person: 5,000（消歧后）
- Conversation: 183,000
- Topic: 10,000
- Event: 100,000
- Location: 3,000
- Organization: 2,000

**关系预估**：
- PARTICIPATED_IN: 366,000（183K对话 × 2参与者）
- DISCUSSED: 640,000（183K对话 × 3.5 topics）
- EXPERT_IN: 15,000
- WORKS_AT: 5,000
- 其他: 500,000

**总计**：~300K 节点，~1.5M 关系

---

## 🔧 消歧的人工干预设计

### 方案A：Web界面（推荐）

```python
# Flask 应用
@app.route('/disambiguation')
def disambiguation_ui():
    ambiguous_cases = load_ambiguous_cases()
    return render_template('disambiguate.html', cases=ambiguous_cases)

@app.route('/merge_persons', methods=['POST'])
def merge_persons():
    person_ids = request.json['person_ids']
    merge_into_one(person_ids)
    return {'status': 'ok'}
```

### 方案B：命令行交互

```bash
python disambiguate.py

发现 52 个需要人工确认的案例

案例 1/52: "老张"
  候选1: 张三 (阿里, 45次提及)
  候选2: 张伟 (腾讯, 12次提及)

  [m] 合并为同一人
  [s] 保持分离
  [v] 查看详细证据
  [n] 跳过

选择: v

详细证据（候选1: 张三）:
  - 2018-05: 老张在阿里做推荐系统
  - 2019-03: 和老张讨论机器学习
  - 2019-11: 老张升职了
  ...

详细证据（候选2: 张伟）:
  - 2019-06: 老张转岗到腾讯
  - 2020-01: 老张做产品经理了
  ...

选择: s (保持分离，因为公司和职业都不同)
```

### 方案C：导出Excel手动标注

```python
# 导出消歧任务
export_disambiguation_tasks('disambiguation_tasks.xlsx')

# Excel格式
| 案例ID | 称呼 | 候选1 | 候选2 | 决策 |
|--------|------|-------|-------|------|
| 1 | 老张 | 张三(阿里) | 张伟(腾讯) | 分离 |
| 2 | 老婆 | 李梅(2015-18) | 王芳(2019-25) | 分离 |
| 3 | 老王 | 王五 | 王五 | 合并 |

# 导入标注结果
import_disambiguation_decisions('disambiguation_tasks.xlsx')
```

---

## ✅ 下一步行动

### 1. 立即执行（现在）

- [x] 完成方案设计
- [ ] 修改 prompt（增加 aliases、inferred_time、disambiguation_hints）
- [ ] 测试提取2个对话（"三蛋"、"北葵向暖"）
- [ ] 评估提取质量

### 2. 短期目标（本次会话）

- [ ] 确认提取质量满意
- [ ] 开始全量提取（183K 对话）

### 3. 中期目标（后续）

- [ ] 实现自动消歧算法
- [ ] 构建人工干预界面
- [ ] 完成实体消歧
- [ ] 构建 Neo4j 图谱

### 4. 长期目标

- [ ] 图谱查询API
- [ ] 可视化界面
- [ ] 智能问答系统

---

## 🎯 成功标准

**阶段1（提取）成功标准**：
- ✅ 成功率 ≥ 95%
- ✅ 平均每对话提取 10-15 个实体
- ✅ Relationships 覆盖主要关系
- ✅ 时间推断准确率 ≥ 80%

**阶段2（消歧）成功标准**：
- ✅ 自动聚类准确率 ≥ 85%
- ✅ 需要人工干预的案例 < 100 个
- ✅ Person 节点去重率 ≥ 95%（360K 提及 → 5K 人物）

**阶段3（图谱）成功标准**：
- ✅ 图谱可查询
- ✅ 典型查询响应时间 < 1秒
- ✅ 支持所有设计的查询场景

---

*方案版本: v2.0*
*最后更新: 2026-02-26*
