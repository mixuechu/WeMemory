# 检索模块 (retrieval)

## 功能
提供向量存储和混合检索能力（BM25 + 向量检索）

## 模块结构

```
retrieval/
├── __init__.py         # 模块导出
├── vector_store.py     # 双向量存储
├── hybrid.py           # 混合检索
└── README.md           # 本文档
```

## 核心类

### 1. SimpleVectorStore (vector_store.py)
双向量存储和检索

**特性**：
- 支持内容向量 + 上下文向量分离存储
- 检索时加权组合（content 85% + context 15%）
- 支持时间、参与者过滤

**使用方法**：
```python
from retrieval import SimpleVectorStore

# 1. 创建向量库
store = SimpleVectorStore(dimension=768)

# 2. 添加向量
store.add(
    content_embedding=[...],  # 768维
    context_embedding=[...],  # 768维
    metadata={
        'session_id': '...',
        'start_timestamp': 1234567890,
        'participants': ['张三', '李四'],
        'content_text': '对话内容...'
    }
)

# 3. 保存向量库
store.save("vector_stores/my_conversation.pkl")

# 4. 加载向量库
store.load("vector_stores/my_conversation.pkl")

# 5. 检索
results = store.search(
    query_content_embedding=[...],
    query_context_embedding=[...],  # 可选
    top_k=5,
    filters={'time_range': (start_ts, end_ts)},  # 可选
    content_weight=0.85,
    context_weight=0.15
)

for result in results:
    print(f"得分: {result['score']:.3f}")
    print(f"内容: {result['metadata']['content_text']}")
```

### 2. HybridVectorStore (hybrid.py)
混合检索向量库 - 组合BM25和向量检索

**特性**：
- 关键词匹配（BM25）+ 语义相似度（向量）
- 权重配比：BM25:0.5 + Vector:0.5（经过评测得出最佳配比）
- 使用jieba进行中文分词

**使用方法**：
```python
from retrieval import HybridVectorStore
from embedding import GoogleEmbeddingClient

# 1. 加载向量库
store = HybridVectorStore(dimension=768)
store.load("vector_stores/my_conversation.pkl")

# 2. 构建BM25索引
store.build_bm25_index()

# 3. 初始化embedding客户端
client = GoogleEmbeddingClient()

# 4. 混合检索
query = "我们讨论过AI的话题吗"
query_embedding = client.get_embeddings([query])[0]

results = store.hybrid_search(
    query_content_embedding=query_embedding,
    query_text=query,  # BM25需要原始文本
    top_k=5,
    bm25_weight=0.5,  # 推荐值
    vector_weight=0.5
)

for result in results:
    print(f"混合分: {result['score']:.3f}")
    print(f"  - BM25: {result['bm25_score']:.3f}")
    print(f"  - 向量: {result['vector_score']:.3f}")
    print(f"内容: {result['metadata']['content_text'][:100]}...")
```

## 权重配比说明

经过系统评测（见 `evaluation/README.md`），我们在以下配比中测试：
- BM25:0.3 + Vector:0.7
- BM25:0.5 + Vector:0.5  ← **推荐**
- BM25:0.7 + Vector:0.3
- BM25:0.9 + Vector:0.1

### 评测结果

| 权重配比 | 有意义查询得分 | 同义词查询得分 | 综合平均 |
|---------|-------------|-------------|---------|
| BM25:0.3 Vector:0.7 | 8.93 | 6.33 | 7.78 |
| **BM25:0.5 Vector:0.5** | **8.87** | **6.92** | **8.00** 🏆 |
| BM25:0.7 Vector:0.3 | 6.80 | 6.83 | 6.81 |
| BM25:0.9 Vector:0.1 | 6.80 | 6.92 | 6.85 |

**结论**：BM25:0.5 + Vector:0.5 综合表现最佳

### 为什么选择 0.5:0.5？
1. **平衡性好**：兼顾关键词匹配和语义理解
2. **避免极端失败**：不像高BM25权重那样出现完全错误的结果
3. **稳定可靠**：在直接查询和同义词查询中都表现优秀

## 过滤器

支持两种过滤条件：

### 1. 时间范围过滤
```python
results = store.search(
    query_embedding,
    filters={
        'time_range': (start_timestamp, end_timestamp)
    }
)
```

### 2. 参与者过滤
```python
results = store.search(
    query_embedding,
    filters={
        'participants': ['张三', '李四']  # 包含任一参与者的对话
    }
)
```

### 3. 组合过滤
```python
results = store.search(
    query_embedding,
    filters={
        'time_range': (start_ts, end_ts),
        'participants': ['张三']
    }
)
```

## 依赖关系
- **依赖**: `embedding` 模块（使用embeddings）
- **被依赖**: 应用层（检索服务）

## 性能优化
1. **BM25索引**：一次构建，多次使用
2. **Numpy向量化**：批量计算相似度
3. **过滤器先行**：减少排序数量

## 未来扩展
1. 支持更多检索算法（如ES、Milvus等）
2. 支持重排序（reranking）
3. 支持查询扩展
4. 支持多模态检索（图片、语音等）
