# 向量知识库测试 - 环境准备

## 1. 安装Python依赖

```bash
pip install openai qdrant-client python-dotenv
```

## 2. 启动Qdrant向量数据库

### 方式A: Docker（推荐）

```bash
docker run -d -p 6333:6333 -p 6334:6334 \
    -v D:/qdrant_storage:/qdrant/storage \
    qdrant/qdrant:latest
```

### 方式B: 本地安装

下载并运行: https://qdrant.tech/documentation/quick-start/

## 3. 配置OpenAI API Key

在命令行设置环境变量：

```bash
# Windows (CMD)
set OPENAI_API_KEY=sk-your-api-key-here

# Windows (PowerShell)
$env:OPENAI_API_KEY="sk-your-api-key-here"

# Git Bash / Linux / Mac
export OPENAI_API_KEY=sk-your-api-key-here
```

或者创建 `.env` 文件：

```bash
# .env
OPENAI_API_KEY=sk-your-api-key-here
```

## 4. 运行测试

```bash
cd "D:\导出聊天记录excel"
python test_embedding_pipeline.py
```

## 测试内容

脚本会：
1. ✅ 初始化Qdrant集合
2. ✅ 加载"成都乖巧萌"对话（~8.5万条消息）
3. ✅ 切分为会话片段（预计~2000个）
4. ✅ 生成增强文本
5. ✅ 批量生成embeddings
6. ✅ 上传到向量数据库
7. ✅ 测试3种检索场景

## 预计成本

- 消息数: ~8万条
- 会话片段: ~2000个
- Embedding成本: 2000 × 200 tokens × $0.02/1M ≈ **$0.008**（不到1分钱）

## 预计时间

- 会话切分: ~10秒
- Embedding生成: ~2-3分钟（批量处理）
- 总计: **5分钟左右**
