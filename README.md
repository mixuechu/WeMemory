# 微信记忆系统

基于 Google Vertex AI + FAISS 的微信聊天记录语义检索系统

## 项目简介

这是一个模块化、可扩展的记忆系统服务，将微信聊天记录转换为向量知识库，提供强大的语义检索能力。

### 核心特性

- ✅ **双向量架构**：内容向量（85%）+ 上下文向量（15%），提升区分度
- ✅ **混合检索**：BM25（50%）+ 向量检索（50%），平衡关键词匹配和语义理解
- ✅ **智能切分**：混合滑动窗口策略，生成主 sessions + 边界 overlaps
- ✅ **动态 Batch**：基于 token 数动态调整批处理，避免 API 限制
- ✅ **FAISS 加速**：HNSW 索引实现 100-400x 搜索加速
- ✅ **分片保存**：内存友好的增量式处理，支持大规模数据

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- `google-cloud-aiplatform` - Google Vertex AI Embedding
- `faiss-cpu` - 向量索引加速
- `rank-bm25` - BM25 关键词检索
- `jieba` - 中文分词

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入你的配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：
```
VITE_GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_REGION=us-central1
VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}
```

### 3. 准备数据

将微信聊天记录导出为 Excel 文件，放在 `聊天记录excel/` 目录下。

格式要求：
- 必需列：`content`（消息内容）、`timestamp`（时间戳）、`sender_name`（发送者）
- 可选列：`conversation_name`（对话名称）、`msg_type`（消息类型）

### 4. 生成向量库

```bash
# 激活虚拟环境
source venv_embedding/Scripts/activate  # Windows Git Bash
# 或
source venv_embedding/bin/activate      # Linux/Mac

# 生成向量库
python scripts/generate_embeddings.py --excel 聊天记录excel/messages.xlsx
```

预计耗时：~80 分钟（698 个对话，183,287 个会话片段）

### 5. 测试搜索

```bash
# 测试向量库和搜索功能
python scripts/test_search.py

# 或运行示例代码
python examples/basic_usage.py
```

## 项目结构

```
微信记忆系统/
├── scripts/                  # 正式脚本
│   ├── generate_embeddings.py   # 向量生成（整合所有最佳实践）
│   ├── test_search.py            # 搜索测试
│   └── README.md                 # 使用指南
├── data_loader/              # 数据加载模块
│   ├── models.py             # 数据模型
│   ├── loader.py             # Excel 加载器
│   ├── session.py            # 会话切分器（滑动窗口）
│   └── README.md
├── embedding/                # 向量生成模块
│   ├── client.py             # Google Vertex AI 客户端
│   ├── enricher.py           # 文本富化器
│   ├── generator.py          # 双向量生成器（动态 batch）
│   └── README.md
├── retrieval/                # 检索模块
│   ├── vector_store.py       # 基础向量存储
│   ├── hybrid.py             # 混合检索（BM25 + FAISS）
│   └── README.md
├── examples/                 # 使用示例
│   ├── basic_usage.py        # 基本使用示例
│   └── README.md
├── docs/                     # 技术文档
├── vector_stores/            # 向量库存储目录
│   ├── conversations.pkl     # 最终向量库
│   └── shards/               # 分片文件
├── config/                   # 配置
├── utils/                    # 工具函数
├── .env.example              # 环境变量示例
├── README.md                 # 本文档
└── README_VECTOR_SYSTEM.md   # 系统架构详细文档
```

## 核心模块

### 1. data_loader - 数据加载

负责微信聊天记录的解析、清洗和会话切分。

**特性**：
- 支持 Excel 格式导入
- 混合滑动窗口策略：30 分钟时间 gap，3-20 条消息
- 边界重叠机制：避免信息丢失

[详细文档](data_loader/README.md)

### 2. embedding - 向量生成

生成双向量 embeddings，支持大规模数据处理。

**特性**：
- Google Vertex AI text-embedding-004（768 维）
- 双向量策略：内容（85%）+ 上下文（15%）
- 动态 batch：基于 token 数动态调整，避免 API 限制
- 分片保存：内存友好，支持增量更新

[详细文档](embedding/README.md)

### 3. retrieval - 检索

混合检索引擎，结合关键词和语义搜索。

**特性**：
- BM25 关键词检索 + 向量语义检索
- 权重配比：BM25:0.5 + Vector:0.5（经过评测优化）
- FAISS HNSW 索引：100-400x 加速
- 支持时间、参与者过滤

[详细文档](retrieval/README.md)

## 使用示例

### 示例 1：基本搜索

```python
from retrieval import HybridVectorStore
from embedding import GoogleEmbeddingClient

# 加载向量库
vs = HybridVectorStore(dimension=768, use_faiss=True)
vs.load("vector_stores/conversations.pkl")

# 构建索引
vs.build_bm25_index()
vs.build_faiss_index()

# 初始化客户端
client = GoogleEmbeddingClient()

# 搜索
query = "讨论 AI 项目的对话"
query_embedding = client.get_embeddings([query])[0]

results = vs.hybrid_search(
    query_content_embedding=query_embedding,
    query_text=query,
    top_k=5
)

# 显示结果
for r in results:
    print(f"分数: {r['score']:.3f}")
    print(f"内容: {r['metadata']['content_text'][:100]}...")
```

### 示例 2：高级搜索（带过滤）

```python
from datetime import datetime

# 定义过滤器
filters = {
    'time_range': (
        datetime(2024, 1, 1).timestamp(),
        datetime(2024, 12, 31).timestamp()
    ),
    'participants': ['Alice', 'Bob']
}

# 执行搜索
results = vs.hybrid_search(
    query_content_embedding=query_embedding,
    query_text="项目进展",
    filters=filters,
    top_k=5
)
```

更多示例见 [examples/](examples/) 目录。

## 技术架构

### 双向量设计

**问题**：单向量方案中，模板文本占比过高，导致区分度低。

**解决方案**：
- **内容向量**（85% 权重）：纯对话内容，捕捉主题和语义
- **上下文向量**（15% 权重）：时间、参与者等元信息

**效果**：向量区分度显著提升

### 混合检索

**组合策略**：
- **BM25**：关键词精确匹配，处理专有名词
- **向量**：语义相似度，处理同义词和隐含语义
- **权重**：经过评测，BM25:0.5 + Vector:0.5 综合表现最佳

### 会话切分

**混合滑动窗口**：
1. **严格分割**：30 分钟时间 gap + 3-20 条消息
2. **创建主 sessions**
3. **创建边界 overlaps**：跨分割点重叠，提高召回率

### 动态 Batch

**问题**：固定 batch_size 会导致 token 超限。

**解决方案**：
- 估算每个 session 的 token 数（~1.5 tokens/字符）
- 动态累积直到接近 19,000 tokens 限制
- 100% 成功率，0 个零向量

详细架构见 [README_VECTOR_SYSTEM.md](README_VECTOR_SYSTEM.md)

## 性能指标

基于实际数据（698 个对话，183,287 个 sessions）：

| 指标 | 数值 |
|-----|------|
| 生成时间 | ~80 分钟 |
| API 调用 | ~1,200 次 |
| 成功率 | 100% |
| 内存峰值 | ~1.5GB |
| 最终文件 | 1.94GB |
| 搜索延迟 | <100ms |
| FAISS 加速 | 100-400x |

## 最佳实践

本项目经过两天迭代，整合了以下最佳实践：

1. ✅ **双层向量**：Content(85%) + Context(15%)
2. ✅ **滑动窗口分片**：30 分钟 gap, 3-20 条消息
3. ✅ **动态 Batch**：基于 token 数，避免 API 限制
4. ✅ **分片保存**：避免 OOM，支持增量更新
5. ✅ **混合检索**：BM25(0.5) + Vector(0.5)
6. ✅ **FAISS 优化**：大规模数据自动启用

详见 [scripts/README.md](scripts/README.md)

## 依赖关系

```
应用层
    ↓
retrieval（检索）
    ↓
embedding（向量生成）
    ↓
data_loader（数据加载）
    ↓
config/utils（配置和工具）
```

## 故障排查

### OOM 错误
使用 `scripts/generate_embeddings.py`（分片策略）而非旧脚本。

### Token 超限错误
使用 `scripts/generate_embeddings.py`（动态 batch）。

### 搜索无结果
1. 检查索引是否构建（`build_bm25_index`, `build_faiss_index`）
2. 检查查询向量是否正确生成
3. 检查是否有零向量（查看生成日志）

## 未来扩展

- [ ] 支持更多 embedding 模型（OpenAI, HuggingFace 等）
- [ ] 本地 embedding 模型（离线使用）
- [ ] 重排序（reranking）
- [ ] 多模态检索（图片、语音等）
- [ ] 分布式向量库（Milvus, Weaviate 等）
- [ ] API 服务化
- [ ] Web 界面

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 相关文档

- [系统架构详解](README_VECTOR_SYSTEM.md)
- [脚本使用指南](scripts/README.md)
- [使用示例](examples/README.md)
- [数据加载模块](data_loader/README.md)
- [向量生成模块](embedding/README.md)
- [检索模块](retrieval/README.md)
