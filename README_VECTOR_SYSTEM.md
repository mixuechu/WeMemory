# 微信记忆系统 - 向量检索系统

基于 Google Vertex AI + FAISS 的微信聊天记录语义检索系统。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      微信聊天记录                             │
│                   (Excel导出，698个对话)                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  会话切分 (Session Splitting)                                │
│  - 滑动窗口: 30分钟gap                                        │
│  - 消息数量: 3-20条                                          │
│  - 边界重叠: 避免信息丢失                                     │
│  ▶ 183,287个会话片段                                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  文本富化 (Text Enrichment)                                  │
│  - Content文本: 消息内容 + 时间戳 + 发送者                    │
│  - Context文本: 对话名称 + 参与者 + 时间范围                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  向量生成 (Embedding Generation)                             │
│  - Google text-embedding-004 (768维)                        │
│  - 动态Batch: 基于token数 (<19,000/batch)                   │
│  - 双向量: Content(85%) + Context(15%)                      │
│  - 分片保存: 每个对话独立保存                                 │
│  ▶ 183,287 × 2 = 366,574个向量                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  索引构建 (Index Building)                                   │
│  - BM25: 关键词匹配索引                                      │
│  - FAISS HNSW: 向量近似检索索引                              │
│  - 自动切换: >=5000条启用FAISS                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  混合检索 (Hybrid Retrieval)                                 │
│  - Score = 0.5×BM25 + 0.5×Vector                           │
│  - Vector = 0.85×Content + 0.15×Context                    │
│  - 性能: <100ms/查询 (FAISS加速)                             │
└─────────────────────────────────────────────────────────────┘
```

## 核心特性

### 1. 双层向量架构
```python
Content向量 (85%权重):
  "2024-02-15 14:30 [张三]: 明天下午2点开会讨论AI项目进展"
  ▶ 768维语义向量

Context向量 (15%权重):
  "对话: AI项目组 | 参与者: 张三, 李四 | 时间: 2024-02-15"
  ▶ 768维上下文向量

混合分数:
  0.85 × cos(query, content) + 0.15 × cos(query, context)
```

### 2. 动态Batch策略
```python
问题: 固定batch_size=250 → token超限 → API错误
解决: 动态累积直到接近19,000 tokens

示例:
  Session 1: 15,000 tokens → Batch 1: [S1]
  Session 2: 3,000 tokens  → Batch 1: [S1, S2]
  Session 3: 2,000 tokens  → Batch 2: [S3]  (S1+S2+S3 > 19K)

结果: 100%成功率，0个零向量
```

### 3. 分片保存策略
```python
问题: 全量加载 → 2.3GB内存 → OOM
解决: 每个对话独立保存为shard

流程:
  1. 处理对话1 → 保存 shard_0000.pkl → 释放内存
  2. 处理对话2 → 保存 shard_0001.pkl → 释放内存
  ...
  698. 处理对话698 → 保存 shard_0697.pkl → 释放内存

  最后: 合并所有shard → conversations.pkl

优势: 内存稳定1.5GB，支持增量更新
```

### 4. 混合检索
```python
查询: "AI相关的讨论"

BM25分数 (关键词):
  - Session A: 0.8  (包含"AI", "讨论")
  - Session B: 0.3  (只包含"讨论")

Vector分数 (语义):
  - Session A: 0.6  (内容相关)
  - Session B: 0.9  (高度相关但用词不同)

混合分数:
  - Session A: 0.5×0.8 + 0.5×0.6 = 0.70
  - Session B: 0.5×0.3 + 0.5×0.9 = 0.60

排序: [Session A, Session B]
```

## 快速开始

### 1. 环境准备
```bash
# 安装依赖
pip install -r requirements.txt

# 配置Google Cloud（.env文件）
GOOGLE_PROJECT_ID=your-project-id
GOOGLE_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
```

### 2. 生成向量库
```bash
# 激活虚拟环境
source venv_embedding/Scripts/activate

# 生成embeddings（首次运行）
python scripts/generate_embeddings.py --excel 聊天记录excel/messages.xlsx

# 预计耗时: ~80分钟（698个对话）
# 内存占用: ~1.5GB
# 最终文件: vector_stores/conversations.pkl (1.94GB)
```

### 3. 测试搜索
```bash
# 测试向量库
python scripts/test_search.py

# 输出示例:
# 查询: 'AI相关的讨论'
#   1. 对话: 项目组讨论
#      分数: 0.638 (BM25:0.412, Vector:0.864)
#      内容: 明天讨论AI模型的优化方案...
```

### 4. 在代码中使用
```python
from retrieval import HybridVectorStore
from embedding import GoogleEmbeddingClient

# 加载向量库
vs = HybridVectorStore(dimension=768, use_faiss=True)
vs.load("vector_stores/conversations.pkl")

# 构建索引（首次使用）
vs.build_bm25_index()
vs.build_faiss_index()

# 搜索
client = GoogleEmbeddingClient()
query_vec = client.get_embeddings(["你的查询"])[0]

results = vs.hybrid_search(
    query_content_embedding=query_vec,
    query_text="你的查询",
    top_k=5
)

for r in results:
    print(f"分数: {r['score']:.3f}")
    print(f"内容: {r['metadata']['content_text'][:100]}")
```

## 性能指标

基于实际数据（698个对话，183,287个sessions）：

| 指标 | 数值 |
|-----|------|
| **生成时间** | 80分钟 |
| **API调用** | ~1,200次 |
| **成功率** | 100% |
| **内存峰值** | 1.5GB |
| **最终文件** | 1.94GB |
| **搜索延迟** | <100ms |
| **FAISS加速** | 100-400x |
| **召回率** | 95-99% (HNSW) |

## 目录结构

```
.
├── scripts/                      # 正式脚本
│   ├── generate_embeddings.py   # 生成向量库
│   ├── test_search.py            # 测试搜索
│   ├── README.md                 # 使用指南
├── embedding/                    # 向量生成模块
│   ├── client.py                 # Google API客户端
│   ├── generator.py              # 双向量生成器（动态batch）
│   └── enricher.py               # 文本富化
├── retrieval/                    # 检索模块
│   ├── hybrid.py                 # 混合检索（BM25+FAISS）
│   └── vector_store.py           # 基础向量库
├── data_loader/                  # 数据加载模块
│   ├── session.py                # 会话切分器（滑动窗口）
│   ├── loader.py                 # Excel加载器
│   └── models.py                 # 数据模型
├── vector_stores/                # 向量库存储
│   ├── conversations.pkl         # 最终向量库
│   └── shards/                   # 分片文件（保留）
├── logs/                         # 日志文件
└── README_VECTOR_SYSTEM.md       # 本文件
```

## 技术栈

- **Embedding**: Google Vertex AI text-embedding-004 (768维)
- **向量索引**: FAISS HNSW (M=32)
- **关键词索引**: BM25Okapi + jieba分词
- **数据存储**: Pickle (未来可迁移到向量数据库)
- **语言**: Python 3.10+

## 最佳实践总结

经过两天迭代，确定的最佳实践：

1. ✅ **双层向量**: Content(85%) + Context(15%)
2. ✅ **滑动窗口分片**: 30分钟gap, 3-20条消息
3. ✅ **动态Batch**: 基于token数，避免API限制
4. ✅ **分片保存**: 避免OOM，支持增量更新
5. ✅ **混合检索**: BM25(0.5) + Vector(0.5)
6. ✅ **FAISS优化**: 大规模数据自动启用

## 问题排查

### OOM错误
```bash
# 问题: 内存不足
# 原因: 使用了旧脚本（累积所有数据）
# 解决: 使用 scripts/generate_embeddings.py（分片策略）
```

### Token超限错误
```bash
# 问题: API报错 "token count is 35443 but supports up to 20000"
# 原因: 使用了固定batch_size
# 解决: 使用 scripts/generate_embeddings.py（动态batch）
```

### 搜索无结果
```bash
# 问题: 搜索返回空
# 检查1: 索引是否构建（build_bm25_index, build_faiss_index）
# 检查2: 查询向量是否正确生成
# 检查3: 是否有零向量（检查生成日志）
```

## 开发历史

- **Day 1 早期**: 首次生成 → OOM失败
- **Day 1 中期**: 分片策略 → 46.41%零向量（token超限）
- **Day 2 早期**: 固定batch修复 → 继续失败
- **Day 2 中期**: 动态batch → 100%成功
- **Day 2 晚期**: 整合所有最佳实践到正式代码


## 许可证

内部项目，未开源。

## 联系方式

