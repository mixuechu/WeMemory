# WeMemory - 微信记忆系统

<div align="center">

**端到端的个人记忆系统构建方案**

从微信聊天记录导出到智能检索API的完整实现

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

[快速开始](#快速开始) • [核心特性](#核心特性) • [文档](#文档) • [架构](#架构) • [贡献](#贡献)

</div>

---

## 项目简介

WeMemory 是一个完整的个人记忆系统构建方案，展示了如何从微信聊天记录构建智能语义检索服务。本项目包含从数据导出、清洗、向量化、知识图谱构建到 API 服务的完整实现。

### 为什么需要这个项目？

- 📱 **个人数据主权**：完全控制自己的聊天记录，不依赖第三方服务
- 🔍 **智能检索**：基于语义理解而非关键词匹配，找到真正相关的对话
- 🧠 **知识沉淀**：从对话中自动提取事件、关系，构建个人知识图谱
- 🚀 **开箱即用**：提供完整的端到端方案，可直接部署使用

---

## 核心特性

### 🎯 端到端能力

本项目展示了构建个人记忆系统的**完整流程**：

```
微信客户端 → 数据导出 → 清洗筛选 → 向量化 → 知识图谱 → API服务
   (WeFlow)   (JSON)    (策略)    (Embedding)  (三元组)   (FastAPI)
```

### 1️⃣ 数据导出与清洗

- 🔗 **集成 [WeFlow](https://github.com/hicccc77/WeFlow)**：从微信客户端导出聊天记录为 JSON 格式
- 🧹 **智能清洗**：过滤系统消息、合并会话片段、去重
- 📊 **数据统计**：自动分析对话质量，筛选有价值的记录

[详细文档](docs/data-export.md) | [清洗策略](docs/data-cleaning.md)

### 2️⃣ 多语言 Embedding

- 🌍 **text-multilingual-embedding-002**：显著提升中文语义区分度
- ⚖️ **双向量架构**：内容向量（85%）+ 上下文向量（15%）
- 🔄 **混合检索**：BM25（50%）+ 向量检索（50%）

**为什么不用其他模型？** 我们对比了 text-embedding-004、OpenAI embeddings 等，multilingual 模型在中文场景下召回质量提升 **15-20%**。

[详细文档](docs/embedding.md)

### 3️⃣ 知识图谱构建

- 📝 **自然语言三元组**：7,865 条优化三元组（5,297 事件 + 2,568 关系）
- 🎯 **智能剪枝**：删除 80% 冗余关系，保留有价值的家庭/工作/地点关系
- 🚫 **为什么不用 Neo4j？**：三元组向量化方案更适合语义检索，避免图数据库复杂性

**技术创新**：将知识图谱转换为自然语言三元组，直接进行向量检索，效果接近图查询但性能更好。

[详细文档](docs/knowledge-graph.md)

### 4️⃣ 向量检索服务

- ⚡ **FAISS 加速**：HNSW 索引实现 100-400x 搜索加速
- 🔀 **混合检索**：结合 BM25 和向量相似度，提升召回率
- 📦 **分片存储**：内存友好，支持增量更新

[详细文档](docs/api-service.md)

### 5️⃣ 统一 API 服务

- 🚀 **FastAPI 服务**：RESTful API，支持记忆联想、主题关联、时序检索
- 🔗 **双向量库融合**：对话向量 + 知识图谱向量，一个查询同时检索两者
- 📊 **测试验证**：111 个测试查询，94%+ 召回质量

[API 文档](api/README.md)

---

## 快速开始

### 前置要求

- Python 3.8+
- Google Cloud 账号（用于 Vertex AI Embedding）
- 微信聊天记录（通过 [WeFlow](https://github.com/hicccc77/WeFlow) 导出）

### 安装

```bash
# 克隆仓库
git clone https://github.com/mixuechu/WeMemory.git
cd WeMemory

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 Google Cloud 凭证
```

### 使用示例

#### 1. 导出微信数据

使用 [WeFlow](https://github.com/hicccc77/WeFlow) 导出聊天记录为 JSON 格式，放到 `data/conversations/chat_data_filtered/`。

[详细教程](docs/data-export.md)

#### 2. 配置环境变量

编辑 `.env` 文件，配置 Google Cloud 凭证：

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}
```

#### 3. 运行完整 Pipeline

```bash
# 一键运行完整流程（数据清洗 → Embedding → 知识抽取 → 图谱构建）
python scripts/run_pipeline.py --all

# 或者单独运行某个步骤
python scripts/run_pipeline.py --step embedding
python scripts/run_pipeline.py --step knowledge_extraction
python scripts/run_pipeline.py --step graph_building
```

Pipeline 会自动：
- ✅ 清洗对话数据（去重、过滤系统消息）
- ✅ 生成双向量 embeddings（内容85% + 上下文15%）
- ✅ 使用 Gemini 2.5 Flash 抽取知识图谱
- ✅ 生成三元组并构建 FAISS 索引
- ✅ 支持断点续传（--fresh 清除检查点重新开始）

#### 4. 启动 API 服务

```bash
# 启动 FastAPI 服务
python api/main.py

# 访问 API 文档
# http://localhost:8000/docs
```

#### 4. 测试检索

```python
import requests

response = requests.post("http://localhost:8000/api/recall", json={
    "query": "上次讨论AI项目的对话",
    "top_k": 5
})

results = response.json()
for item in results["memories"]:
    print(f"相关度: {item['score']:.2f}")
    print(f"内容: {item['content']}")
```

[完整快速开始指南](docs/quickstart.md)

---

## 💰 成本说明

### 对话量 × 模型 = 开销

基于 **138个对话、53,732个记忆片段** 的实际生产数据测算：

| 对话数量 | Gemini Flash ⭐ | GPT-4o-mini | Claude Haiku | GPT-4o | Claude Sonnet |
|---------|----------------|-------------|--------------|---------|---------------|
| **10个** | $0.03 | $0.03 | $0.04 | $0.24 | $0.32 |
| **50个** | $0.13 | $0.16 | $0.22 | $1.22 | $1.60 |
| **100个** | $0.26 | $0.33 | $0.44 | $2.44 | $3.19 |
| **500个** | $1.31 | $1.65 | $2.22 | $12.22 | $15.97 |
| **1000个** | $2.62 | $3.30 | $4.45 | $24.45 | $31.95 |

> ⭐ **推荐使用 Gemini 2.5 Flash**：性价比最优，与 GPT-4o-mini 接近，比 GPT-4o/Claude Sonnet 便宜 **10-12倍**

### 成本构成

完整 Pipeline 包含两个 API 调用步骤：

**1. Embedding 步骤**（text-multilingual-embedding-002）
- 每个对话约 **97,341 tokens**（389个记忆片段 × 250 tokens/片段）
- 定价：约 $0.00002/1K tokens
- 成本：约 **$0.002/对话**

**2. 知识抽取步骤**（使用 LLM 抽取知识图谱）
- 每个对话约 **5,000 输入 tokens + 1,000 输出 tokens**
- 定价：取决于选择的模型（见上表）
- 成本：Gemini Flash 约 **$0.0007/对话**

**总计：** 每个对话约 **$0.0027**（使用 Gemini Flash）

### 模型定价对比

| 模型 | 输入定价 (per 1K tokens) | 输出定价 (per 1K tokens) | 100个对话总成本 |
|------|------------------------|------------------------|---------------|
| **Gemini 2.5 Flash** ⭐ | $0.000075 | $0.0003 | **$0.26** |
| GPT-4o-mini | $0.00015 | $0.0006 | $0.33 |
| Claude 3 Haiku | $0.00025 | $0.00125 | $0.44 |
| GPT-4o | $0.0025 | $0.01 | $2.44 |
| Claude 3.5 Sonnet | $0.003 | $0.015 | $3.19 |

*注：Embedding 成本（$0.002/对话）已包含在总成本中*

### 省钱建议

1. **模型选择**：
   - 日常使用：**Gemini 2.5 Flash**（最优性价比）
   - 高质量需求：GPT-4o-mini 或 Claude 3 Haiku
   - 避免使用：GPT-4o / Claude 3.5 Sonnet（成本高10倍）

2. **数据筛选**：
   - 过滤低价值对话（系统消息、短对话）
   - 使用数据清洗策略减少无效记录
   - 合理设置对话长度阈值

3. **分批处理**：
   - 利用 Pipeline 的断点续传功能
   - 失败后从检查点恢复，避免重复调用 API
   - 先用小批量测试，确认效果后再全量处理

---

## 架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                    微信客户端                            │
└────────────────────┬────────────────────────────────────┘
                     │ WeFlow 导出
                     ↓
┌─────────────────────────────────────────────────────────┐
│              JSON 聊天记录 (data/conversations/)         │
└────────────────────┬────────────────────────────────────┘
                     │ 数据清洗
                     ↓
         ┌───────────┴───────────┐
         ↓                       ↓
┌──────────────────┐    ┌──────────────────┐
│  对话向量化       │    │  知识图谱构建     │
│  (Embedding)     │    │  (三元组提取)     │
│                  │    │                  │
│ - 内容向量 85%   │    │ - 5,297 事件     │
│ - 上下文向量 15% │    │ - 2,568 关系     │
└────────┬─────────┘    └────────┬─────────┘
         │                       │ 三元组向量化
         ↓                       ↓
┌──────────────────┐    ┌──────────────────┐
│  对话向量库       │    │  图谱向量库       │
│  (FAISS)         │    │  (FAISS)         │
└────────┬─────────┘    └────────┬─────────┘
         │                       │
         └───────────┬───────────┘
                     ↓
         ┌───────────────────────┐
         │   混合检索引擎         │
         │  (BM25 + Vector)      │
         └───────────┬───────────┘
                     ↓
         ┌───────────────────────┐
         │    FastAPI 服务        │
         │  /api/recall           │
         └───────────────────────┘
```

[架构详细文档](docs/architecture.md)

### 技术栈

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| **数据导出** | [WeFlow](https://github.com/hicccc77/WeFlow) | 微信聊天记录导出工具 |
| **Embedding** | Google Vertex AI | text-multilingual-embedding-002 (768维) |
| **向量索引** | FAISS | HNSW 索引，100-400x 加速 |
| **关键词检索** | BM25 | 基于 rank-bm25 实现 |
| **知识抽取** | Gemini 2.5 Flash | 自然语言三元组提取 |
| **API 框架** | FastAPI | 高性能异步 Web 框架 |
| **Pipeline** | 自研框架 | 支持断点续传、检查点恢复 |

---

## 文档

### 📚 完整文档

- [快速开始指南](docs/quickstart.md) - 5分钟上手
- [数据导出教程](docs/data-export.md) - WeFlow 集成与数据格式
- [数据清洗策略](docs/data-cleaning.md) - 如何筛选有价值的对话
- [Embedding 方案](docs/embedding.md) - 模型选择、配比优化、检索策略
- [知识图谱构建](docs/knowledge-graph.md) - 三元组提取、为什么不用 Neo4j
- [API 服务部署](docs/api-service.md) - 服务配置、性能优化、API 文档
- [系统架构设计](docs/architecture.md) - 技术决策、性能指标

### 📦 模块文档

- [API 模块](api/README.md) - Memory Recall API
- [Embedding 模块](embedding/README.md) - 向量生成
- [Knowledge Graph 模块](knowledge_graph/README.md) - 知识图谱
- [Data Loader 模块](data_loader/README.md) - 数据加载
- [Retrieval 模块](retrieval/README.md) - 混合检索

---

## 性能指标

基于 138 个精选对话的测试结果：

| 指标 | 数值 | 说明 |
|------|------|------|
| **召回质量** | 94%+ | 111 个测试查询的平均召回率 |
| **检索延迟** | <100ms | FAISS HNSW 索引加速 |
| **知识图谱** | 7,865 条 | 5,297 事件 + 2,568 关系 |
| **向量维度** | 768 | text-multilingual-embedding-002 |
| **数据规模** | ~2GB | 生产环境数据大小 |

---

## 技术亮点

### 🌟 核心创新

1. **多语言 Embedding 模型**
   - 对比实验证明，text-multilingual-embedding-002 在中文场景下比 text-embedding-004 召回质量提升 15-20%
   - [详细对比](docs/embedding.md#模型对比)

2. **三元组知识图谱方案**
   - 将传统图数据库查询转换为向量检索
   - 避免 Neo4j 的复杂性，性能提升 3-5x
   - [设计思路](docs/knowledge-graph.md#为什么不用neo4j)

3. **智能关系剪枝**
   - 删除 80% 冗余关系（如"提到"、"相关"）
   - 保留有价值的家庭/工作/地点关系
   - 知识图谱质量提升，噪音降低 70%

4. **混合检索融合**
   - BM25（50%）处理专有名词和关键词
   - 向量检索（50%）处理语义相似和同义词
   - 综合效果优于单一方案 25-30%

---

## 项目结构

```
WeMemory/
├── pipeline/                    # 核心 Pipeline 框架 ⭐
│   ├── base.py                 # Pipeline 基类
│   ├── data_cleaning.py        # 数据清洗
│   ├── embedding.py            # 向量生成
│   ├── knowledge_extraction.py # 知识抽取（Gemini）
│   └── graph_building.py       # 三元组构建
├── config/                      # 配置系统 ⭐
│   ├── default.yaml            # 默认配置
│   └── loader.py               # 配置加载器
├── scripts/                     # 脚本工具 ⭐
│   └── run_pipeline.py         # Pipeline 统一入口
├── api/                        # FastAPI 服务
│   ├── main.py                 # 服务入口
│   ├── routers/                # API 路由
│   └── services/               # 业务逻辑
├── embedding/                  # Embedding 模块
│   ├── client.py              # Vertex AI 客户端
│   ├── generator.py           # 双向量生成器
│   └── session_builder.py     # 会话构建
├── knowledge_graph/            # 知识图谱模块
│   ├── triplet_builder.py     # 三元组构建
│   └── embedding_generator.py # 三元组向量化
├── retrieval/                  # 检索模块
│   ├── vector_store.py        # 向量存储（FAISS + BM25）
│   └── hybrid.py              # 混合检索
├── data_loader/                # 数据加载模块
│   ├── parser.py              # WeChat 格式解析
│   └── cleaner.py             # 数据清洗
├── data/                       # 生产数据（.gitignore）
│   ├── conversations/         # 对话数据
│   └── knowledge_graph/       # 知识图谱
├── vector_stores/              # 向量库（.gitignore）
│   ├── conversations/         # 对话向量
│   └── triplets/              # 三元组向量
├── tests/                      # 测试套件
├── examples/                   # 使用示例
└── docs/                       # 完整文档
```

---

## 常见问题

### Q: 为什么不直接使用 ChatGPT/Claude 检索聊天记录？

A:
1. **隐私**：本地部署，数据完全自主控制
2. **成本**：避免每次检索都调用 LLM API
3. **速度**：向量检索 <100ms，LLM 调用需要几秒
4. **定制化**：可以根据个人需求优化检索策略

### Q: 必须使用 Google Vertex AI 吗？

A: 不是必须的。代码设计支持多种 Embedding 提供商：
- Google Vertex AI（推荐，中文效果好）
- OpenAI Embeddings
- 本地模型（如 SentenceTransformers）

只需实现 `embedding/client.py` 的接口即可。

### Q: 数据规模有限制吗？

A: 本项目展示的是 138 个对话（~2GB）的方案。实际上：
- **小规模**（<1000 对话）：可直接使用，内存占用 <4GB
- **中规模**（1000-10000 对话）：需要分片存储，参考 `scripts/generate_embeddings.py`
- **大规模**（>10000 对话）：建议使用分布式向量库（Milvus、Weaviate）

---

## 贡献

欢迎贡献！请阅读 [贡献指南](CONTRIBUTING.md)。

### 贡献方式

- 🐛 提交 Bug 报告
- 💡 提出新功能建议
- 📝 改进文档
- 🔧 提交代码优化

---

## 许可证

[MIT License](LICENSE)

---

## 致谢

- [WeFlow](https://github.com/hicccc77/WeFlow) - 微信聊天记录导出工具
- [FAISS](https://github.com/facebookresearch/faiss) - Facebook AI 向量搜索库
- [Google Vertex AI](https://cloud.google.com/vertex-ai) - Embedding 服务

---

## 联系方式

- GitHub Issues: [提交问题](https://github.com/mixuechu/WeMemory/issues)
- 项目主页: [WeMemory](https://github.com/mixuechu/WeMemory)

---

<div align="center">

**如果这个项目对你有帮助，请给个 ⭐️ Star！**

Made with ❤️ by WeMemory Team

</div>
