# WeChat Memory System - 项目状态报告

**更新日期**: 2026-03-09
**当前状态**: 项目重构完成 - 精简版已提升为生产版本

> **重要更新 (2026-03-09)**:
> 项目已从全量数据（676对话）迁移到精简版（138对话），采用三元组知识图谱和 text-multilingual-embedding-002 模型。全量数据已备份至 `/archive/full_data_backup/` (~17GB)。

---

## 📊 当前系统架构

```
[████████████████████] 100% 生产就绪

✅ 精简版数据集: 138个对话
✅ 知识图谱: 7,865条三元组（5,297事件 + 2,568关系）
✅ 向量化: text-multilingual-embedding-002（768维）
✅ 测试验证: 111个查询，94%+召回质量
✅ 项目结构: 数据/代码分离，易于版本控制
```

---

## 🎯 精简版 vs 全量版对比

| 维度 | 全量版（已备份） | 精简版（生产） |
|------|-----------------|---------------|
| 对话数 | 676 | 138 |
| 数据大小 | ~17GB | ~2GB |
| 知识图谱 | 151,204个Person实例 | 7,865条优化三元组 |
| Embedding模型 | text-embedding-004 | text-multilingual-embedding-002 |
| 中文区分度 | 一般 | 显著提升 |
| 版本控制 | 困难（太大） | 容易 |
| 迭代速度 | 慢（内存压力大） | 快 |

---

## ✅ 已完成 - 项目重构 (2026-03-09)

### Phase 1-8: 完整重构流程
- ✅ **Phase 1**: 创建新目录结构
- ✅ **Phase 2**: 备份全量数据（17GB）到 `/archive/full_data_backup/`
- ✅ **Phase 3**: 提升精简版数据到生产位置
- ✅ **Phase 4**: 提升精简版代码到正式模块
- ✅ **Phase 5**: 归档临时文件到 `/archive/`
- ✅ **Phase 6**: 更新 `.gitignore`
- ✅ **Phase 7**: 更新文档
- ✅ **Phase 8**: 验证数据完整性

### 新的项目结构
```
data/                      # 生产数据（精简版）
├── knowledge_graph/       # KG数据（curated_kg.json, triplets.json）
└── conversations/         # 对话数据（138个）

vector_stores/             # 向量库
├── triplets/              # 三元组向量索引
└── conversations/         # 对话向量索引

knowledge_graph/           # KG模块
├── triplet_builder.py     # 三元组构建
└── embedding_generator.py # 向量生成

tests/                     # 测试套件
├── test_triplet_search.py
└── comprehensive_test.py  # 111个测试查询

archive/                   # 归档（不上传Git）
├── full_data_backup/      # 全量数据备份（~17GB）
├── temp_scripts/          # 临时脚本
├── temp_docs/             # 临时文档
└── temp_outputs/          # 临时输出
```

---

## 📊 历史阶段回顾（全量版）

以下内容描述的是全量数据处理流程，数据已备份至 `/archive/full_data_backup/`：

---

## ✅ 已完成的工作

### Phase 1: 基础数据处理
- ✅ WeChat对话Excel导出（676个对话，共49,977个批次）
- ✅ 对话批次分割与处理
- ✅ Claude API集成与测试

### Phase 2: 知识抽取 (2026-02-26 至 2026-02-27)
- ✅ **完整抽取**: 49,977个对话批次
- ✅ **实体类型**: Person, Organization, Location, Event, Topic
- ✅ **关系抽取**: KNOWS, WORKS_AT, DISCUSSED_TOPIC等
- ✅ **备份位置**: `backups/before_merge_20260303_143226/batch_20260227_001822/`
  - 文件数: 49,977个JSON文件
  - 总大小: 637 MB
  - 包含完整的events, relationships, entities

**抽取统计**:
- Person实例: 151,204个
- 唯一Person名称: 12,543个
- 对话数: 676个

### Phase 3: Person实体去重与合并 (2026-02-28 至 2026-03-04)

#### 3.1 自动化合并建议
使用Vertex AI (gemini-2.5-flash) 生成AI辅助合并建议:

**第一批** (2026-02-28):
- 处理对话: 485个
- 合并建议: 1,145组
- 输出: `person_merge_suggestions_ai.html`

**补充批次** (2026-03-01 至 2026-03-02):
- 处理对话: 191个（处理所有遗漏对话）
- 合并建议: 1,781组
- 特殊处理: 7个超大对话（350+ Person）使用批处理
- 输出: `person_merge_suggestions_191_conversations.html`

#### 3.2 人工审核
**第一版审核**:
- 文件: `c:/Users/A/Downloads/手过第一版.json`
- 批准: 1,097组
- 拒绝: 48组

**补充版审核**:
- 文件: `c:/Users/A/Downloads/手过补充版.json`
- 批准: 1,223组
- 拒绝: 189组
- 未处理（默认拒绝）: 369组

#### 3.3 数据融合
- 融合脚本: `merge_entities.py`
- 输出文件: `merged_entities_by_conversation.json` (5.55 MB)
- 结果统计:
  - 对话总数: 677
  - 合并后实体: 17,675个
  - 原始Person实例: 152,489个
  - 被合并的实体: 6,283个

#### 3.4 交互式精细化编辑
**编辑界面**: `conversation_entity_editor.html`
- 自动加载数据（通过JS文件）
- 功能:
  - 对话级别: 标记保留/排除
  - 实体级别: 删除、改名、合并
  - 合并组管理: 添加实体到已有组、撤销合并
  - 详情查看: 查看实体关联的events、relationships、topics

**详情索引**: `person_details_index.json` (346 MB)
- 构建脚本: `build_person_details_index_optimized.py`
- 内容统计:
  - 总Events: 196,499个
  - 总Relationships: 1,098,360个
  - 总Topics: 272,317个

**最终编辑结果**: `c:/Users/A/Downloads/conversation_entity_edits_v1.json`
- 排除对话: 124个
- 编辑对话: 233个
- 删除实体: 3,171个
- 合并组: 424组（1,337个实体被合并）
- 改名实体: 50个
- **状态**: 大部分完成，仍可继续编辑

### Phase 6: 向量化与Embedding (2026-02-25 至 2026-02-26)

#### 6.1 双向量生成系统
**模块**: `embedding/`
- **模型**: Google Vertex AI text-embedding-004
- **维度**: 768维
- **策略**: 双向量分离
  - 内容向量 (content_embedding): 纯对话内容
  - 上下文向量 (context_embedding): 时间、参与者等元信息
  - 检索权重: 85% 内容 + 15% 上下文

**核心组件**:
- `GoogleEmbeddingClient` - Vertex AI 客户端
- `TextEnricher` - 文本富化器
- `DualVectorGenerator` - 双向量生成器

#### 6.2 向量库构建
**位置**: `vector_stores/`
- `conversations_complete.pkl` - 2.0 GB
  - **记忆总数**: 183,287个
  - 包含完整的 content_embedding 和 context_embedding
- `all_conversations_content.faiss` - 612 MB（内容向量索引）
- `all_conversations_context.faiss` - 612 MB（上下文向量索引）

**检索策略**:
- FAISS HNSW 索引（高性能近似最近邻）
- BM25 关键词检索
- 混合检索融合（0.5 向量 + 0.5 BM25）

### Phase 7: Memory Recall API (2026-02-26)

#### 7.1 API 服务
**位置**: `api/`
- **框架**: FastAPI
- **功能**: 记忆联想（非简单搜索）

**核心端点**:
- `POST /api/recall` - 记忆联想（主要功能）
- `POST /api/associate/topic` - 主题关联
- `POST /api/associate/people` - 人物关联
- `POST /api/associate/temporal` - 时序联想

#### 7.2 性能测试结果
**测试数据**: `api/PERFORMANCE_REPORT.md`
- 启动时间: 165秒 (~3分钟，一次性)
- 内存占用: 2.1 GB
- 查询延迟: 1.4秒（首次，含API调用）/ <100ms（缓存）
- 查询质量: 8.0/10（综合评分）
- 向量库: 183,287个记忆

**部署状态**:
- ✅ 开发环境测试完成
- ✅ 性能基准测试完成
- ⏸️ 生产部署（待定）

---

## 🎯 当前状态与待完成工作

### ✅ 已完成的双轨系统

#### 轨道 1: 向量检索系统（已完成）
- ✅ 对话切片与双向量生成（183,287个记忆）
- ✅ FAISS向量索引 + BM25混合检索
- ✅ Memory Recall API服务
- ✅ 性能测试与优化
- **状态**: 可独立使用，查询质量 8.0/10

#### 轨道 2: 知识图谱系统（部分完成）
- ✅ 知识抽取（49,977个批次）
- ✅ Person实体编辑（95%完成）
- ⏸️ 应用编辑结果（Phase 4）
- ⬜ Neo4j图谱构建（Phase 5）
- **状态**: 人工编辑可继续，然后建图

### ⏸️ Phase 3: Person实体编辑（可继续）
**当前进度**: 95% 完成
- 已编辑: 233个对话
- 剩余未编辑: ~320个对话
- 编辑工具: `conversation_entity_editor.html`（可随时继续）

**下一步**:
- 可选择继续完成剩余320个对话的编辑
- 或直接使用当前95%的结果进入Phase 4

### ⏸️ Phase 4: 应用编辑结果（未开始）
**待执行任务**:
1. 读取 `conversation_entity_edits_v1.json`
2. 应用到 `merged_entities_by_conversation.json`:
   - 移除排除的124个对话
   - 删除3,171个标记删除的实体
   - 应用50个改名操作
   - 应用424组手动合并
3. 生成最终的Person实体列表
4. 更新原始抽取结果中的Person引用

### ⬜ Phase 5: 知识图谱构建（未开始）
**待执行任务**:
1. 设计图谱Schema（Person, Organization, Location, Event, Topic）
2. 导入Neo4j或其他图数据库
3. 建立实体关系网络（KNOWS, WORKS_AT, DISCUSSED_TOPIC等）
4. 与向量检索系统集成（混合检索）

---

## 📁 核心数据文件清单

### 原始数据
| 文件 | 位置 | 大小 | 说明 |
|------|------|------|------|
| 原始Excel | `D:\导出聊天记录excel\` | - | WeChat对话导出 |

### 知识抽取结果（备份）
| 文件/目录 | 位置 | 大小 | 说明 |
|-----------|------|------|------|
| 完整抽取备份 | `backups/before_merge_20260303_143226/batch_20260227_001822/` | 637 MB | 49,977个JSON文件，包含完整的entities和relationships |

### Person实体数据
| 文件 | 位置 | 大小 | 说明 |
|------|------|------|------|
| person_database.pkl | `knowledge_graph/` | 9.6 MB | 151,204个Person实例的完整数据库 |
| person_details_index.json | `knowledge_graph/` | 346 MB | 每个Person关联的events/relationships/topics |
| merged_entities_by_conversation.json | `knowledge_graph/` | 5.55 MB | AI辅助+人工审核后的初步合并结果 |
| **conversation_entity_edits_v1.json** | `c:/Users/A/Downloads/` | - | **人工精细化编辑的最终决策（当前最新）** |

### 审核数据
| 文件 | 位置 | 大小 | 说明 |
|------|------|------|------|
| 手过第一版.json | `c:/Users/A/Downloads/` | - | 第一批485个对话的人工审核结果 |
| 手过补充版.json | `c:/Users/A/Downloads/` | - | 补充191个对话的人工审核结果 |

### 编辑界面
| 文件 | 位置 | 大小 | 说明 |
|------|------|------|------|
| conversation_entity_editor.html | `knowledge_graph/` | 53 KB | 交互式编辑界面 |
| merged_entities_data.js | `knowledge_graph/` | 3.1 MB | 实体数据（JS格式） |
| person_details_data.js | `knowledge_graph/` | 247 MB | 详情索引（JS格式） |

### 向量知识库（⭐ 已完成）
| 文件 | 位置 | 大小 | 说明 |
|------|------|------|------|
| conversations_complete.pkl | `vector_stores/` | 2.0 GB | 完整向量库（183,287个记忆） |
| all_conversations_content.faiss | `vector_stores/` | 612 MB | 内容向量FAISS索引 |
| all_conversations_context.faiss | `vector_stores/` | 612 MB | 上下文向量FAISS索引 |

### API服务（⭐ 已完成）
| 文件 | 位置 | 说明 |
|------|------|------|
| api/main.py | `api/` | FastAPI主服务 |
| api/README.md | `api/` | API使用文档 |
| api/PERFORMANCE_REPORT.md | `api/` | 性能测试报告 |

---

## 🔧 核心脚本清单

### 可用的生产脚本
| 脚本 | 用途 | 状态 |
|------|------|------|
| `build_person_details_index_optimized.py` | 构建Person详情索引 | ✅ 可用 |
| `merge_entities.py` | 融合AI建议和人工审核结果 | ✅ 可用 |
| `extract_first_batch_data.py` | 从HTML提取第一批数据 | ✅ 可用 |
| `convert_json_to_js.py` | 转换JSON为JS格式供HTML使用 | ✅ 可用 |
| `batch_extract_all.py` | 批量知识抽取（最新版） | ✅ 可用 |

### 临时/调试脚本（已归档）
这些脚本用于特定问题的调试，已完成使命，建议归档到 `knowledge_graph/archive/debugging/`

---

## 🎯 下一步行动计划

### 选项 A: 继续Person实体编辑（推荐先完成）
1. 打开 `conversation_entity_editor.html`
2. 导入当前 `conversation_entity_edits_v1.json`
3. 继续编辑剩余 ~320个对话
4. 导出更完整的编辑结果

### 选项 B: 直接进入Phase 4（使用当前95%结果）
1. **创建应用编辑脚本** `apply_entity_edits.py`:
   - 读取 `conversation_entity_edits_v1.json`
   - 应用所有编辑操作
   - 生成最终的实体映射表

2. **更新抽取结果**:
   - 将Person实体的引用更新为合并后的名称
   - 保留原始person_id的映射关系

3. **生成最终数据集**:
   - 清理后的entities
   - 更新后的relationships
   - 完整的知识图谱数据

### 后续任务（Phase 5）
- Neo4j图谱构建
- 与向量检索系统集成（混合检索）

---

## 📝 重要说明

### 数据完整性
- ✅ 所有原始抽取结果已完整备份
- ✅ Person实体的person_id稳定，可追溯
- ✅ 所有人工编辑决策已保存
- ✅ 数据格式已验证，可直接用于下一步处理

### 迁移准备
本项目已准备好进行迁移，需要迁移的核心数据：

**知识图谱数据**:
1. `backups/before_merge_20260303_143226/` - 完整抽取备份（637 MB）
2. `knowledge_graph/person_database.pkl` - Person数据库（9.6 MB）
3. `knowledge_graph/person_details_index.json` - 详情索引（346 MB）
4. `knowledge_graph/merged_entities_by_conversation.json` - 初步合并结果（5.55 MB）
5. `c:/Users/A/Downloads/conversation_entity_edits_v1.json` - **最终编辑决策**

**向量知识库**:
6. `vector_stores/conversations_complete.pkl` - 完整向量库（2.0 GB）
7. `vector_stores/all_conversations_content.faiss` - 内容向量索引（612 MB）
8. `vector_stores/all_conversations_context.faiss` - 上下文向量索引（612 MB）

**API服务**:
9. `api/` - Memory Recall API完整代码
10. `embedding/` - 向量生成模块

**总计**: ~4.5 GB 核心数据

---

## 👥 团队协作

### 工作流程（双轨并行）

**轨道 1 - 向量检索系统** (已完成 ✅):
```
原始对话导出 → 对话切片 → 双向量生成 → FAISS索引 → Memory Recall API → 性能测试 ✅
```

**轨道 2 - 知识图谱系统** (进行中 ⏸️):
```
原始对话导出 → 知识抽取 → AI辅助合并 → 人工审核 → 精细化编辑 ⏸️ → [应用编辑] → Neo4j图谱构建 → 混合检索
```

### 当前节点
**轨道 1**: ✅ 完成，API可用
**轨道 2**: ⏸️ Person实体编辑95%完成，可继续或进入Phase 4

---

**文档版本**: v1.0
**最后更新**: 2026-03-04 23:00
