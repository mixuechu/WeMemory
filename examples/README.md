# 使用示例

本目录包含 WeMemory 的使用示例代码。

---

## 数据样例

### data_samples/

包含 ChatLab 格式的脱敏数据样例：

- `chatlab_format_private_chat.json` - 私聊对话样例
- `chatlab_format_group_chat.json` - 群聊对话样例
- `README.md` - 格式详细说明

**用途**：
- 了解 ChatLab 格式结构
- 测试数据处理脚本
- 作为文档参考

**详细说明**：[data_samples/README.md](data_samples/README.md)

---

## 代码示例

### 1. basic_usage.py

**功能**：演示基本的向量搜索功能

```python
# 加载向量库
vs = HybridVectorStore(dimension=768, use_faiss=True)
vs.load("vector_stores/conversations/embeddings.pkl")

# 构建索引
vs.build_bm25_index()
vs.build_faiss_index()

# 执行搜索
results = vs.hybrid_search(
    query_content_embedding=query_embedding,
    query_text="讨论 AI 项目的对话",
    top_k=5
)
```

**运行**：
```bash
python examples/basic_usage.py
```

### 2. search_example.py

**功能**：演示高级搜索功能（带过滤）

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

**运行**：
```bash
python examples/search_example.py
```

### 3. api_client_example.py

**功能**：演示如何使用 WeMemory API

```python
import httpx

# 调用 API
response = httpx.post(
    "http://localhost:8000/api/recall",
    json={
        "query": "上次和张三讨论的项目进展",
        "top_k": 5
    }
)

results = response.json()
```

**运行**：
```bash
# 先启动 API 服务
python scripts/start_api.py

# 然后运行示例
python examples/api_client_example.py
```

### 4. 01_generate_embeddings.py

**功能**：演示如何生成向量库（基础示例）

⚠️ **注意**：此示例是早期版本，建议使用新的 Pipeline 系统：

```bash
# 推荐使用 Pipeline
python scripts/run_pipeline.py --step embedding
```

### 5. 02_hybrid_search.py

**功能**：演示混合搜索（BM25 + 向量）

```python
# 自定义权重
results = vs.hybrid_search(
    query_content_embedding=query_embedding,
    query_text="开会时间",
    bm25_weight=0.8,  # 关键词优先
    vector_weight=0.2
)
```

---

## 前提条件

### 1. 配置环境

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，设置必需的变量
nano .env
```

**必需的环境变量**：
- `GOOGLE_CLOUD_PROJECT` - Google Cloud 项目 ID
- `GOOGLE_APPLICATION_CREDENTIALS` 或 `GOOGLE_APPLICATION_CREDENTIALS_JSON`

**验证配置**：
```bash
python scripts/validate_config.py
```

### 2. 准备数据

```bash
# 导出微信数据（使用 WeFlow）
# 详见: docs/data-export.md

# 验证数据格式
python scripts/validate_chatlab_format.py data/conversations/chat_data_filtered/
```

### 3. 生成向量库

```bash
# 使用 Pipeline（推荐）
python scripts/run_pipeline.py --step embedding

# 或使用直接脚本
python scripts/generate_embeddings.py
```

---

## 完整工作流程示例

### 从零开始

```bash
# 1. 设置配置
cp .env.example .env
# 编辑 .env

# 2. 验证配置
python scripts/validate_config.py

# 3. 准备数据（假设已用 WeFlow 导出）
# 数据放在 data/conversations/chat_data_filtered/

# 4. 验证数据格式
python scripts/validate_chatlab_format.py data/conversations/chat_data_filtered/

# 5. 数据清洗（可选）
python scripts/run_pipeline.py --step data_cleaning

# 6. 生成向量库
python scripts/run_pipeline.py --step embedding

# 7. 启动 API 服务
python scripts/start_api.py

# 8. 测试 API（新终端）
python examples/api_client_example.py
```

### 使用现有向量库

```bash
# 1. 确认向量库存在
ls -lh vector_stores/conversations/embeddings.pkl

# 2. 运行搜索示例
python examples/search_example.py

# 3. 或启动 API
python scripts/start_api.py
```

---

## 扩展阅读

### 文档
- [快速开始](../docs/quickstart.md) - 5 分钟上手指南
- [数据导出](../docs/data-export.md) - WeFlow 使用指南
- [数据清洗](../docs/data-cleaning.md) - 数据清洗策略
- [Embedding](../docs/embedding.md) - 向量生成详解
- [API 服务](../docs/api-service.md) - API 使用指南
- [知识图谱](../docs/knowledge-graph.md) - 知识图谱构建

### 代码
- [Pipeline 模块](../pipeline/README.md) - 端到端数据处理
- [配置系统](../config/README.md) - 配置管理
- [脚本工具](../scripts/README.md) - 实用脚本

### 参考
- [项目架构](../docs/architecture.md) - 系统架构说明
- [贡献指南](../CONTRIBUTING.md) - 如何贡献代码

---

返回 [主文档](../README.md)
