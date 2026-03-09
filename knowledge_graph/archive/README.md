# Archive 归档目录

**最后更新**: 2026-03-04
**归档原因**: Phase 3完成，清理历史调试和临时文件，准备进入Phase 4

---

## 📁 目录结构

```
archive/
├── debugging/        # 调试和检查脚本（~20个）
├── intermediate/     # 中间结果文件（~20个JSON）
├── old_html/         # 旧版HTML界面（~8个）
└── old_scripts/      # 被替代的旧版脚本（~40个）
```

---

## 🔍 debugging/ - 调试脚本

用于特定问题诊断的一次性脚本，已完成使命：

**分析类**: `analyze_*.py` - 失败原因、遗漏合并、Person实体等分析
**检查类**: `check_*.py` - 完整性、进度、关系抽取等检查
**查找类**: `find_*.py` - 查找遗漏批次、对话样本等
**快速工具**: `quick_*.py` - 快速测试和分析

**文件数**: ~20个
**用途**: 调试抽取流程、验证数据完整性

---

## 📊 intermediate/ - 中间结果文件

处理过程中产生的中间数据，已有最终版本：

- **清理结果**: `cleanup_results_*.json` - 图谱清理中间结果
- **失败记录**: `*failed*.json` - 失败和遗漏的对话
- **分析报告**: `*_analysis*.json` - 各类分析结果
- **重试结果**: `retry_*.json`, `remaining_*.json`

**文件数**: ~20个JSON
**大小**: 约5-10 MB
**用途**: 问题追踪、进度记录

---

## 🖥️ old_html/ - 旧版HTML界面

历史版本的合并建议查看界面：

- `person_merge_suggestions_ai.html` - AI辅助版（第一批485个对话）
- `person_merge_suggestions_191_conversations.html` - 补充191个对话
- `person_merge_by_conversation*.html` - 早期按对话分组版本
- 其他早期版本...

**文件数**: ~8个
**大小**: 约5 MB
**替代**: `conversation_entity_editor.html` (主目录)

---

## 🔧 old_scripts/ - 被替代的旧版脚本

已被改进版本替代的脚本：

### 核心替代
- `build_person_details_index.py` → `build_person_details_index_optimized.py` ✅
- `batch_extract_all_improved.py` → `batch_extract_all.py` ✅

### 临时脚本（~40个）
- **生成类**: `generate_*.py` - 各版本合并建议生成
- **处理类**: `process_*.py` - 临时数据处理
- **重试类**: `retry_*.py` - 失败任务重试
- **测试类**: `test_*.py` - 各种测试验证
- **步骤类**: `step*.py` - 分步骤旧工作流
- **验证类**: `verify_*.py` - 数据验证

**文件数**: ~40个
**用途**: 历史问题解决、流程优化

---

## 📈 归档统计

| 类别 | 文件数 | 说明 |
|------|--------|------|
| debugging/ | ~20 | 调试脚本 |
| intermediate/ | ~20 | 中间JSON |
| old_html/ | ~8 | 旧版界面 |
| old_scripts/ | ~40 | 旧版脚本 |
| **总计** | **~90** | **归档文件** |

---

## ⚠️ 重要说明

1. **已归档但未删除** - 可查看历史问题解决过程
2. **可选择性迁移** - 迁移新环境时可不迁移归档文件
3. **稳定后删除** - 确认新系统稳定运行后可删除

---

## 🎯 当前保留的核心文件

主目录现仅保留以下核心文件：

### 生产脚本
- `batch_extract_all.py` - 知识抽取
- `build_person_details_index_optimized.py` - 构建详情索引
- `merge_entities.py` - 融合编辑结果
- `extract_first_batch_data.py` - 数据提取
- `convert_json_to_js.py` - 格式转换

### 数据文件
- `person_database.pkl` - Person数据库
- `person_details_index.json` - 详情索引
- `merged_entities_by_conversation.json` - 合并结果
- `all_191_results.json` - 补充批结果
- `first_batch_merge_suggestions.json` - 第一批建议

### 工具
- `conversation_entity_editor.html` - 编辑界面
- `merged_entities_data.js` / `person_details_data.js` - 数据文件

---

**归档执行**: 自动归档脚本
**归档时间**: 2026-03-04 23:15
