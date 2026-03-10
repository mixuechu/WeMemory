# WeMemory 脚本工具

本目录包含 WeMemory 项目的核心脚本工具。

---

## 核心脚本

### run_pipeline.py - Pipeline 统一入口 ⭐

**功能**: WeMemory 端到端数据处理的统一入口脚本。

**使用方法**:

```bash
# 运行完整流程（4个步骤）
python scripts/run_pipeline.py --all

# 从头开始（清除检查点）
python scripts/run_pipeline.py --all --fresh

# 运行单个步骤
python scripts/run_pipeline.py --step data_cleaning
python scripts/run_pipeline.py --step embedding
python scripts/run_pipeline.py --step knowledge_extraction
python scripts/run_pipeline.py --step graph_building

# 使用自定义配置
python scripts/run_pipeline.py --all --config my_config.yaml

# 查看检查点状态
python scripts/run_pipeline.py --status

# 清除所有检查点
python scripts/run_pipeline.py --clear
```

**Pipeline 步骤**:

1. **data_cleaning**: 清洗对话数据
   - 输入: `data/conversations/chat_data_filtered/`
   - 输出: `data/conversations/cleaned/`

2. **embedding**: 生成双向量 embeddings
   - 输入: `data/conversations/cleaned/`
   - 输出: `vector_stores/conversations/`

3. **knowledge_extraction**: 使用 Gemini 抽取知识图谱
   - 输入: `data/conversations/cleaned/`
   - 输出: `data/knowledge_graph/curated_kg.json`

4. **graph_building**: 构建三元组向量索引
   - 输入: `data/knowledge_graph/curated_kg.json`
   - 输出: `data/knowledge_graph/triplets.json` + `vector_stores/triplets/`

**特性**:
- ✅ 支持断点续传（自动保存检查点）
- ✅ 实时进度显示
- ✅ 详细统计信息
- ✅ 错误处理和重试机制

**详细文档**: [Pipeline 模块](../pipeline/README.md)

---

## 其他脚本

### （未来扩展）

- `export_data.py` - 数据导出工具
- `validate_data.py` - 数据验证工具
- `benchmark.py` - 性能基准测试

---

## 使用示例

### 完整流程示例

```bash
# 1. 准备数据
# 将 WeChat 导出的 JSON 文件放到 data/conversations/chat_data_filtered/

# 2. 配置环境变量
# 编辑 .env 文件，设置 Google Cloud 凭证

# 3. 运行完整 Pipeline
python scripts/run_pipeline.py --all

# 4. 等待处理完成（约15-20分钟）
# 查看输出统计信息

# 5. 启动 API 服务
python api/main.py
```

### 增量更新示例

```bash
# 1. 添加新的对话文件到 data/conversations/chat_data_filtered/

# 2. 只运行 embedding 步骤（会自动跳过已处理的文件）
python scripts/run_pipeline.py --step embedding

# 3. 更新知识图谱
python scripts/run_pipeline.py --step knowledge_extraction
python scripts/run_pipeline.py --step graph_building
```

### 错误恢复示例

```bash
# 1. Pipeline 中断或出错后，直接重新运行
python scripts/run_pipeline.py --all
# 会自动从检查点继续，跳过已成功的文件

# 2. 如果需要重新处理某个步骤
python scripts/run_pipeline.py --step embedding --fresh
# --fresh 会清除该步骤的检查点，从头开始
```

---

## 检查点管理

### 检查点位置

检查点保存在 `.checkpoints/` 目录：

```
.checkpoints/
├── data_cleaning.json
├── embedding.json
├── knowledge_extraction.json
└── graph_building.json
```

### 检查点格式

```json
{
  "processed_items": ["file1.json", "file2.json"],
  "stats": {
    "total": 138,
    "success": 136,
    "failed": 2
  },
  "last_updated": "2026-03-10T14:10:06"
}
```

### 手动清除检查点

```bash
# 清除所有检查点
python scripts/run_pipeline.py --clear

# 或者手动删除
rm -rf .checkpoints/
```

---

## 配置文件

### 默认配置

使用 `config/default.yaml` 作为默认配置。

### 自定义配置

创建自定义配置文件：

```yaml
# my_config.yaml
paths:
  input_data: my_data/conversations/

vertex_ai:
  extraction:
    model: gemini-2.5-flash
    max_tokens: 8192  # 使用更小的token限制

pipeline:
  embedding:
    batch_size: 16  # 减小batch size
```

使用自定义配置：

```bash
python scripts/run_pipeline.py --all --config my_config.yaml
```

---

## 环境变量要求

运行脚本前需要设置以下环境变量（在 `.env` 文件中）：

```bash
# Google Cloud 配置
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}
```

---

## 常见问题

### Q: 运行报错 "No module named 'pipeline'"

A: 确保在项目根目录运行脚本：
```bash
cd /path/to/wechat_memory
python scripts/run_pipeline.py --all
```

### Q: 如何查看详细日志？

A: 日志自动输出到控制台，也可以重定向到文件：
```bash
python scripts/run_pipeline.py --all 2>&1 | tee pipeline.log
```

### Q: Pipeline 运行很慢怎么办？

A:
1. 检查网络连接（Vertex AI 需要访问 Google Cloud）
2. 减小 batch_size（在配置文件中调整）
3. 使用更少的数据进行测试

### Q: 如何并行处理多个对话？

A: Pipeline 内部已经实现了批处理，不需要手动并行。如需调整并行度，修改配置：
```yaml
pipeline:
  embedding:
    batch_size: 32  # 调整批处理大小
```

---

## 性能提示

### 优化建议

1. **网络优化**:
   - 使用稳定的网络连接
   - 如在 Google Cloud VM 上运行，延迟更低

2. **数据优化**:
   - 先用小批量数据测试（10-20个对话）
   - 确认流程正常后再处理全量数据

3. **配置优化**:
   ```yaml
   pipeline:
     embedding:
       batch_size: 32  # 根据API配额调整
     knowledge_extraction:
       batch_size: 10  # Gemini 并发数
   ```

---

## 故障排查

### 常见错误

1. **Google Cloud 认证失败**
   ```
   Error: GOOGLE_APPLICATION_CREDENTIALS_JSON not found
   ```
   解决: 检查 `.env` 文件，确保包含正确的服务账号 JSON

2. **模型访问权限错误**
   ```
   404 Model not found
   ```
   解决: 确认 Google Cloud 项目已启用 Vertex AI API

3. **文件不存在错误**
   ```
   FileNotFoundError: data/conversations/chat_data_filtered/
   ```
   解决: 创建目录并放入对话数据文件

4. **内存不足**
   ```
   MemoryError
   ```
   解决: 减小 batch_size 或分批处理数据

---

## 开发指南

### 添加新脚本

1. 在 `scripts/` 目录创建新脚本
2. 添加 shebang 和编码声明:
   ```python
   #!/usr/bin/env python3
   # -*- coding: utf-8 -*-
   ```
3. 添加文档字符串说明用途
4. 更新本 README

### 脚本规范

- ✅ 使用 argparse 处理命令行参数
- ✅ 添加 `--help` 说明
- ✅ 使用 logging 输出日志
- ✅ 处理异常并返回合适的退出码
- ✅ 提供使用示例

---

## 相关文档

- [Pipeline 模块](../pipeline/README.md) - 详细的 Pipeline 说明
- [配置系统](../config/README.md) - 配置文件说明
- [快速开始](../docs/quickstart.md) - 完整的快速开始指南
