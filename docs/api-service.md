# API 服务指南

本文档说明如何启动和使用 WeMemory API 服务。

---

## 概述

WeMemory API 是一个基于 FastAPI 的智能记忆联想服务，提供：

- 🧠 **记忆联想**：基于语义的记忆检索
- 🔍 **混合搜索**：BM25 + 向量检索
- 🕸️ **知识图谱查询**：基于三元组的关系检索
- ⚡ **高性能**：FAISS HNSW 索引，毫秒级响应
- 📊 **完整文档**：自动生成的 Swagger UI

---

## 启动前置条件

### 必需条件

1. **对话向量库已生成**
   ```bash
   # 检查向量库文件是否存在
   ls -lh vector_stores/conversations/embeddings.pkl

   # 如果不存在，先生成
   python scripts/generate_embeddings.py
   ```

2. **环境变量已配置**
   ```bash
   # 检查配置
   python scripts/validate_config.py

   # 必需的环境变量
   GOOGLE_CLOUD_PROJECT=your-project-id
   ```

### 可选条件

3. **知识图谱向量库**（可选，用于三元组查询）
   ```bash
   # 检查三元组向量库
   ls -lh vector_stores/triplets/embeddings.pkl

   # 如果不存在，可以生成
   python knowledge_graph/embedding_generator.py
   ```

---

## 启动步骤

### 方法 1：使用启动脚本（推荐）

```bash
# 使用启动脚本（会自动检查前置条件）
python scripts/start_api.py

# 指定端口
python scripts/start_api.py --port 9000

# 开发模式（启用热重载）
python scripts/start_api.py --reload
```

**启动脚本会自动**：
- ✅ 检查向量库是否存在
- ✅ 验证配置
- ✅ 显示访问地址
- ✅ 提供友好的错误提示

### 方法 2：直接运行

```bash
# 方式1：使用 python 直接运行
python api/main.py

# 方式2：使用 uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000

# 开发模式（热重载）
uvicorn api.main:app --reload
```

### 方法 3：使用配置文件

```bash
# 设置环境变量（可选）
export API_PORT=9000
export API_HOST=0.0.0.0
export DEBUG=true

# 启动
python api/main.py
```

---

## 验证启动

### 1. 检查健康状态

```bash
# 基础健康检查
curl http://localhost:8000/api/health

# 响应示例
{
  "status": "healthy",
  "version": "1.0.0",
  "vector_store_loaded": true,
  "uptime_seconds": 123.45
}
```

### 2. 详细健康检查

```bash
# 详细健康检查（包含向量库、索引、内存信息）
curl http://localhost:8000/api/health/detailed

# 响应示例
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "conversation_vector_store": {
      "status": "healthy",
      "total_memories": 1523,
      "index_type": "HNSW",
      "dimensions": 768
    },
    "triplet_vector_store": {
      "status": "healthy",
      "total_triplets": 7865,
      "index_type": "HNSW"
    },
    "memory": {
      "status": "healthy",
      "used_mb": 850.5,
      "total_mb": 4096.0,
      "usage_percent": 20.8
    }
  },
  "uptime_seconds": 123.45
}
```

### 3. 访问 API 文档

启动成功后，访问以下地址：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## API 使用指南

### 核心端点

#### 1. 记忆联想 - `/api/recall`

**功能**：根据查询联想相关记忆

```bash
# 基础查询
curl -X POST http://localhost:8000/api/recall \
  -H "Content-Type: application/json" \
  -d '{
    "query": "上次和张三讨论的项目进展",
    "top_k": 5
  }'
```

**响应示例**：
```json
{
  "query": "上次和张三讨论的项目进展",
  "results": [
    {
      "conversation_name": "张三",
      "content": "项目已经完成了80%，下周可以交付...",
      "timestamp": "2024-01-15 14:30:00",
      "relevance_score": 0.92,
      "recall_reason": "语义相关：讨论项目进展"
    }
  ],
  "total_results": 5,
  "search_time_ms": 12.5
}
```

**参数说明**：

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | ✅ | - | 查询文本 |
| `top_k` | integer | ❌ | 5 | 返回结果数量（1-20） |
| `min_score` | float | ❌ | 0.0 | 最小相关性分数（0-1） |
| `use_hybrid` | boolean | ❌ | true | 是否使用混合搜索（BM25+向量） |

#### 2. 知识图谱查询 - `/api/knowledge/triplets`

**功能**：查询知识图谱三元组

```bash
curl -X POST http://localhost:8000/api/knowledge/triplets \
  -H "Content-Type: application/json" \
  -d '{
    "query": "张三的工作经历",
    "top_k": 10
  }'
```

**响应示例**：
```json
{
  "query": "张三的工作经历",
  "triplets": [
    {
      "subject": "张三",
      "predicate": "就职于",
      "object": "某某公司",
      "confidence": 0.95,
      "source_conversation": "张三",
      "timestamp": "2024-01-10"
    }
  ],
  "total_results": 10
}
```

#### 3. 统计信息 - `/api/stats`

**功能**：获取向量库统计信息

```bash
curl http://localhost:8000/api/stats
```

**响应示例**：
```json
{
  "total_memories": 1523,
  "total_conversations": 138,
  "date_range": {
    "earliest": "2023-01-01",
    "latest": "2024-12-31"
  },
  "index_info": {
    "type": "HNSW",
    "dimensions": 768,
    "total_vectors": 1523
  }
}
```

---

## 配置选项

### 环境变量配置

```bash
# .env 文件
# API 服务器配置
API_HOST=0.0.0.0          # 监听地址
API_PORT=8000             # 端口号
DEBUG=false               # 是否启用调试模式

# 向量库路径
VECTOR_STORE_PATH=vector_stores/conversations/embeddings.pkl
TRIPLET_VECTOR_STORE_PATH=vector_stores/triplets/embeddings.pkl

# 搜索配置
DEFAULT_TOP_K=5           # 默认返回结果数
MAX_TOP_K=20              # 最大返回结果数
MIN_RELEVANCE_SCORE=0.0   # 最小相关性分数

# 性能配置
ENABLE_CACHE=true         # 启用缓存
CACHE_TTL=3600            # 缓存过期时间（秒）
```

### YAML 配置文件

```yaml
# config/default.yaml
api:
  host: 0.0.0.0
  port: 8000
  reload: false

  search:
    default_top_k: 5
    max_top_k: 20

  cors:
    enabled: true
    origins:
      - http://localhost:3000
      - http://localhost:8000
```

---

## 性能优化

### 1. 缓存配置

API 自动缓存相同的查询：

```python
# 第一次查询（需要计算）
response_time: 50ms

# 相同查询（从缓存返回）
response_time: 2ms
```

**配置缓存**：
```bash
ENABLE_CACHE=true
CACHE_TTL=3600  # 1小时
```

### 2. 批量查询

```bash
# 批量查询多个问题
curl -X POST http://localhost:8000/api/recall/batch \
  -H "Content-Type: application/json" \
  -d '{
    "queries": [
      "上次和张三讨论的项目",
      "李四的联系方式",
      "本周的会议安排"
    ],
    "top_k": 3
  }'
```

### 3. 并发处理

API 支持并发请求，建议配置：

```yaml
# config/default.yaml
performance:
  max_concurrent_requests: 10
  max_concurrent_api_calls: 5
```

---

## 故障排查

### 问题 1：启动失败 - 向量库不存在

**错误信息**：
```
[ERROR] 向量库文件不存在: vector_stores/conversations.pkl
请先运行: python scripts/generate_embeddings.py
```

**解决方案**：
```bash
# 1. 确认数据已导出
ls data/conversations/chat_data_filtered/

# 2. 生成向量库
python scripts/generate_embeddings.py

# 3. 重新启动 API
python scripts/start_api.py
```

### 问题 2：查询返回空结果

**可能原因**：
- 查询文本与记忆内容语义相差太大
- `min_score` 设置过高
- 向量库为空或损坏

**解决方案**：
```bash
# 1. 检查向量库统计
curl http://localhost:8000/api/stats

# 2. 降低最小分数阈值
curl -X POST http://localhost:8000/api/recall \
  -d '{"query": "测试", "min_score": 0.0}'

# 3. 使用混合搜索
curl -X POST http://localhost:8000/api/recall \
  -d '{"query": "测试", "use_hybrid": true}'
```

### 问题 3：响应速度慢

**可能原因**：
- 向量库过大
- 没有启用 FAISS 索引
- 内存不足

**解决方案**：
```bash
# 1. 检查内存使用
curl http://localhost:8000/api/health/detailed

# 2. 启用缓存
export ENABLE_CACHE=true

# 3. 减少返回结果数
export DEFAULT_TOP_K=3

# 4. 重建索引（如果损坏）
python scripts/rebuild_index.py
```

### 问题 4：CORS 错误（前端调用失败）

**错误信息**：
```
Access to fetch at 'http://localhost:8000/api/recall' from origin
'http://localhost:3000' has been blocked by CORS policy
```

**解决方案**：

修改 `config/default.yaml`:
```yaml
api:
  cors:
    enabled: true
    origins:
      - http://localhost:3000  # 添加你的前端地址
      - http://localhost:8000
```

或在 `.env` 中设置：
```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

### 问题 5：端口被占用

**错误信息**：
```
ERROR: [Errno 48] Address already in use
```

**解决方案**：
```bash
# 查找占用端口的进程
lsof -i :8000

# 杀死进程
kill -9 <PID>

# 或使用不同端口
python scripts/start_api.py --port 9000
```

---

## 监控和日志

### 1. 查看日志

```bash
# 实时查看日志
tail -f logs/wememory.log

# 查看最近的错误
grep ERROR logs/wememory.log | tail -20

# 查看访问日志
grep "GET\|POST" logs/wememory.log
```

### 2. 健康监控

```bash
# 定期健康检查脚本
#!/bin/bash
while true; do
  curl -s http://localhost:8000/api/health | jq .
  sleep 60
done
```

### 3. 性能指标

```bash
# 查询性能统计
curl http://localhost:8000/api/stats

# 查看平均响应时间
curl http://localhost:8000/api/health/detailed | jq '.performance'
```

---

## 生产部署建议

### 1. 使用进程管理器

**使用 Supervisor**:
```ini
# /etc/supervisor/conf.d/wememory.conf
[program:wememory-api]
command=/path/to/venv/bin/python scripts/start_api.py
directory=/path/to/wechat_memory
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/wememory/error.log
stdout_logfile=/var/log/wememory/access.log
```

**使用 systemd**:
```ini
# /etc/systemd/system/wememory.service
[Unit]
Description=WeMemory API Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/wechat_memory
ExecStart=/path/to/venv/bin/python scripts/start_api.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### 2. 反向代理

**Nginx 配置**:
```nginx
upstream wememory_api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://wememory_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. HTTPS 配置

```bash
# 使用 Let's Encrypt
sudo certbot --nginx -d api.example.com
```

### 4. 性能调优

```bash
# 使用多个 worker 进程
uvicorn api.main:app --workers 4 --host 0.0.0.0 --port 8000

# 或在配置中设置
# config/production.yaml
api:
  workers: 4
  timeout: 30
```

---

## 安全建议

### 1. API 认证（可选）

```yaml
# config/default.yaml
security:
  enable_auth: true
  api_key: ${WEMEMORY_API_KEY}
```

```bash
# 使用 API Key
curl -H "X-API-Key: your-secret-key" \
  http://localhost:8000/api/recall
```

### 2. 限流

```yaml
api:
  rate_limiting:
    enabled: true
    requests_per_minute: 60
```

### 3. HTTPS Only

```yaml
api:
  https_only: true
  ssl_cert: /path/to/cert.pem
  ssl_key: /path/to/key.pem
```

---

## 测试

### 运行测试套件

```bash
# 运行所有 API 测试
python -m pytest tests/test_api_e2e.py -v

# 运行单个测试
python -m pytest tests/test_api_e2e.py::test_health_check -v

# 查看覆盖率
python -m pytest tests/test_api_e2e.py --cov=api
```

---

## 下一步

1. 📖 **了解 API 架构**
   - 详见：[architecture.md](architecture.md)

2. 🧠 **优化搜索质量**
   - 详见：[embedding.md](embedding.md)

3. 🕸️ **使用知识图谱**
   - 详见：[knowledge-graph.md](knowledge-graph.md)

---

返回 [主文档](../README.md)
