## Pipeline 模块

WeMemory 端到端数据处理框架。

---

## 概述

Pipeline 模块提供统一的数据处理流程，包括：

1. **数据清洗** (data_cleaning) - 过滤和清洗对话数据
2. **Embedding 生成** (embedding) - 生成对话向量
3. **知识抽取** (knowledge_extraction) - 抽取实体、事件、关系
4. **图谱构建** (graph_building) - 构建知识图谱

---

## 核心特性

### 统一接口

所有 Pipeline 继承自 `BasePipeline` 或 `BatchPipeline`，提供：

- ✅ **统一的日志记录**：自动日志到文件和控制台
- ✅ **进度保存（Checkpoint）**：自动保存进度，支持断点续传
- ✅ **错误处理和重试**：自动重试失败的批次
- ✅ **进度显示**：使用 tqdm 显示实时进度
- ✅ **统计信息**：自动收集执行统计

### 断点续传

Pipeline 自动保存检查点，中断后可以继续：

```python
# 首次运行
pipeline.run()  # 处理了 50/100 项后中断

# 恢复运行
pipeline.run(resume=True)  # 从第 51 项继续
```

### 批量处理

支持批量 API 调用，提高效率：

```python
class MyBatchPipeline(BatchPipeline):
    def process_batch(self, batch):
        # 一次调用处理多个项目
        return api.batch_process(batch)
```

---

## 使用方法

### 1. 使用主控脚本（推荐）

```bash
# 执行数据清洗
python scripts/run_pipeline.py --step data_cleaning

# 执行全流程
python scripts/run_pipeline.py --all

# 从头开始（清除检查点）
python scripts/run_pipeline.py --step data_cleaning --fresh

# 查看当前进度
python scripts/run_pipeline.py --status

# 清除所有检查点
python scripts/run_pipeline.py --clear
```

### 2. 在代码中使用

```python
from pipeline.data_cleaning import DataCleaningPipeline
from config.loader import load_config

# 加载配置
config = load_config()

# 创建 Pipeline
pipeline = DataCleaningPipeline(
    config,
    input_dir='data/conversations/raw',
    output_dir='data/conversations/cleaned'
)

# 运行 Pipeline
stats = pipeline.run(resume=True)

# 查看统计
print(f"处理成功: {stats['processed_items']}/{stats['total_items']}")
print(f"处理失败: {stats['failed_items']}")
```

---

## 已实现的 Pipeline

### 1. Data Cleaning Pipeline

**功能**：清洗对话数据

**输入**：原始对话 JSON 文件
**输出**：清洗后的对话 JSON 文件

**配置**：
```yaml
# config/default.yaml
pipeline:
  data_cleaning:
    min_messages: 3
    max_time_gap_minutes: 30
    quality_threshold: 0.5
```

**使用**：
```bash
python scripts/run_pipeline.py --step data_cleaning
```

---

## 待实现的 Pipeline

### 2. Embedding Pipeline

**功能**：生成对话向量

**输入**：清洗后的对话 JSON 文件
**输出**：向量库文件 (embeddings.pkl, index.faiss)

**配置**：
```yaml
pipeline:
  embedding:
    batch_size: 32
    checkpoint_interval: 100
    content_weight: 0.85
    context_weight: 0.15
```

### 3. Knowledge Extraction Pipeline

**功能**：抽取知识（实体、事件、关系）

**输入**：对话 JSON 文件
**输出**：知识抽取结果 JSON

**配置**：
```yaml
pipeline:
  knowledge_extraction:
    batch_size: 10
    confidence_threshold: 0.8
    entity_types:
      - 人物
      - 地点
      - 组织
```

### 4. Graph Building Pipeline

**功能**：构建知识图谱

**输入**：知识抽取结果
**输出**：知识图谱文件 (curated_kg.json, triplets.json)

**配置**：
```yaml
pipeline:
  graph_building:
    prune_relations: true
    generate_triplet_embeddings: true
```

---

## Pipeline 架构

### BasePipeline

基础 Pipeline 类，适用于逐项处理：

```python
from pipeline.base import BasePipeline

class MyPipeline(BasePipeline):
    def get_items(self):
        """返回要处理的项目列表"""
        return [item1, item2, item3]

    def process_item(self, item):
        """处理单个项目"""
        # 处理逻辑
        return result
```

### BatchPipeline

批量 Pipeline 类，适用于批量 API 调用：

```python
from pipeline.base import BatchPipeline

class MyBatchPipeline(BatchPipeline):
    def get_items(self):
        """返回要处理的项目列表"""
        return [item1, item2, item3]

    def process_batch(self, batch):
        """处理一批项目"""
        # 批量处理逻辑
        return [result1, result2, ...]
```

### 检查点管理

Pipeline 自动管理检查点：

```python
# 检查点保存位置
.checkpoints/
├── data_cleaning_checkpoint.json
├── embedding_checkpoint.json
└── ...

# 检查点格式
{
  "pipeline_name": "data_cleaning",
  "timestamp": "2024-01-01T10:00:00",
  "state": {
    "processed_indices": [0, 1, 2, ...],
    "stats": {...}
  }
}
```

---

## 配置

### Pipeline 配置

```yaml
# config/default.yaml
pipeline:
  # 数据清洗
  data_cleaning:
    min_messages: 3
    max_time_gap_minutes: 30
    quality_threshold: 0.5
    remove_duplicates: true

  # Embedding 生成
  embedding:
    batch_size: 32
    checkpoint_interval: 100

  # 知识抽取
  knowledge_extraction:
    batch_size: 10
    confidence_threshold: 0.8

  # 图谱构建
  graph_building:
    prune_relations: true
```

### 路径配置

```yaml
paths:
  input_data: data/conversations/chat_data_filtered/
  vector_stores: vector_stores/
  knowledge_graph: data/knowledge_graph/
  checkpoints: .checkpoints/
  logs: logs/
```

---

## 日志

Pipeline 自动记录日志：

```
logs/
├── pipeline_data_cleaning.log
├── pipeline_embedding.log
├── pipeline_knowledge_extraction.log
└── pipeline_graph_building.log
```

日志格式：
```
[2024-01-01 10:00:00] INFO [pipeline.data_cleaning] 开始执行 Pipeline: data_cleaning
[2024-01-01 10:00:01] INFO [pipeline.data_cleaning] 总项目数: 138
[2024-01-01 10:00:05] DEBUG [pipeline.data_cleaning] 已清洗: 张三.json
[2024-01-01 10:05:00] INFO [pipeline.data_cleaning] Pipeline 完成
```

---

## 错误处理

### 自动重试

批量 Pipeline 支持自动重试：

```python
pipeline = MyBatchPipeline(
    config,
    batch_size=10,
    max_retries=3,      # 最多重试 3 次
    retry_delay=2.0     # 重试前等待 2 秒
)
```

### 错误日志

失败的项目会被记录：

```
[2024-01-01 10:00:10] ERROR [pipeline.data_cleaning] 处理项目 42 失败: JSONDecodeError
```

### 继续执行

即使部分项目失败，Pipeline 仍会继续执行其他项目。

---

## 性能优化

### 1. 批量大小

调整批量大小以平衡速度和内存：

```yaml
embedding:
  batch_size: 32  # 较大：更快，但需要更多内存
                  # 较小：较慢，但节省内存
```

### 2. 检查点间隔

控制检查点保存频率：

```python
pipeline.run(
    checkpoint_interval=10  # 每处理 10 项保存一次
)
```

### 3. 并行处理

未来可以支持多进程并行：

```python
# TODO: 实现并行处理
pipeline.run(workers=4)
```

---

## 最佳实践

### 1. 分步执行

对于大数据集，建议分步执行：

```bash
# 步骤 1: 数据清洗
python scripts/run_pipeline.py --step data_cleaning

# 步骤 2: 生成向量
python scripts/run_pipeline.py --step embedding

# 步骤 3: 知识抽取
python scripts/run_pipeline.py --step knowledge_extraction

# 步骤 4: 构建图谱
python scripts/run_pipeline.py --step graph_building
```

### 2. 定期保存检查点

使用较小的检查点间隔：

```python
pipeline.run(checkpoint_interval=5)  # 每 5 项保存
```

### 3. 监控日志

实时查看日志：

```bash
tail -f logs/pipeline_data_cleaning.log
```

### 4. 验证结果

每个步骤完成后验证输出：

```bash
# 清洗后评估质量
python scripts/evaluate_data_quality.py data/conversations/cleaned/

# 向量生成后验证
python scripts/test_search.py
```

---

## 开发新 Pipeline

### 创建新 Pipeline

```python
from pipeline.base import BasePipeline

class MyNewPipeline(BasePipeline):
    """新 Pipeline 说明"""

    def __init__(self, config, **kwargs):
        super().__init__("my_pipeline", config, **kwargs)

        # 初始化逻辑
        self.my_config = config.get('my_pipeline', {})

    def get_items(self):
        """获取要处理的项目"""
        return [...]  # 返回项目列表

    def process_item(self, item):
        """处理单个项目"""
        # 处理逻辑
        result = do_something(item)
        return result
```

### 注册到主控脚本

在 `scripts/run_pipeline.py` 中添加：

```python
def _run_my_pipeline(self, resume=True, **kwargs):
    """执行新 Pipeline"""
    from pipeline.my_new_pipeline import MyNewPipeline

    pipeline = MyNewPipeline(
        self.config,
        checkpoint_dir=self.checkpoint_dir,
        **kwargs
    )

    stats = pipeline.run(resume=resume)
    return stats
```

---

## 常见问题

### Q: 如何从失败的检查点恢复？

```bash
# 直接运行会自动从检查点恢复
python scripts/run_pipeline.py --step data_cleaning
```

### Q: 如何重新开始（忽略检查点）？

```bash
python scripts/run_pipeline.py --step data_cleaning --fresh
```

### Q: 检查点在哪里？

```
.checkpoints/
├── data_cleaning_checkpoint.json
└── ...
```

### Q: 如何调整日志级别？

```yaml
# config/default.yaml
logging:
  level: DEBUG  # DEBUG, INFO, WARNING, ERROR
```

---

## 参考文档

- [配置系统](../config/README.md)
- [数据清洗](../docs/data-cleaning.md)
- [Embedding](../docs/embedding.md)
- [知识图谱](../docs/knowledge-graph.md)

---

返回 [主文档](../README.md)
