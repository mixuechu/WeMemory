# 知识图谱模块 (Knowledge Graph Module)

**最后更新**: 2026-03-09
**当前状态**: 精简版已提升为生产版本
**数据规模**: 138 个对话，7,865 条三元组

---

## 核心功能

本模块负责从对话中提取结构化知识，构建三元组，并生成向量索引。

### 1. 三元组构建 (triplet_builder.py)
从知识图谱生成优化的自然语言三元组

**功能**:
- 读取知识图谱 JSON 文件
- 提取事件和关系信息
- 生成自然语言描述的三元组
- 应用剪枝策略（保留有价值的关系）

**使用**:
```bash
python knowledge_graph/triplet_builder.py
```

**输出**: `data/knowledge_graph/triplets.json`

### 2. 向量生成 (embedding_generator.py)
为三元组生成向量嵌入并构建 FAISS 索引

**功能**:
- 使用 text-multilingual-embedding-002 模型
- 为每个三元组生成 768 维向量
- 构建 FAISS 索引用于快速检索

**使用**:
```bash
python knowledge_graph/embedding_generator.py
```

**输出**: `vector_stores/triplets/`

---

## 其他脚本

### 全量抽取（用于全量数据）
- `full_extraction.py` - 从对话批量提取知识
- `batch_extract_all.py` - 批次化抽取管理

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
