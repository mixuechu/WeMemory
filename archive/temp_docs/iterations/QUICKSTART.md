# API 快速启动指南

## 5 分钟快速上手

### 1. 安装依赖

```bash
# 基础依赖已经安装（从主项目）
# 只需要安装 FastAPI 相关依赖
pip install fastapi uvicorn pydantic
```

### 2. 确保有向量库文件

```bash
# 检查向量库是否存在
ls -lh vector_stores/conversations.pkl

# 如果没有，先生成
python scripts/generate_embeddings.py --excel your_data.xlsx
```

### 3. 启动 API 服务

```bash
# 开发模式（自动重载）
uvicorn api.main:app --reload --port 8000

# 或者直接运行
python api/main.py
```

看到这个说明启动成功：
```
✓ WeMemory API 启动成功！
文档地址: http://localhost:8000/docs
```

### 4. 访问文档

打开浏览器访问：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 5. 测试 API

#### 方式 1: 使用 Swagger UI（推荐）

1. 打开 http://localhost:8000/docs
2. 点击 `POST /api/recall`
3. 点击 "Try it out"
4. 输入：
   ```json
   {
     "context": "明天要讨论AI项目",
     "top_k": 3
   }
   ```
5. 点击 "Execute"
6. 查看响应结果

#### 方式 2: 使用 curl

```bash
curl -X POST "http://localhost:8000/api/recall" \
  -H "Content-Type: application/json" \
  -d '{
    "context": "讨论AI项目的进展",
    "recall_type": "auto",
    "top_k": 3
  }'
```

#### 方式 3: 使用 Python 客户端

```bash
# 运行测试客户端
python api/test_client.py
```

或者在你的代码中：

```python
import requests

# 记忆联想
response = requests.post(
    "http://localhost:8000/api/recall",
    json={
        "context": "明天要开会讨论项目",
        "top_k": 5
    }
)

result = response.json()
for memory in result['memories']:
    print(f"相关度: {memory['relevance_score']:.2f}")
    print(f"原因: {memory['recall_reason']}")
    print(f"内容: {memory['content'][:100]}...")
    print()
```

## 主要端点

### 1. 记忆联想（核心功能）

```bash
POST /api/recall

{
  "context": "明天要和张三讨论新功能",
  "recall_type": "auto",  # auto, semantic, temporal, people
  "top_k": 5
}
```

**返回**：相关的记忆 + 联想原因 + 关联信息

### 2. 主题关联

```bash
POST /api/associate/topic

{
  "topic": "AI项目",
  "top_k": 10
}
```

### 3. 人物关联

```bash
POST /api/associate/people

{
  "person": "张三",
  "top_k": 10
}
```

### 4. 时序联想

```bash
POST /api/associate/temporal

{
  "reference_time": 1708012800,  # Unix时间戳
  "direction": "around",          # before, after, around
  "time_window": 7                # 天数
}
```

### 5. 统计信息

```bash
GET /api/stats
```

### 6. 健康检查

```bash
GET /api/health
```

## 环境变量配置

创建 `.env` 文件：

```bash
# 向量库路径
VECTOR_STORE_PATH=vector_stores/conversations.pkl

# API 配置
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# 联想配置
DEFAULT_TOP_K=5
MIN_RELEVANCE_SCORE=0.3

# Google Cloud（用于 embedding）
VITE_GOOGLE_CLOUD_PROJECT=your-project-id
VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON={...}
```

## 生产部署

### 使用 Gunicorn（推荐）

```bash
# 安装 gunicorn
pip install gunicorn

# 启动
gunicorn api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### 使用 Docker

```bash
# 构建镜像
docker build -t wememory-api -f api/Dockerfile .

# 运行容器
docker run -p 8000:8000 \
  -v $(pwd)/vector_stores:/app/vector_stores \
  -v $(pwd)/.env:/app/.env \
  wememory-api
```

## 常见问题

### Q: 服务启动失败？

A: 检查：
1. 向量库文件是否存在
2. 依赖是否都已安装
3. 端口 8000 是否被占用

### Q: 联想结果不准确？

A: 调整参数：
1. 增加 `top_k` 获取更多结果
2. 降低 `min_relevance` 阈值
3. 尝试不同的 `recall_type`

### Q: 响应慢？

A: 优化方案：
1. 确保向量库在 SSD 上
2. 增加 workers 数量
3. 检查是否启用了缓存

## 下一步

- 阅读完整文档：`api/README.md`
- 了解核心概念：记忆联想 vs 传统搜索
- 探索更多端点：http://localhost:8000/docs
- 集成到你的应用中

---

**创建时间**: 2026-02-26
**版本**: 1.0.0
