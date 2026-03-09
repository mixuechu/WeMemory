# 归档清单

归档时间: 2026-02-26

## 已完成脚本 (5个)
**completed_scripts/**

这些脚本已执行完成，完成了特定的一次性任务：

1. `fix_event_person_relationships.py` - Event-Person关系修复（单线程版本）
2. `fix_event_person_relationships_batch.py` - Event-Person关系修复（批量并行版本）
3. `execute_manual_merges.py` - 执行用户确认的Person实体合并
4. `set_person_names_and_aliases.py` - 设置关键人物的正式名称和别名
5. `clean_generic_persons.py` - 清理泛指实体（已被auto_graph_cleaner替代）

---

## 测试脚本 (34个)
**tests/**

开发和调试过程中使用的测试脚本：

### 提取测试
- `test_single_extraction.py` - 单条消息提取测试
- `test_flash_extraction.py` - Gemini Flash模型测试
- `test_claude_extraction.py` - Claude模型测试
- `test_extraction_quality.py` - 提取质量评估
- `test_specific_conversations.py` - 特定对话测试
- `test_jiyue_only.py` - 吉月对话专项测试
- `test_jy_only.py` - JY对话专项测试
- `test_three_users.py` - 三个用户测试

### 模型测试
- `test_all_gemini_models.py` - 所有Gemini模型对比
- `test_gemini25_speed.py` - Gemini 2.5速度测试
- `test_gemini25_response.py` - Gemini 2.5响应测试
- `test_correct_models.py` - 模型正确性验证
- `list_available_models.py` - 列出可用模型

### API测试
- `test_vertexai_api.py` - Vertex AI API测试
- `test_claude_rest_api.py` - Claude REST API测试

### 批量处理测试
- `test_batch_fix.py` - 批量修复测试
- `test_batch_simple.py` - 简单批量测试
- `test_batch_step1.py` - 批量步骤1测试
- `test_batch_step2.py` - 批量步骤2测试

### 清理器测试
- `test_intelligent_cleaner.py` - 智能清理器测试
- `test_llm_only.py` - 纯LLM判断测试

### 调试脚本
- `debug_gemini25.py` - Gemini 2.5调试
- `debug_json_error.py` - JSON错误调试
- `debug_json_failures.py` - JSON失败分析

### 验证脚本
- `validate_extraction_quality.py` - 提取质量验证
- `validate_jy_quality.py` - JY对话质量验证

### 检查脚本
- `check_conversations.py` - 检查对话列表
- `check_event_stats.py` - Event统计检查
- `check_vector_store.py` - 向量存储检查

### 查询脚本
- `list_jiyue_persons.py` - 列出吉月相关Person

### 其他测试
- `test_regex.py` - 正则表达式测试
- `test_single_with_retry.py` - 带重试的单次提取
- `retest_gemini25.py` - Gemini 2.5重测
- `quick_model_test.py` - 快速模型测试

---

## 分析脚本 (15个)
**analysis/**

用于数据分析、统计和可视化的工具：

### 图谱分析
- `analyze_graph_structure.py` - 图结构分析
- `analyze_json_failures.py` - JSON失败分析
- `analyze_test_results.py` - 测试结果分析
- `analyze_users.py` - 用户分析

### 结果展示
- `show_analysis_summary.py` - 分析摘要
- `show_cleanup_results.py` - 清理结果展示
- `show_group_top20.py` - 分组Top20
- `show_personal_top20.py` - 个人Top20
- `show_top20.py` - 通用Top20
- `show_top50.py` - Top50统计

### 其他分析
- `comprehensive_model_comparison.py` - 全面模型对比
- `monitor_extraction.py` - 提取过程监控
- `calculate_after_pruning.py` - 剪枝后计算
- `run_analysis_only.py` - 仅运行分析
- `find_users.py` - 查找用户

---

## 旧版本脚本 (6个)
**old_versions/**

已被新版本替代的脚本：

1. `intelligent_graph_cleaner.py` - 智能清理器（旧版，单个处理）
2. `intelligent_graph_cleaner_batch.py` - 智能清理器（批量版，已被auto版本替代）
3. `build_neo4j_from_jy.py` - 从JY对话构建图（旧版）
4. `build_neo4j_test.py` - 构建测试（旧版）
5. `fix_existing_extractions.py` - 修复现有提取（旧版）
6. `reset_neo4j_password.py` - 重置Neo4j密码工具

---

## 日志文件 (2个)
**logs/**

1. `event_fix.log` - Event-Person关系修复日志（第一次运行，无别名版本）
2. `event_fix_v2.log` - Event-Person关系修复日志（第二次运行，含别名版本）

---

## 历史文档 (6个)
**docs/**

开发过程中的分析报告和实验文档：

1. `COMPREHENSIVE_ANALYSIS_REPORT.md` - 综合分析报告
2. `EXTRACTION_QUALITY_REPORT.md` - 提取质量报告
3. `FINAL_PLAN.md` - 最终计划
4. `MODEL_SELECTION_SUMMARY.md` - 模型选择总结
5. `QUALITY_COMPARISON_2.0_vs_2.5.md` - Gemini 2.0 vs 2.5质量对比
6. `QUALITY_COMPARISON_ALL_MODELS.md` - 全模型质量对比

---

## 如何查找归档文件

### 按功能查找
- **需要参考测试代码**: `tests/`
- **需要数据分析工具**: `analysis/`
- **需要查看历史决策**: `docs/`
- **需要查看日志**: `logs/`
- **需要参考已完成的脚本**: `completed_scripts/`

### 按时间查找
所有文件的修改时间保留，可以使用:
```bash
ls -lt archive/*/ | head -20  # 查看最近修改的文件
```

### 恢复文件
如果需要恢复某个归档文件到根目录:
```bash
cp archive/tests/test_single_extraction.py .
```

---

## 归档原则

**保留在根目录的脚本:**
- 核心生产脚本（full_extraction.py, auto_graph_cleaner.py等）
- 工具库（graph_manager.py）
- 核心设计文档

**归档到archive的脚本:**
- 一次性执行完成的脚本
- 测试和调试脚本
- 分析和统计工具
- 已被替代的旧版本
- 历史文档和报告

