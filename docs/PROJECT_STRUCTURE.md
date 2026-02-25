# 微信记忆系统 - 项目结构设计

## 项目目标
构建一个模块化的、可维护的记忆系统服务，将微信聊天记录转换为Agent可用的向量知识库，提供语义检索能力。

## 模块划分

### 1. 数据加载模块 (data_loader/)
**职责**：微信聊天记录的解析、清洗、预处理
```
data_loader/
├── __init__.py
├── parser.py           # JSON格式的微信记录解析
├── filter.py           # 数据过滤（时间范围、私聊筛选等）
├── session.py          # 会话分片逻辑（时间窗口、滑动窗口）
└── README.md           # 模块说明文档
```

**现有文件映射**：
- filter_old_private_chats.py → data_loader/filter.py
- test_embedding_simple.py中的ConversationSession等类 → data_loader/session.py

---

### 2. 向量生成模块 (embedding/)
**职责**：生成双向量（content + context），管理embedding客户端
```
embedding/
├── __init__.py
├── client.py           # Google Vertex AI客户端封装
├── enricher.py         # 文本富化（添加上下文信息）
├── generator.py        # 双向量生成器（content 85% + context 15%）
├── config.py           # embedding配置（模型、维度等）
└── README.md
```

**现有文件映射**：
- test_embedding_simple.py中的GoogleEmbeddingClient → embedding/client.py
- test_embedding_simple.py中的TextEnricher → embedding/enricher.py
- test_embedding_simple.py中的VectorKnowledgeBasePipeline → embedding/generator.py

---

### 3. 检索模块 (retrieval/)
**职责**：混合检索（BM25 + Vector），向量存储管理
```
retrieval/
├── __init__.py
├── vector_store.py     # 向量存储（SimpleVectorStore, HybridVectorStore）
├── bm25.py             # BM25索引构建和检索
├── hybrid.py           # 混合检索实现（权重配比：BM25:0.5 + Vector:0.5）
├── query.py            # 查询接口和过滤器
├── config.py           # 检索配置（权重、top_k等）
└── README.md
```

**现有文件映射**：
- test_embedding_simple.py中的SimpleVectorStore → retrieval/vector_store.py
- test_hybrid_search.py中的HybridVectorStore → retrieval/vector_store.py
- test_hybrid_search.py中的混合检索逻辑 → retrieval/hybrid.py

---

### 4. 评测模块 (evaluation/)
**职责**：权重配比评测、检索质量评估
```
evaluation/
├── README.md           # 评测说明文档（已有）
├── queries/            # 测试查询（已有）
├── scripts/            # 评测脚本（已有）
└── results/            # 评测结果（已有）
```

**状态**：已整理完成 ✓

---

### 5. 配置和工具 (config/ & utils/)
**职责**：环境配置、通用工具函数
```
config/
├── __init__.py
├── settings.py         # 全局配置（从.env加载）
└── constants.py        # 常量定义

utils/
├── __init__.py
├── logger.py           # 日志工具
└── file_utils.py       # 文件操作工具
```

---

### 6. 主入口和示例 (examples/ & main.py)
**职责**：演示如何使用各个模块
```
examples/
├── 01_data_loading.py       # 示例：加载和预处理微信记录
├── 02_generate_embeddings.py  # 示例：生成向量库
├── 03_hybrid_search.py      # 示例：混合检索
└── 04_batch_process.py      # 示例：批量处理多个对话

main.py                      # CLI入口（未来可扩展）
```

---

### 7. 数据目录
```
chat_data_filtered/          # 过滤后的微信记录
vector_stores/               # 生成的向量库（.pkl文件）
logs/                        # 日志文件
```

---

## 项目根目录结构

```
微信记忆系统/
├── data_loader/             # 数据加载模块
├── embedding/               # 向量生成模块
├── retrieval/               # 检索模块
├── evaluation/              # 评测模块
├── config/                  # 配置
├── utils/                   # 工具
├── examples/                # 使用示例
├── chat_data_filtered/      # 数据（已有）
├── vector_stores/           # 向量库
├── logs/                    # 日志
├── requirements.txt         # Python依赖
├── .env                     # 环境变量（已有）
├── .gitignore
├── README.md                # 项目总览
└── main.py                  # CLI入口
```

---

## 依赖关系

```
main.py / examples/
    ↓
data_loader → embedding → retrieval
    ↓           ↓           ↓
   utils ← config ← evaluation
```

- **data_loader** 不依赖其他模块（最底层）
- **embedding** 依赖 data_loader
- **retrieval** 依赖 embedding（使用向量存储）
- **evaluation** 依赖 retrieval（测试检索效果）
- 所有模块都可以使用 config 和 utils

---

## 模块独立性原则

1. **单一职责**：每个模块只负责一个明确的功能
2. **接口清晰**：模块间通过明确的接口交互，不暴露内部实现
3. **可独立开发**：每个模块可以独立开发、测试、部署
4. **可替换性**：如果要换embedding模型或检索算法，只需修改对应模块
5. **文档完备**：每个模块都有README说明使用方法

---

## 下一步行动

1. ✅ 创建模块目录结构
2. ✅ 拆分现有核心代码到各个模块
3. ✅ 编写各模块的README
4. ✅ 创建使用示例
5. ✅ 删除临时/过时文件
6. ✅ 编写项目总README

---

## 优势

- **可维护性**：模块化结构便于维护和调试
- **可扩展性**：易于添加新功能（如新的embedding模型、检索算法）
- **可测试性**：每个模块可以独立测试
- **可复用性**：模块可以在其他项目中复用
- **团队协作**：不同开发者可以负责不同模块
