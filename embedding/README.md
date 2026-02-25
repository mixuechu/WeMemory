# 向量生成模块 (embedding)

## 功能
为会话片段生成双向量embeddings，使用Google Vertex AI的text-embedding-004模型。

## 模块结构

```
embedding/
├── __init__.py         # 模块导出
├── client.py           # Google Vertex AI客户端
├── enricher.py         # 文本富化器
├── generator.py        # 双向量生成器
└── README.md           # 本文档
```

## 核心类

### 1. GoogleEmbeddingClient (client.py)
Google Vertex AI Embedding客户端

**配置**：
需要在 `.env` 文件中设置以下环境变量：
```
VITE_GOOGLE_CLOUD_PROJECT=your-project-id
VITE_GOOGLE_CLOUD_LOCATION=us-central1
VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}
```

**使用方法**：
```python
from embedding import GoogleEmbeddingClient

client = GoogleEmbeddingClient()
embeddings = client.get_embeddings(["你好", "世界"])
# 返回: [[768维向量], [768维向量]]
```

**特性**：
- 模型: text-embedding-004
- 维度: 768
- 批处理: 每批5条（API限制）
- 错误处理: 失败时返回零向量

### 2. TextEnricher (enricher.py)
文本富化器 - 为会话添加上下文信息

**双向量策略**：
1. **内容向量** (content_text): 纯对话内容
   ```
   张三: 今天天气真不错
   李四: 是啊，要不要出去走走
   ```

2. **上下文向量** (context_text): 元信息
   ```
   2025年2月25日下午 参与者：张三, 李四
   ```

**使用方法**：
```python
from embedding import TextEnricher

enricher = TextEnricher()
content_text, context_text = enricher.enrich_session(session)
```

### 3. DualVectorGenerator (generator.py)
双向量生成器 - 完整的embedding生成流程

**流程**：
1. 文本富化：为每个session生成 content_text 和 context_text
2. 批量embedding：分别生成内容和上下文向量
3. 保存结果：将embeddings附加到session对象上

**使用方法**：
```python
from embedding import DualVectorGenerator

generator = DualVectorGenerator()
sessions = generator.generate(sessions, batch_size=10)

# sessions现在包含embeddings
for session in sessions:
    print(f"内容向量: {session.content_embedding}")  # 768维
    print(f"上下文向量: {session.context_embedding}")  # 768维
```

## 完整使用示例

```python
from pathlib import Path
from data_loader import WeChatParser, SessionBuilder
from embedding import DualVectorGenerator

# 1. 加载和切分
file_path = Path("chat_data_filtered/alex_li/alex_li.json")
messages, metadata = WeChatParser.load_conversation(file_path)

builder = SessionBuilder()
sessions = builder.split_into_sessions(messages, metadata)

# 2. 生成双向量
generator = DualVectorGenerator()
sessions = generator.generate(sessions, batch_size=10)

# 3. 查看结果
session = sessions[0]
print(f"内容文本: {session.content_text}")
print(f"上下文文本: {session.context_text}")
print(f"内容向量维度: {len(session.content_embedding)}")  # 768
print(f"上下文向量维度: {len(session.context_embedding)}")  # 768
```

## 双向量设计理念

### 为什么使用双向量？
1. **分离关注点**：
   - 内容向量：捕捉对话主题和语义
   - 上下文向量：捕捉时间、参与者等元信息

2. **提高检索质量**：
   - 85%权重给内容向量（主要语义）
   - 15%权重给上下文向量（辅助信息）

3. **避免模板污染**：
   - 早期单向量方案：模板文本占80%，导致所有向量相似度0.72-0.73
   - 双向量方案：分离后，内容向量纯净，区分度提升

### 权重配比
在检索时（retrieval模块），双向量的组合方式：
```python
final_score = 0.85 * content_similarity + 0.15 * context_similarity
```

## 依赖关系
- **依赖**: `data_loader` 模块（使用ConversationSession）
- **被依赖**: `retrieval` 模块（使用生成的embeddings）

## 性能考虑
- **批处理**: 建议batch_size=10（双向量会发2倍API请求）
- **API限制**: Google每批最多5条，已内置处理
- **时间估算**: 1000个sessions约需10-15分钟（取决于网络）

## 未来扩展
1. 支持其他embedding模型（OpenAI, HuggingFace等）
2. 本地embedding模型（离线使用）
3. 缓存机制（避免重复embedding）
4. 多线程并发（加速处理）
