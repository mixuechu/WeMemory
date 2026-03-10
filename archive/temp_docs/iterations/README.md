# WeMemory API - 记忆联想服务

## 概念说明

这不是一个简单的"搜索" API，而是一个**记忆联想**（Memory Recall/Association）服务。

### Search vs Recall

**传统搜索**：
```
输入: "AI项目"
输出: 包含"AI项目"关键词的对话
```

**记忆联想**：
```
输入: "明天要开会讨论那个新功能"
系统联想:
  → 上次讨论这个功能的对话（时序关联）
  → 参与讨论的人是谁（人物关联）
  → 当时的结论和待办事项（语义关联）
  → 相关的其他会议记录（主题关联）
```

就像人类记忆一样，**一个线索可以触发多个相关记忆**。

## 核心功能

### 1. 记忆联想 (Memory Recall)

根据当前上下文，联想到相关的历史记忆。

**端点**: `POST /api/recall`

**请求示例**:
```json
{
  "context": "明天要和张三讨论AI项目的进展",
  "recall_type": "auto",  // auto, semantic, temporal, people
  "top_k": 5,
  "include_context": true
}
```

**响应示例**:
```json
{
  "memories": [
    {
      "content": "2024-02-15 与张三讨论AI项目初期规划...",
      "relevance_score": 0.89,
      "recall_reason": "同一主题 + 同一人物",
      "timestamp": 1708012800,
      "participants": ["张三", "用户"],
      "related_memories": [...]
    }
  ],
  "associations": {
    "people": ["张三"],
    "topics": ["AI项目", "进展讨论"],
    "time_context": "最近3个月的相关讨论"
  }
}
```

### 2. 主题关联 (Topic Association)

找到与特定主题相关的所有记忆。

**端点**: `POST /api/associate/topic`

### 3. 人物关联 (People Association)

找到与特定人物相关的记忆。

**端点**: `POST /api/associate/people`

### 4. 时序联想 (Temporal Association)

找到时间上相关的记忆（之前/之后发生的事）。

**端点**: `POST /api/associate/temporal`

## 技术架构

```
用户请求
    ↓
API Layer (FastAPI)
    ↓
Recall Service (联想服务)
    ├→ Vector Retrieval (向量检索)
    ├→ Context Analysis (上下文分析)
    └→ Association Logic (关联逻辑)
    ↓
Response Enhancement (响应增强)
    ├→ Relevance Scoring (相关性评分)
    ├→ Context Enrichment (上下文增强)
    └→ Explanation Generation (解释生成)
    ↓
返回结果
```

## 安装和运行

### 安装依赖

```bash
pip install fastapi uvicorn python-multipart
```

### 启动服务

```bash
# 开发模式（自动重载）
uvicorn api.main:app --reload --port 8000

# 生产模式
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 访问文档

启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 端点列表

### 核心端点

- `POST /api/recall` - 记忆联想（主要功能）
- `POST /api/associate/topic` - 主题关联
- `POST /api/associate/people` - 人物关联
- `POST /api/associate/temporal` - 时序联想

### 辅助端点

- `POST /api/search` - 简单搜索（兼容性）
- `GET /api/stats` - 向量库统计
- `GET /api/health` - 健康检查

## 使用示例

### Python 客户端

```python
import requests

# 记忆联想
response = requests.post(
    "http://localhost:8000/api/recall",
    json={
        "context": "明天要开会讨论项目进展",
        "top_k": 5
    }
)

memories = response.json()["memories"]
for mem in memories:
    print(f"相关度: {mem['relevance_score']:.2f}")
    print(f"原因: {mem['recall_reason']}")
    print(f"内容: {mem['content'][:100]}...")
    print()
```

### JavaScript 客户端

```javascript
const recall = async (context) => {
  const response = await fetch('http://localhost:8000/api/recall', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      context: context,
      top_k: 5
    })
  });
  return await response.json();
};

const memories = await recall("明天要开会");
console.log(memories);
```

## 配置

环境变量配置（`.env`）：

```bash
# 向量库路径
VECTOR_STORE_PATH=vector_stores/conversations.pkl

# API 配置
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# 联想配置
DEFAULT_TOP_K=5
MAX_TOP_K=20
MIN_RELEVANCE_SCORE=0.3

# 缓存配置
ENABLE_CACHE=true
CACHE_TTL=3600  # 1小时
```

## 性能优化

### 1. 向量库预加载

服务启动时一次性加载向量库到内存，避免每次请求重新加载。

### 2. 结果缓存

对相同或相似的请求进行缓存，TTL 默认 1 小时。

### 3. 异步处理

使用 FastAPI 的异步特性，提升并发能力。

### 4. 批量推理

如果有多个联想请求，可以批量处理。

## 部署

### Docker 部署

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t wememory-api .
docker run -p 8000:8000 -v $(pwd)/vector_stores:/app/vector_stores wememory-api
```

### 云部署

支持部署到：
- Google Cloud Run
- AWS Lambda (with Mangum adapter)
- Azure Functions
- 任何支持 Docker 的平台

## 监控和日志

### 日志级别

- `INFO`: 正常请求
- `WARNING`: 联想结果少于预期
- `ERROR`: 向量库加载失败等

### 监控指标

- 请求延迟 (P50, P95, P99)
- 请求成功率
- 联想质量评分（用户反馈）
- 缓存命中率

## 扩展功能（未来）

- [ ] 多租户支持（多用户隔离）
- [ ] 联想质量反馈（用户评分）
- [ ] 实时记忆更新（WebSocket）
- [ ] 联想解释可视化
- [ ] A/B 测试框架

## 故障排查

### 问题 1: 向量库加载失败

```bash
# 检查文件是否存在
ls -lh vector_stores/conversations.pkl

# 检查权限
chmod 644 vector_stores/conversations.pkl
```

### 问题 2: 联想结果质量差

- 检查 `min_relevance_score` 设置
- 尝试不同的 `recall_type`
- 增加 `top_k` 获取更多结果

### 问题 3: 响应慢

- 启用缓存
- 增加 workers 数量
- 检查向量库是否在 SSD 上

## 贡献

欢迎提交 Issue 和 Pull Request！

## License

MIT
