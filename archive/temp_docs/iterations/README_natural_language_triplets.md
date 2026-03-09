# 自然语言三元组 v1

生成时间: 2026-03-06

## 🎯 设计理念

**核心思想**：用自然语言描述代替图谱关系，配合向量检索实现统一的知识获取。

### 为什么不用Neo4j图谱？

| 对比项 | Neo4j图谱 | 自然语言三元组 + FAISS |
|--------|-----------|----------------------|
| **查询方式** | Cypher查询语言 | 自然语言向量检索 |
| **部署复杂度** | 需要数据库服务 | 本地文件 + FAISS |
| **语义灵活性** | 需要精确匹配关系类型 | 模糊语义匹配 |
| **时间表达** | 需要额外事件节点 | 直接在文本中 |
| **维护成本** | 需要写Cypher更新 | 重建索引 |
| **适用场景** | 复杂图遍历查询 | 个人助理问答 |

**结论**：对于"个人助理"场景，**自然语言三元组**更简单、更灵活、更适合。

## 📊 数据统计

| 项目 | 数量 |
|------|------|
| 关系三元组 | 2,568条 |
| 事件描述 | 5,297条 |
| 总记录数 | 7,865条 |
| 文件大小 | 3.69 MB |

## 📝 数据结构

### 1. 关系三元组示例

```json
{
  "id": "rel_00001",
  "type": "relationship",
  "text": "赵萌是米雪川的配偶",
  "metadata": {
    "subject": "米雪川",
    "relation_type": "HAS_SPOUSE",
    "object": "赵萌",
    "object_type": "Person",
    "conversation": "妈",
    "context": "双方父母通过媒人商量婚事..."
  }
}
```

**自然语言表达**：
- "赵萌是米雪川的配偶"
- "米雪川在acrossor.com工作"
- "柴英杰是米雪川的表哥"
- "米雪川位于北京"

### 2. 事件描述示例

```json
{
  "id": "evt_00001",
  "type": "event",
  "text": "2016年12月9日，米雪川参加了一场考试",
  "metadata": {
    "event_name": "米雪川的考试",
    "event_type": "教育事件",
    "time_description": "2016年12月9日",
    "participants": ["米雪川"],
    "conversation": "外婆",
    "related_entity": "米雪川"
  }
}
```

**自然语言表达**：
- "2016年12月9日，米雪川参加了一场考试"
- "2025年3月，沈超和米雪川讨论了大模型项目"
- "今天一点半，小冉敏将要参加一个会议"

## 🔧 生成方法

### 当前版本：规则模板（v1）

**关系三元组**：使用预定义模板
```python
templates = {
    'HAS_SPOUSE': "{object}是{subject}的配偶",
    'WORKS_AT': "{subject}在{object}工作",
    'HAS_PARENT': "{object}是{subject}的父母"
}
```

**事件描述**：拼接时间、参与者、描述
```python
"{time_description}，{participants}：{description}"
```

**优点**：
- ⚡ 快速：1秒生成全部
- 💰 免费：无API调用
- 🎯 确定：格式统一

**缺点**：
- 语言相对机械
- 缺少上下文丰富性

### 可选：LLM增强（v2）

如果检索效果不够好，可以用LLM重新生成部分记录。

**适合LLM增强的场景**：
1. 复杂事件描述（参与者多、上下文丰富）
2. 需要融入context字段的关系
3. 需要更自然的表达

**示例**：
```python
# 规则版本
"2025年3月6日，米雪川, 赵萌：参加婚礼"

# LLM增强版本
"2025年3月6日，米雪川和妻子赵萌一起参加了朋友的婚礼，这是他们结婚后第一次正式社交活动"
```

## 🚀 使用方式

### 1. 向量化

```python
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import json

# 加载数据
with open('natural_language_triplets.json', 'r') as f:
    data = json.load(f)

records = data['records']

# 提取文本
texts = [r['text'] for r in records]

# 向量化
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
embeddings = model.encode(texts, show_progress_bar=True)

# 构建FAISS索引
dimension = embeddings.shape[1]
index = faiss.IndexFlatIP(dimension)  # 内积相似度
faiss.normalize_L2(embeddings)  # 归一化
index.add(embeddings)

# 保存
faiss.write_index(index, 'knowledge_base.index')
with open('knowledge_base_records.json', 'w') as f:
    json.dump(records, f, ensure_ascii=False)
```

### 2. 检索

```python
# 查询
query = "我老婆是谁？"
query_embedding = model.encode([query])
faiss.normalize_L2(query_embedding)

# 搜索
k = 5
distances, indices = index.search(query_embedding, k)

# 结果
for i, idx in enumerate(indices[0]):
    record = records[idx]
    print(f"{i+1}. {record['text']} (相似度: {distances[0][i]:.3f})")
```

**输出示例**：
```
1. 赵萌是米雪川的配偶 (相似度: 0.892)
2. 米雪川和赵萌一起回宝鸡 (相似度: 0.756)
3. 赵萌的妈妈是米雪川的未来岳母 (相似度: 0.698)
```

### 3. 混合检索（推荐）

结合对话原文：
```python
# 索引三种数据源
sources = {
    'triplets': natural_language_triplets,  # 结构化知识
    'events': event_descriptions,           # 事件记录
    'conversations': conversation_chunks    # 对话原文
}

# 查询时搜索所有源，按相似度排序
results = search_all_sources(query, k=10)
```

## 🎯 应用场景

### 1. 关系查询
```
Q: "我老婆是谁？"
A: 赵萌是米雪川的配偶

Q: "我在哪工作？"
A: 米雪川在acrossor.com工作

Q: "我家人有谁？"
A: [检索到所有家庭关系三元组]
```

### 2. 事件查询
```
Q: "我上次考试是什么时候？"
A: 2016年12月9日，米雪川参加了一场考试

Q: "我和沈超聊过什么？"
A: [检索到相关事件和对话]
```

### 3. 语义检索
```
Q: "我的亲人有谁？"
→ 自动匹配：配偶、父母、孩子、兄弟姐妹...

Q: "我的同事们"
→ 自动匹配：IS_COLLEAGUE_OF关系
```

## 📈 后续优化方向

### 阶段1: 规则版本验证（当前）
- ✅ 快速生成全部数据
- ✅ 测试检索效果
- ✅ 识别问题记录

### 阶段2: LLM选择性增强
- 对检索效果差的记录用LLM重新生成
- 融入更多上下文信息
- A/B测试对比效果

### 阶段3: 动态更新
- 新对话 → 自动提取三元组
- 增量更新FAISS索引
- 保持知识库最新

## 📁 文件说明

- **natural_language_triplets.json** (3.69 MB)
  - 包含所有关系三元组和事件描述
  - 规则生成，格式统一

- **curated_knowledge_graph_v3.1.json** (3.54 MB)
  - 源数据（关系剪枝后）
  - 如需重新生成可以基于此文件

## ✨ 优势总结

1. **简单部署** - 不需要Neo4j，只需FAISS
2. **统一检索** - 关系、事件、对话都用向量检索
3. **语义灵活** - "我老婆"、"我妻子"、"我配偶"都能匹配
4. **易于维护** - 重建索引即可，无需复杂的图更新
5. **成本低廉** - 本地运行，无额外服务费用

适合"个人助理"这种需要灵活语义理解、不需要复杂图遍历的应用场景。
