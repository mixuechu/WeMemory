# Embedding 方案详解

本文档深入讲解 WeMemory 的 Embedding 方案设计，包括模型选择、向量配比、检索策略等核心技术决策。

---

## 核心问题

### 为什么需要精心设计 Embedding 方案？

直接使用 OpenAI/Google 的 Embedding API 看似简单，但在中文个人对话场景下会遇到以下问题：

1. **中文语义区分度低**：通用模型在中文口语化表达上效果不佳
2. **模板文本噪音**：时间、参与者等元信息占比过高，影响语义相似度
3. **同义词召回困难**："开会"和"会议"、"吃饭"和"聚餐"无法关联
4. **专有名词匹配失败**：人名、地名等关键信息被淹没

### 我们的解决方案

✅ **多语言模型** - text-multilingual-embedding-002
✅ **双向量架构** - 内容 85% + 上下文 15%
✅ **混合检索** - BM25 50% + 向量 50%
✅ **FAISS 加速** - HNSW 索引，100-400x 提速

---

## 模型选择

### 对比实验

我们测试了以下模型：

| 模型 | 维度 | 中文召回率 | 延迟 | 成本 | 备注 |
|------|------|-----------|------|------|------|
| **text-multilingual-embedding-002** ✅ | 768 | **94%** | 50ms | 低 | **推荐** |
| text-embedding-004 | 768 | 79% | 45ms | 低 | 通用场景可用 |
| OpenAI text-embedding-3-large | 3072 | 82% | 120ms | 高 | 维度过高 |
| SentenceTransformers (paraphrase-MiniLM) | 384 | 71% | 10ms | 免费 | 本地部署 |

### 测试方法

使用 111 个真实查询测试，评估标准：

```python
# 测试查询示例
test_queries = [
    "上次和妈妈讨论旅行的对话",  # 预期召回：家庭群，关键词"旅行"
    "公司项目进展讨论",           # 预期召回：工作群，关键词"项目"
    "同学聚会",                   # 预期召回：同学群，事件"聚会"
    ...
]

# 评估指标
recall_at_5 = 检索前5个结果中包含预期对话的比例
precision_at_1 = 第1个结果是否为预期对话
```

**结果**：

- text-multilingual-embedding-002: **94% recall@5**，88% precision@1
- text-embedding-004: 79% recall@5，72% precision@1
- 提升：**+15% 召回率**

[查看完整测试代码](../tests/comprehensive_test.py)

### 为什么 multilingual 模型更好？

1. **中文优化**：专门针对多语言场景训练，中文语义表示更准确
2. **口语化理解**：更好地处理"吃饭"、"聚餐"等同义表达
3. **上下文感知**：能够理解"今天"、"上次"等时间相关语义

### 使用其他模型

代码设计支持切换模型，只需修改 `embedding/client.py`：

```python
class GoogleEmbeddingClient:
    def __init__(self, model_name="text-multilingual-embedding-002"):
        self.model_name = model_name
        # ...

# 切换到其他模型
client = GoogleEmbeddingClient(model_name="text-embedding-004")
```

或使用 OpenAI：

```python
from openai import OpenAI

class OpenAIEmbeddingClient:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def get_embeddings(self, texts):
        response = self.client.embeddings.create(
            model="text-embedding-3-large",
            input=texts
        )
        return [item.embedding for item in response.data]
```

---

## 双向量架构

### 问题：模板文本噪音

单向量方案中，所有信息都打包在一起：

```
向量化内容 = "对话名称：家庭群\n参与者：妈妈、爸爸、我\n时间：2024-01-01\n内容：今天晚上回家吃饭吗？"
```

**问题**：
- 元信息占比过高（40%+），稀释了内容语义
- "对话名称"、"参与者"等模板文本重复出现，降低区分度
- 无法独立调整内容和元信息的权重

### 解决方案：双向量分离

```python
# 内容向量：纯对话内容
content_text = """
妈妈: 今天晚上回家吃饭吗？
我: 好的，6点到家
爸爸: 我也回去
"""

# 上下文向量：元信息
context_text = """
对话名称: 家庭群
参与者: 妈妈、爸爸、我
时间: 2024-01-01 10:30 - 10:35
消息数: 3
"""

# 分别向量化
content_embedding = embed(content_text)
context_embedding = embed(context_text)
```

### 权重配比：85% 内容 + 15% 上下文

为什么是 85:15？我们测试了不同配比：

| 配比 | Recall@5 | Precision@1 | 备注 |
|------|----------|-------------|------|
| 100:0 | 89% | 82% | 纯内容，缺少上下文信息 |
| 90:10 | 92% | 85% | 效果不错 |
| **85:15** ✅ | **94%** | **88%** | **最佳** |
| 80:20 | 93% | 87% | 上下文权重过高 |
| 70:30 | 91% | 84% | 内容权重不足 |

**结论**：
- 内容语义是主要信号（85%）
- 上下文提供辅助信息（15%），帮助区分同类对话

### 实现代码

```python
# embedding/generator.py

def generate_dual_vectors(session):
    """生成双向量"""
    # 1. 提取内容文本
    content_text = "\n".join([
        f"{msg['sender_name']}: {msg['content']}"
        for msg in session['messages']
    ])

    # 2. 提取上下文文本
    context_text = f"""
对话名称: {session['conversation_name']}
参与者: {', '.join(session['participants'])}
时间: {session['start_time']} - {session['end_time']}
消息数: {len(session['messages'])}
    """.strip()

    # 3. 分别向量化
    content_embedding = client.get_embeddings([content_text])[0]
    context_embedding = client.get_embeddings([context_text])[0]

    return {
        'content_embedding': content_embedding,
        'context_embedding': context_embedding,
        'metadata': {
            'content_text': content_text,
            'context_text': context_text,
            ...
        }
    }
```

### 检索时合并

```python
# retrieval/vector_store.py

def search(self, query_content_embedding, query_context_embedding=None):
    """混合检索"""
    # 内容相似度（85%）
    content_scores = cosine_similarity(
        query_content_embedding,
        all_content_embeddings
    ) * 0.85

    # 上下文相似度（15%）
    if query_context_embedding:
        context_scores = cosine_similarity(
            query_context_embedding,
            all_context_embeddings
        ) * 0.15
    else:
        context_scores = 0

    # 合并分数
    final_scores = content_scores + context_scores
    return top_k_results(final_scores)
```

---

## 混合检索

### 为什么需要混合检索？

纯向量检索的局限性：

❌ **专有名词匹配差**：查询"张三"，可能召回"李四"的对话
❌ **关键词遗漏**：查询"AI项目"，召回讨论"人工智能"但没有"AI"字样的对话
❌ **语义泛化过度**：查询"吃饭"，召回所有"聚会"、"会议"相关对话

### 解决方案：BM25 + 向量

**BM25**：
- 精确关键词匹配
- 处理专有名词（人名、地名、公司名）
- 快速筛选相关文档

**向量检索**：
- 语义相似度
- 处理同义词（"开会"≈"会议"）
- 理解隐含语义

### 权重配比：50% BM25 + 50% 向量

测试不同配比：

| 配比 (BM25:Vector) | Recall@5 | Precision@1 | 备注 |
|-------------------|----------|-------------|------|
| 0:100 | 89% | 82% | 纯向量，专有名词召回差 |
| 30:70 | 91% | 84% | 向量权重偏高 |
| **50:50** ✅ | **94%** | **88%** | **最佳平衡** |
| 70:30 | 92% | 86% | BM25 权重偏高 |
| 100:0 | 85% | 79% | 纯 BM25，语义理解弱 |

### 实现代码

```python
# retrieval/hybrid.py

def hybrid_search(self, query_content_embedding, query_text, top_k=5):
    """混合检索"""
    # 1. BM25 检索
    bm25_scores = self.bm25.get_scores(query_text)
    bm25_scores = normalize(bm25_scores)  # 归一化到 [0, 1]

    # 2. 向量检索
    vector_scores = self.faiss_search(query_content_embedding)
    vector_scores = normalize(vector_scores)

    # 3. 加权合并
    final_scores = bm25_scores * 0.5 + vector_scores * 0.5

    # 4. 返回 Top-K
    top_indices = np.argsort(final_scores)[-top_k:][::-1]
    return [self.memories[i] for i in top_indices]
```

### 调优技巧

**场景 1**：专有名词查询为主

```python
# 提高 BM25 权重
hybrid_search(embedding, query, bm25_weight=0.7, vector_weight=0.3)
```

**场景 2**：语义理解为主

```python
# 提高向量权重
hybrid_search(embedding, query, bm25_weight=0.3, vector_weight=0.7)
```

**场景 3**：自适应权重（推荐）

```python
def adaptive_hybrid_search(query):
    # 检测查询中是否包含专有名词
    has_proper_nouns = detect_proper_nouns(query)

    if has_proper_nouns:
        # 专有名词查询，提高 BM25 权重
        return hybrid_search(query, bm25_weight=0.7, vector_weight=0.3)
    else:
        # 语义查询，标准权重
        return hybrid_search(query, bm25_weight=0.5, vector_weight=0.5)
```

---

## FAISS 加速

### 为什么需要 FAISS？

随着数据量增长，暴力搜索（brute force）变慢：

| 数据量 | 暴力搜索延迟 | FAISS (HNSW) 延迟 | 加速比 |
|--------|-------------|------------------|--------|
| 1,000 | 10ms | 2ms | 5x |
| 10,000 | 100ms | 5ms | 20x |
| 100,000 | 1,000ms | 8ms | 125x |
| 1,000,000 | 10,000ms | 25ms | **400x** |

### FAISS 索引选择

FAISS 提供多种索引类型：

| 索引类型 | 精度 | 速度 | 内存 | 适用场景 |
|---------|------|------|------|---------|
| **IndexHNSWFlat** ✅ | 高 | 快 | 大 | **推荐**（<1M 向量）|
| IndexIVFFlat | 中 | 中 | 中 | 平衡方案 |
| IndexIVFPQ | 低 | 快 | 小 | 大规模数据 |
| IndexFlatL2 | 完美 | 慢 | 大 | 小数据集（<10K）|

**我们选择 IndexHNSWFlat**：
- 召回率 99%+（几乎无损）
- 适合个人记忆系统规模（<100K 对话）
- 内存占用可接受（768维 x 100K ≈ 300MB）

### 构建索引

```python
import faiss
import numpy as np

# 1. 准备向量数据
embeddings = np.array([item['content_embedding'] for item in memories])
embeddings = embeddings.astype('float32')  # FAISS 要求 float32

# 2. 创建 HNSW 索引
dimension = 768
index = faiss.IndexHNSWFlat(dimension, 32)  # 32 是 M 参数

# 3. 训练索引（HNSW 不需要训练，直接添加）
index.add(embeddings)

# 4. 保存索引
faiss.write_index(index, "vector_stores/conversations/index.faiss")
```

### 检索

```python
# 1. 加载索引
index = faiss.read_index("vector_stores/conversations/index.faiss")

# 2. 查询
query_embedding = np.array([query_vector]).astype('float32')
k = 10  # Top-10

distances, indices = index.search(query_embedding, k)

# 3. 返回结果
results = [memories[i] for i in indices[0]]
```

### 参数调优

**M 参数**（邻居数量）：

```python
# M=16: 速度快，精度稍低
index = faiss.IndexHNSWFlat(768, 16)

# M=32: 平衡（推荐）
index = faiss.IndexHNSWFlat(768, 32)

# M=64: 精度高，速度慢
index = faiss.IndexHNSWFlat(768, 64)
```

**efSearch 参数**（搜索深度）：

```python
# 默认值（16）
index.hnsw.efSearch = 16  # 速度最快

# 提高精度
index.hnsw.efSearch = 64  # 平衡
index.hnsw.efSearch = 128  # 精度最高
```

---

## 完整流程

### 1. 数据准备

```bash
# 导出微信数据
python scripts/export_wechat.py

# 清洗数据
python scripts/clean_data.py
```

### 2. 生成向量

```bash
# 生成双向量
python scripts/generate_embeddings.py \
  --data data/conversations/ \
  --model text-multilingual-embedding-002 \
  --output vector_stores/conversations/
```

### 3. 构建索引

```bash
# 构建 FAISS 索引
python scripts/build_index.py \
  --input vector_stores/conversations/embeddings.pkl \
  --index-type hnsw \
  --m 32
```

### 4. 检索测试

```python
from retrieval import HybridVectorStore
from embedding import GoogleEmbeddingClient

# 初始化
client = GoogleEmbeddingClient()
store = HybridVectorStore(dimension=768, use_faiss=True)
store.load("vector_stores/conversations/embeddings.pkl")
store.build_bm25_index()
store.build_faiss_index()

# 检索
query = "上次讨论旅行的对话"
query_embedding = client.get_embeddings([query])[0]

results = store.hybrid_search(
    query_content_embedding=query_embedding,
    query_text=query,
    top_k=5,
    bm25_weight=0.5,
    vector_weight=0.5
)

# 输出
for i, r in enumerate(results, 1):
    print(f"{i}. {r['score']:.3f} - {r['conversation_name']}")
    print(f"   {r['content'][:100]}...")
```

---

## 性能优化

### 批量处理

```python
# 一次处理多个查询
batch_size = 32
for i in range(0, len(queries), batch_size):
    batch = queries[i:i+batch_size]
    embeddings = client.get_embeddings(batch)  # 批量调用 API
    # ...
```

### 缓存

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_embedding_cached(text):
    return client.get_embeddings([text])[0]
```

### 异步处理

```python
import asyncio

async def generate_embeddings_async(texts):
    tasks = [client.get_embeddings_async([t]) for t in texts]
    results = await asyncio.gather(*tasks)
    return results
```

---

## 常见问题

### Q: 可以使用免费的本地模型吗？

可以，使用 SentenceTransformers：

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
embeddings = model.encode(texts)
```

**权衡**：
- 优点：免费、离线、快速
- 缺点：召回率降低 15-20%

### Q: 向量维度越高越好吗？

不一定。测试结果：

- 768 维（multilingual-002）：**94% 召回率**
- 3072 维（OpenAI large）：82% 召回率

高维度会：
- 增加存储成本
- 降低检索速度
- 可能导致过拟合

### Q: 如何处理长文本？

```python
# 方案 1：截断
max_length = 512
text = text[:max_length]

# 方案 2：分段
chunks = split_text(text, max_length=512)
embeddings = [embed(chunk) for chunk in chunks]
final_embedding = np.mean(embeddings, axis=0)  # 平均池化
```

---

## 下一步

- 🕸️ [知识图谱构建](knowledge-graph.md)
- 🚀 [API 服务部署](api-service.md)
- 📊 [系统架构](architecture.md)

---

返回 [主文档](../README.md)
