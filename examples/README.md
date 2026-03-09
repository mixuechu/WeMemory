# 使用示例

本目录包含微信记忆系统的使用示例。

## 前提条件

1. 已配置 `.env` 文件（参考根目录的 `.env.example`）
2. 已生成向量库文件 `vector_stores/conversations.pkl`

如果还没有生成向量库，请运行：
```bash
python scripts/generate_embeddings.py --excel your_data.xlsx
```

## 示例列表

### 1. basic_usage.py - 基本使用

演示三种常见使用场景：

#### 示例 1: 基本搜索
```python
# 加载向量库并执行简单搜索
vs = HybridVectorStore(dimension=768, use_faiss=True)
vs.load("vector_stores/conversations.pkl")

# 构建索引
vs.build_bm25_index()
vs.build_faiss_index()

# 搜索
results = vs.hybrid_search(
    query_content_embedding=query_embedding,
    query_text="讨论 AI 项目的对话",
    top_k=5
)
```

#### 示例 2: 高级搜索（带过滤）
```python
# 按时间范围和参与者过滤
filters = {
    'time_range': (start_timestamp, end_timestamp),
    'participants': ['Alice', 'Bob']
}

results = vs.hybrid_search(
    query_content_embedding=query_embedding,
    query_text="项目进展",
    filters=filters
)
```

#### 示例 3: 自定义权重
```python
# 调整 BM25 和向量搜索的权重
results = vs.hybrid_search(
    query_content_embedding=query_embedding,
    query_text="开会时间",
    bm25_weight=0.8,  # 关键词优先
    vector_weight=0.2
)
```

## 运行示例

```bash
# 激活虚拟环境
source venv_embedding/Scripts/activate  # Windows Git Bash
# 或
source venv_embedding/bin/activate      # Linux/Mac

# 运行基本示例
python examples/basic_usage.py
```

## 扩展阅读

- 完整文档: `README_VECTOR_SYSTEM.md`
- 脚本使用: `scripts/README.md`
- API 文档: `docs/` 目录
