# 快速开始指南

本指南将帮助您在 5 分钟内搭建并运行 WeMemory 记忆系统。

---

## 前置要求

### 必需

- **Python 3.8+**
- **Google Cloud 账号** - 用于 Vertex AI Embedding API
- **微信聊天记录** - JSON 格式（通过 WeFlow 导出）

### 可选

- **Docker** - 用于容器化部署
- **Neo4j** - 如果要尝试图数据库方案（本项目不使用）

---

## 第一步：安装

### 1.1 克隆仓库

```bash
git clone https://github.com/mixuechu/WeMemory.git
cd WeMemory
```

### 1.2 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 1.3 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
nano .env
```

填入以下配置：

```env
# Google Cloud 配置
VITE_GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_REGION=us-central1
VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}

# 可选：API 服务配置
API_HOST=0.0.0.0
API_PORT=8000
```

**获取 Google Cloud 凭证**：
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建项目并启用 Vertex AI API
3. 创建服务账号并下载 JSON 凭证
4. 将 JSON 内容复制到 `VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON`

---

## 第二步：准备数据

### 2.1 导出微信数据

使用 [WeFlow](https://github.com/hicccc77/WeFlow) 导出微信聊天记录：

1. 下载 WeFlow 工具
2. 运行导出，选择 JSON 格式
3. 将导出的 JSON 文件放到 `data/conversations/chat_data_filtered/`

[详细教程](data-export.md)

### 2.2 数据格式示例

WeFlow 导出的 JSON 格式：

```json
{
  "conversation_name": "家庭群",
  "messages": [
    {
      "timestamp": "2024-01-01 10:30:00",
      "sender_name": "妈妈",
      "content": "今天晚上回家吃饭吗？",
      "msg_type": "text"
    },
    {
      "timestamp": "2024-01-01 10:32:15",
      "sender_name": "我",
      "content": "好的，6点到家",
      "msg_type": "text"
    }
  ]
}
```

---

## 第三步：生成向量库

### 3.1 生成对话向量

```bash
# 生成对话向量库
python scripts/generate_embeddings.py \
  --data data/conversations/chat_data_filtered/ \
  --output vector_stores/conversations/embeddings.pkl

# 预计耗时：~5 分钟（138 个对话）
```

**输出**：
- `vector_stores/conversations/embeddings.pkl` - 对话向量库
- 自动构建 FAISS 索引

### 3.2 生成知识图谱（可选）

如果需要知识图谱功能：

```bash
# 1. 从对话中提取三元组
python knowledge_graph/triplet_builder.py

# 2. 生成三元组向量
python knowledge_graph/embedding_generator.py

# 预计耗时：~10 分钟
```

**输出**：
- `data/knowledge_graph/triplets.json` - 三元组数据
- `vector_stores/triplets/` - 三元组向量库

[跳过知识图谱构建](knowledge-graph.md#跳过构建)

---

## 第四步：启动服务

### 4.1 启动 API 服务

```bash
# 启动 FastAPI 服务
python api/main.py

# 或使用 uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**服务地址**：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

### 4.2 测试检索

#### 方法 1：使用 API 文档（推荐）

1. 访问 http://localhost:8000/docs
2. 展开 `POST /api/recall`
3. 点击 "Try it out"
4. 填入查询：

```json
{
  "query": "讨论工作的对话",
  "top_k": 5
}
```

5. 点击 "Execute" 查看结果

#### 方法 2：使用 Python 代码

```python
import requests

response = requests.post("http://localhost:8000/api/recall", json={
    "query": "上次讨论 AI 项目的对话",
    "top_k": 5
})

results = response.json()
for item in results["memories"]:
    print(f"相关度: {item['score']:.2f}")
    print(f"对话: {item['conversation_name']}")
    print(f"内容: {item['content'][:100]}...")
    print("-" * 50)
```

#### 方法 3：使用 curl

```bash
curl -X POST "http://localhost:8000/api/recall" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "家人聊天的对话",
    "top_k": 3
  }'
```

---

## 第五步：运行测试

### 5.1 基础功能测试

```bash
# 测试向量检索
python tests/test_triplet_search.py

# 综合测试套件（111 个查询）
python tests/comprehensive_test.py
```

### 5.2 API 性能测试

```bash
# 运行 API 性能测试
python api/performance_test.py

# 预期结果：
# - 首次查询延迟：~1.4s（含 API 调用）
# - 缓存查询延迟：<100ms
```

---

## 使用示例

### 示例 1：基本检索

```python
from retrieval import HybridVectorStore
from embedding import GoogleEmbeddingClient

# 初始化
client = GoogleEmbeddingClient()
vector_store = HybridVectorStore(dimension=768, use_faiss=True)

# 加载向量库
vector_store.load("vector_stores/conversations/embeddings.pkl")
vector_store.build_bm25_index()
vector_store.build_faiss_index()

# 检索
query = "上次讨论旅行的对话"
query_embedding = client.get_embeddings([query])[0]

results = vector_store.hybrid_search(
    query_content_embedding=query_embedding,
    query_text=query,
    top_k=5
)

for r in results:
    print(f"{r['score']:.2f} - {r['metadata']['content_text'][:50]}...")
```

### 示例 2：带过滤的检索

```python
from datetime import datetime

# 时间范围过滤
filters = {
    'time_range': (
        datetime(2024, 1, 1).timestamp(),
        datetime(2024, 12, 31).timestamp()
    ),
    'participants': ['妈妈', '爸爸']
}

results = vector_store.hybrid_search(
    query_content_embedding=query_embedding,
    query_text="家庭聚餐",
    filters=filters,
    top_k=5
)
```

### 示例 3：知识图谱检索

```python
# 加载知识图谱向量库
kg_store = HybridVectorStore(dimension=768, use_faiss=True)
kg_store.load("vector_stores/triplets/embeddings.pkl")
kg_store.build_faiss_index()

# 检索相关三元组
query = "张三的工作单位"
query_embedding = client.get_embeddings([query])[0]

triplets = kg_store.search(
    query_embedding=query_embedding,
    top_k=10
)

for t in triplets:
    print(f"{t['subject']} - {t['relation']} - {t['object']}")
```

---

## 常见问题

### Q: 向量生成时出现 API 限制错误

**错误信息**：`Quota exceeded for quota metric 'Embedding requests'`

**解决方案**：
1. 检查 Google Cloud 配额
2. 使用 `--batch-size` 参数减小批次大小：
```bash
python scripts/generate_embeddings.py --batch-size 50
```

### Q: 内存不足错误

**错误信息**：`MemoryError` 或 `OOM`

**解决方案**：
1. 使用分片处理：
```bash
python scripts/generate_embeddings.py --shard-size 100
```
2. 减少数据量（先从少量对话开始）

### Q: 检索结果不相关

**可能原因**：
1. 向量库未构建索引
2. 查询语义不清晰
3. BM25 权重配置不当

**解决方案**：
1. 确认调用了 `build_bm25_index()` 和 `build_faiss_index()`
2. 使用更具体的查询词
3. 调整混合检索权重（见 [embedding.md](embedding.md#权重调优)）

### Q: API 服务启动失败

**可能原因**：
1. 端口被占用
2. 向量库文件不存在
3. 环境变量未配置

**解决方案**：
```bash
# 检查端口
lsof -i :8000

# 检查向量库文件
ls -lh vector_stores/conversations/embeddings.pkl

# 检查环境变量
python -c "import os; print(os.getenv('VITE_GOOGLE_CLOUD_PROJECT'))"
```

---

## 下一步

- 📖 [了解数据导出流程](data-export.md)
- 🧹 [优化数据清洗策略](data-cleaning.md)
- 🧠 [深入理解 Embedding 方案](embedding.md)
- 🕸️ [构建知识图谱](knowledge-graph.md)
- 🚀 [部署到生产环境](api-service.md)

---

## 获取帮助

遇到问题？

- 📚 查阅[完整文档](../README.md#文档)
- 🐛 [提交 Issue](https://github.com/mixuechu/WeMemory/issues)
- 💬 参与[讨论](https://github.com/mixuechu/WeMemory/discussions)

---

返回 [主文档](../README.md)
