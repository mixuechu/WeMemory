# 归档目录 (Archive)

本目录用于存储项目重构过程中产生的历史数据、临时文件和开发过程文件。

## 目录结构

### full_data_backup/ (~17GB)
**全量数据备份** - 包含项目早期使用的全量数据集
- **不上传到 Git**（已加入 .gitignore）
- 仅本地保留，供需要时参考

#### 内容清单：
- `vector_stores/` (~11GB) - 全量对话向量库（676 对话）
- `chat_data_filtered/` (~4GB) - 全量对话数据
- `extractions/` (~1.5GB) - 知识抽取中间数据
- `backups/` (~635MB) - 各类备份文件
- `knowledge_graph/` (~362MB) - 大型知识图谱索引文件

**为什么备份？**
- 项目从全量数据（676 对话）迁移到精简版（138 对话）
- 全量数据内存消耗过大，不适合快速迭代
- 保留备份供未来扩展或对比验证

---

### temp_scripts/
**临时脚本** - 开发过程中产生的测试和实验脚本

#### 子目录：
- `testing/` - 测试脚本（~60 个）
  - 单元测试、集成测试、验证脚本
  - 大部分已合并到正式测试套件 `/tests/`

- `experiments/` - 实验性脚本
  - 多版本的实体合并建议生成脚本
  - 功能增强实验
  - 模型对比实验

- `deprecated/` - 过时脚本
  - 已完成任务的旧脚本
  - 被新版本替代的代码

---

### temp_docs/
**临时文档** - 开发迭代过程中的文档版本

#### 子目录：
- `iterations/` - 版本迭代文档
  - README 多个版本（README_v1.md, README_v2.md 等）
  - AI 辅助文档（AI_*.md）
  - 旧版模块文档

- `notes/` - 开发笔记
  - TODO 列表
  - 开发日志
  - 快速启动脚本
  - 临时文本文件

---

### temp_outputs/
**临时输出** - 脚本运行产生的临时文件

#### 子目录：
- `logs/` - 日志文件
  - 抽取日志（extraction_log.json）
  - 测试报告（test_report.txt）
  - 各类运行日志

- `html_versions/` - HTML 文件多版本
  - 实体编辑器多个版本
  - 可视化工具的历史版本
  - 调试用 HTML 页面

- `intermediate/` - 中间结果
  - 知识图谱历史版本（v1, v2, v3, v3.1）
  - 临时 JSON 文件
  - 进度保存文件
  - 调试输出

---

## 使用建议

### 查找历史文件
如果需要查找某个功能的历史实现或测试用例，可以在归档目录中搜索：

```bash
# 查找所有测试脚本
find archive/temp_scripts/testing/ -name "*.py"

# 查找特定功能的实验脚本
grep -r "merge_suggestions" archive/temp_scripts/experiments/

# 查看知识图谱历史版本
ls -lh archive/temp_outputs/intermediate/curated_knowledge_graph_v*.json
```

### 磁盘空间管理
如果磁盘空间不足，可以考虑：
1. 压缩 `full_data_backup/`（已经很大）
2. 删除 `temp_outputs/logs/`（可重新生成）
3. 删除 `temp_outputs/intermediate/`（旧版本数据）

### 恢复数据
如果需要恢复全量数据环境：
1. 确认 `archive/full_data_backup/` 完整
2. 将向量库文件复制回 `vector_stores/`
3. 将对话数据复制回 `chat_data_filtered/`
4. 重新运行索引构建脚本

---

## 重要提醒

- **不要删除 `full_data_backup/`**：这是唯一的全量数据备份
- **定期清理临时输出**：`temp_outputs/` 中的文件可以定期清理
- **文档归档**：新的迭代文档应继续放入 `temp_docs/iterations/`
- **脚本归档**：已完成的实验脚本应移到 `temp_scripts/deprecated/`

---

## 版本历史

- **2026-03-09** - 创建归档目录，完成项目重构
  - 全量数据备份（17GB）
  - 临时文件整理归档
  - 精简版提升为生产版本
