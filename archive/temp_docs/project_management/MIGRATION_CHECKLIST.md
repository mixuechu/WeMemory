# 迁移检查清单

**创建日期**: 2026-03-04
**目的**: 确保项目迁移时数据完整性和可追溯性

---

## ✅ 必须迁移的核心数据

### 1. 原始抽取结果（最重要）
```
📁 backups/before_merge_20260303_143226/batch_20260227_001822/
   ├── session_*.json (49,977个文件，637 MB)
   └── 包含完整的entities, events, relationships
```
**重要性**: ⭐⭐⭐⭐⭐
**说明**: 所有后续工作的基础，不可丢失

### 2. Person实体处理结果
```
📁 knowledge_graph/
   ├── person_database.pkl (9.6 MB)          - Person数据库
   ├── person_details_index.json (346 MB)   - 详情索引
   └── merged_entities_by_conversation.json (5.55 MB) - 初步合并结果
```
**重要性**: ⭐⭐⭐⭐⭐

### 3. 人工编辑决策（最终版本）
```
📁 c:/Users/A/Downloads/
   ├── conversation_entity_edits_v1.json    - 最终编辑结果 ⭐⭐⭐⭐⭐
   ├── 手过第一版.json                      - 第一批审核
   └── 手过补充版.json                      - 补充批审核
```
**重要性**: ⭐⭐⭐⭐⭐

### 4. 编辑工具
```
📁 knowledge_graph/
   ├── conversation_entity_editor.html (53 KB)
   ├── merged_entities_data.js (3.1 MB)
   └── person_details_data.js (247 MB)
```
**重要性**: ⭐⭐⭐⭐
**说明**: 如需继续编辑，这些文件必须保留

### 5. 向量知识库（重要）
```
📁 vector_stores/
   ├── conversations_complete.pkl (2.0 GB)              - 完整向量库（183,287个记忆）
   ├── all_conversations_content.faiss (612 MB)         - 内容向量索引
   └── all_conversations_context.faiss (612 MB)         - 上下文向量索引
```
**重要性**: ⭐⭐⭐⭐⭐
**说明**: 已完成的向量检索系统，可独立使用

### 6. 向量生成模块
```
📁 embedding/
   ├── client.py           - Google Vertex AI客户端
   ├── enricher.py         - 文本富化器
   ├── generator.py        - 双向量生成器
   └── README.md           - 模块文档
```
**重要性**: ⭐⭐⭐⭐

### 7. Memory Recall API
```
📁 api/
   ├── main.py                    - FastAPI主服务
   ├── routers/                   - API路由
   ├── services/                  - 业务逻辑
   ├── models/                    - 数据模型
   ├── README.md                  - API文档
   ├── PERFORMANCE_REPORT.md      - 性能测试报告
   ├── QUICKSTART.md              - 快速开始
   ├── performance_test.py        - 性能测试脚本
   └── requirements-api.txt       - API依赖
```
**重要性**: ⭐⭐⭐⭐⭐
**说明**: 已完成并测试的API服务

### 8. 核心脚本
```
📁 knowledge_graph/
   ├── build_person_details_index_optimized.py  - 构建详情索引
   ├── merge_entities.py                        - 融合编辑结果
   ├── extract_first_batch_data.py             - 数据提取
   ├── convert_json_to_js.py                   - 格式转换
   └── batch_extract_all.py                    - 知识抽取
```
**重要性**: ⭐⭐⭐⭐

### 9. 项目文档
```
📁 根目录/
   ├── PROJECT_STATUS.md          - 项目状态（本文档）
   ├── MIGRATION_CHECKLIST.md     - 迁移清单
   ├── README.md                  - 项目说明
   └── ROADMAP.md                 - 开发路线图（如有）
```
**重要性**: ⭐⭐⭐⭐

---

## 📦 可选迁移（辅助文件）

### API相关（如已开发）
```
📁 api/
   ├── main.py
   ├── README.md
   └── performance_test.py
```
**重要性**: ⭐⭐⭐

### 文档与示例
```
📁 docs/
   └── *.md (各类文档)
```
**重要性**: ⭐⭐⭐

---

## 🗑️ 可以归档/不迁移的文件

### 1. 临时调试脚本
以下脚本已完成历史使命，建议归档但不必迁移：
```
knowledge_graph/archive/debugging/
   ├── analyze_failures.py
   ├── analyze_missing_merges.py
   ├── check_*.py (各种检查脚本)
   ├── detailed_check.py
   ├── find_*.py (查找脚本)
   └── quick_*.py (快速测试脚本)
```

### 2. 中间结果文件
以下是过程中产生的中间文件，已有最终版本，可归档：
```
knowledge_graph/archive/intermediate/
   ├── cleanup_results_*.json (清理结果)
   ├── extraction_test_results.json
   ├── failed_conversations.json
   ├── large_conversations_results*.json
   ├── merge_analysis.json
   ├── missing_conversations.json
   ├── quick_analysis.json
   └── relationship_extraction_examples.json
```

### 3. 旧版HTML文件
以下是旧版本的合并建议HTML，最新版已保留：
```
knowledge_graph/archive/old_html/
   ├── intelligent_merge_suggestions.html
   ├── person_merge_by_conversation.html
   ├── person_merge_by_conversation_fixed.html
   ├── person_merge_suggestions.html
   ├── person_merge_suggestions_complete.html
   ├── person_merge_suggestions_ai_supplement.html
   └── (其他旧版HTML)
```

### 4. 旧版脚本
以下是被改进版本替代的脚本：
```
knowledge_graph/archive/old_scripts/
   ├── batch_extract_all_improved.py (被batch_extract_all.py替代)
   ├── build_person_details_index.py (被optimized版替代)
   ├── generate_*.py (各种旧版生成脚本)
   ├── process_*.py (临时处理脚本)
   └── extract_missing.py (临时脚本)
```

---

## 📋 迁移前检查清单

**知识图谱数据**:
- [ ] 1. 验证 `backups/before_merge_20260303_143226/` 完整性（49,977个文件）
- [ ] 2. 确认 `conversation_entity_edits_v1.json` 已备份多份
- [ ] 3. 验证 `person_database.pkl` 可正常加载
- [ ] 4. 验证 `person_details_index.json` 可正常解析
- [ ] 5. 测试 `conversation_entity_editor.html` 可正常打开

**向量知识库**:
- [ ] 6. 验证 `conversations_complete.pkl` 可正常加载（183,287个记忆）
- [ ] 7. 验证 FAISS 索引文件完整性
- [ ] 8. 测试向量检索功能

**API服务**:
- [ ] 9. 验证API服务可正常启动
- [ ] 10. 测试 `/api/recall` 端点
- [ ] 11. 检查性能测试报告

**通用**:
- [ ] 12. 复制所有核心脚本到新位置
- [ ] 13. 复制 `PROJECT_STATUS.md` 到新位置
- [ ] 14. 在新位置运行 `verify_for_migration.py`

---

## 📊 数据大小统计

```
核心数据总大小估算:

知识图谱数据:
- 抽取备份:            637 MB
- Person数据库:        9.6 MB
- 详情索引:            346 MB
- 合并结果:            5.55 MB
- 编辑决策:            ~500 KB
- JS数据文件:          250 MB
小计:                  ~1.25 GB

向量知识库:
- 向量库文件:          2.0 GB
- FAISS索引(content):  612 MB
- FAISS索引(context):  612 MB
小计:                  ~3.2 GB

其他:
- API服务代码:         ~5 MB
- Embedding模块:       ~50 KB
- 核心脚本:            ~1 MB
- 文档:                ~500 KB
小计:                  ~7 MB

------------------------------
总计约:                ~4.5 GB
```

---

## 🔄 迁移后验证步骤

### 1. 数据完整性验证
```python
# 运行验证脚本
python verify_migration.py

# 应检查:
# - 备份文件数量: 49,977个
# - person_database.pkl 加载成功
# - person_details_index.json 解析成功
# - conversation_entity_edits_v1.json 格式正确
```

### 2. 功能验证

**知识图谱工具**:
```bash
# 1. 测试编辑界面
# 双击 conversation_entity_editor.html，检查数据加载

# 2. 测试脚本运行
python build_person_details_index_optimized.py --test
python merge_entities.py --test
```

**向量检索系统**:
```bash
# 3. 测试向量库加载
python -c "import pickle; data = pickle.load(open('vector_stores/conversations_complete.pkl', 'rb')); print(f'记忆数: {len(data)}')"

# 4. 测试API服务
cd api
uvicorn main:app --reload

# 5. 测试查询功能
python test_client.py
```

### 3. 文档验证
- [ ] PROJECT_STATUS.md 可读
- [ ] MIGRATION_CHECKLIST.md 完整
- [ ] README.md 说明清晰

---

## 💡 推荐迁移结构

建议在新环境中使用以下目录结构：

```
wechat_memory_system/
├── data/
│   ├── raw/                          # 原始抽取结果
│   │   └── batch_20260227_001822/    # 49,977个JSON文件
│   ├── knowledge_graph/              # 知识图谱数据
│   │   ├── person_database.pkl
│   │   ├── person_details_index.json
│   │   └── merged_entities_by_conversation.json
│   ├── vector_stores/                # 向量知识库 ⭐
│   │   ├── conversations_complete.pkl
│   │   ├── all_conversations_content.faiss
│   │   └── all_conversations_context.faiss
│   └── edits/
│       ├── conversation_entity_edits_v1.json  ⭐
│       ├── 手过第一版.json
│       └── 手过补充版.json
├── scripts/
│   ├── processing/
│   │   ├── build_person_details_index_optimized.py
│   │   ├── merge_entities.py
│   │   └── batch_extract_all.py
│   └── utils/
│       ├── extract_first_batch_data.py
│       └── convert_json_to_js.py
├── embedding/                        # 向量生成模块 ⭐
│   ├── client.py
│   ├── enricher.py
│   ├── generator.py
│   └── README.md
├── api/                              # Memory Recall API ⭐
│   ├── main.py
│   ├── routers/
│   ├── services/
│   ├── models/
│   ├── README.md
│   ├── PERFORMANCE_REPORT.md
│   └── requirements-api.txt
├── tools/
│   ├── conversation_entity_editor.html
│   ├── merged_entities_data.js
│   └── person_details_data.js
├── docs/
│   ├── PROJECT_STATUS.md
│   ├── MIGRATION_CHECKLIST.md
│   └── README.md
└── archive/                          # 历史文件归档
    ├── debugging/
    ├── intermediate/
    ├── old_html/
    └── old_scripts/
```

---

## ⚠️ 重要提醒

1. **conversation_entity_edits_v1.json** 是当前最宝贵的文件，包含数小时的人工标注成果
2. **备份的49,977个JSON文件** 是所有工作的基础，务必完整迁移
3. 迁移前建议制作额外备份到云存储
4. 迁移后务必验证数据完整性再删除旧数据

---

**文档版本**: v1.0
**创建时间**: 2026-03-04 23:05
