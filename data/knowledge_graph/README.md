# 知识图谱数据 (Knowledge Graph Data)

本目录包含精简版的知识图谱数据，基于 138 个精选对话构建。

## 文件说明

### curated_kg.json
**精选知识图谱** - 经过实体合并和关系剪枝优化的知识图谱
- 数据来源：138 个精选对话
- 优化措施：
  - 实体合并（去重同一人物的不同名称）
  - 关系剪枝（删除 80% 冗余关系，保留有价值的家庭/工作/地点关系）
- 格式：JSON
- 大小：约 6MB

### triplets.json
**自然语言三元组** - 从知识图谱生成的优化三元组
- 总数：7,865 条记录
  - 5,297 事件三元组
  - 2,568 关系三元组
- 优化：
  - 事件三元组以人物为中心描述
  - 关系三元组保留有价值的关系
- 格式：JSON
- 大小：约 6MB

### entity_alias_map.json
**实体别名映射** - 用于将不同名称映射到统一实体
- 用途：在查询时将"老板"、"领导"等别名映射到具体人物
- 格式：JSON
- 大小：约 88KB

## 技术细节

### Embedding 模型
使用 **text-multilingual-embedding-002** 模型
- 优势：显著提升中文语义区分度
- 对比实验：相比 text-embedding-004，中文查询召回质量提升明显

### 测试验证
- 测试查询数：111 个
- 召回质量：94%+ 准确率
- 详见：`/tests/comprehensive_test.py`

## 数据生成

三元组数据由以下脚本生成：
```bash
# 1. 从知识图谱生成三元组
python knowledge_graph/triplet_builder.py

# 2. 生成三元组向量索引
python knowledge_graph/embedding_generator.py
```

## 版本历史

- **v4** (当前版本) - 关系剪枝优化 + multilingual embedding
- v3.1 - 实体合并优化
- v3 - 三元组系统引入
- v2 - 知识图谱结构优化
- v1 - 初始版本

## 相关资源

- 三元组向量索引：`/vector_stores/triplets/`
- 对话数据：`/data/conversations/chat_data_filtered/`
- 测试套件：`/tests/`
