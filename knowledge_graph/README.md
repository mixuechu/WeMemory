# 知识图谱模块 (Knowledge Graph Module)

**最后更新**: 2026-03-10
**当前状态**: 完整 Pipeline 集成，生产就绪
**推荐使用**: `pipeline/graph_building.py` (通过 `run_pipeline.py` 调用)

---

## 概述

本模块负责从对话中提取结构化知识，构建三元组，并生成向量索引。

### 核心创新

🎯 **自然语言三元组** - 不使用传统图数据库（Neo4j），直接将知识图谱转换为自然语言三元组进行向量检索

**优势**:
- ⚡ 性能提升 3-5x（相比 Neo4j 图查询）
- 🔍 更好的语义理解（向量检索 vs 路径匹配）
- 🚀 更简单的架构（无需维护图数据库）

---

## Pipeline 集成 ⭐ (推荐)

**推荐使用 Pipeline 统一流程**，而非直接运行本目录的脚本：

```bash
# 完整流程（包含知识抽取和图谱构建）
python scripts/run_pipeline.py --all

# 只运行知识抽取
python scripts/run_pipeline.py --step knowledge_extraction

# 只运行图谱构建
python scripts/run_pipeline.py --step graph_building
```

详见: [Pipeline 文档](../pipeline/README.md)

---

## 模块组成

### 1. 知识抽取 (通过 Pipeline)

**实现**: `pipeline/knowledge_extraction.py`

**功能**:
- 使用 **Gemini 2.5 Flash** 从对话中抽取结构化知识
- 提取: People, Organizations, Topics, Events, Locations, Relationships
- 自动重试机制（最多3次）
- Token 使用统计

**输出**: `data/knowledge_graph/curated_kg.json`

**配置** (`config/default.yaml`):
```yaml
vertex_ai:
  extraction:
    model: gemini-2.5-flash
    max_tokens: 16000
    temperature: 0.0
```

### 2. 三元组构建 (通过 Pipeline)

**实现**: `pipeline/graph_building.py`

**功能**:
- 从知识图谱生成自然语言三元组
- 添加语义增强（别名、关系语义、时间信息）
- 生成 768 维向量（text-multilingual-embedding-002）
- 构建 FAISS 索引

**输出**:
- `data/knowledge_graph/triplets.json` - 三元组数据
- `vector_stores/triplets/embeddings.pkl` - 三元组向量
- `vector_stores/triplets/index.faiss` - FAISS 索引

---

## 参考实现（仅供参考）

本目录包含的独立脚本是早期实现，**不推荐直接使用**，建议通过 Pipeline 调用：

### triplet_builder.py (已集成到 Pipeline)

原始三元组构建实现，现已集成到 `pipeline/graph_building.py`。

### embedding_generator.py (已集成到 Pipeline)

原始向量生成实现，现已集成到 `pipeline/graph_building.py`。

### 图谱构建
- `build_neo4j_graph.py` - 构建 Neo4j 图数据库
- `graph_manager.py` - 图谱管理工具

### 实体管理
- `merge_entities.py` - 合并重复实体
- `analyze_person_entities.py` - 分析人物实体

### 工具脚本
- `auto_graph_cleaner.py` - 自动清理冗余关系
- `build_person_details_index_optimized.py` - 构建人物详情索引

---

## 数据流程

```
对话数据 → 知识抽取 → 实体合并 → 关系剪枝 → 知识图谱 → 三元组 → 向量索引
```

---

## 测试

```bash
# 三元组搜索测试
python tests/test_triplet_search.py

# 综合测试套件
python tests/comprehensive_test.py
```

---

## 归档

历史数据和脚本已移至：
- 全量数据：`/archive/full_data_backup/`
- 旧脚本：`/archive/temp_scripts/`
- 旧文档：`/archive/temp_docs/`

详见 `/archive/README.md`

---

## 相关资源

- 知识图谱数据：`/data/knowledge_graph/`
- 三元组向量库：`/vector_stores/triplets/`
- 测试套件：`/tests/`
