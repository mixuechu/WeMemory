# 数据清洗指南

本文档说明如何对导出的微信聊天记录进行清洗和筛选，以提高向量搜索和知识抽取的质量。

---

## 为什么需要数据清洗？

原始的微信聊天记录包含大量噪音和无用信息：

### 常见噪音类型

1. **系统消息**
   - "你已添加了xxx，现在可以开始聊天了。"
   - "xxx撤回了一条消息"
   - "xxx拍了拍你"
   - "xxx邀请你加入了群聊"

2. **超短对话**
   - 只有1-2条消息的对话片段
   - 缺乏上下文，无法提取有价值信息

3. **重复对话**
   - 因导出工具问题产生的重复记录
   - 转发消息的重复

4. **时间跨度过短**
   - 在很短时间内（<1分钟）的大量消息
   - 通常是测试消息或误发

5. **低质量内容**
   - 纯表情符号
   - "[图片]"、"[语音]" 等媒体占位符（无文字内容）
   - 无意义的单字回复（"哦"、"嗯"、"啊"）

### 清洗的好处

- ✅ **提高搜索质量**：减少噪音，提升相关性
- ✅ **节省资源**：减少向量生成和存储成本
- ✅ **改善知识抽取**：专注于有价值的对话
- ✅ **加快处理速度**：数据量减少30-50%

---

## 清洗策略

### 1. 过滤系统消息

**目标**：移除所有 `type: 80` 的系统消息。

**原因**：
- 系统消息不包含用户信息
- 对记忆检索无价值
- 会干扰知识抽取

**实现**：
```python
# 过滤前
messages = [
    {"type": 0, "content": "你好"},
    {"type": 80, "content": "你已添加了xxx"},  # 系统消息
    {"type": 0, "content": "最近怎么样"}
]

# 过滤后
messages = [
    {"type": 0, "content": "你好"},
    {"type": 0, "content": "最近怎么样"}
]
```

### 2. 消息数量阈值

**目标**：过滤消息数量少于 N 条的对话（默认 N=3）。

**原因**：
- 过少的消息缺乏上下文
- 无法形成有意义的对话片段
- 知识抽取准确率低

**配置**：
```yaml
# config/default.yaml
pipeline:
  data_cleaning:
    min_messages: 3  # 最少3条消息
```

**示例**：
```python
# 过滤前：2条消息，会被移除
{
  "name": "张三",
  "messages": [
    {"content": "在吗"},
    {"content": "好的"}
  ]
}

# 保留：5条消息，保留
{
  "name": "李四",
  "messages": [
    {"content": "明天有空吗"},
    {"content": "有的"},
    {"content": "一起吃饭"},
    {"content": "好啊"},
    {"content": "几点？"}
  ]
}
```

### 3. 去重

**目标**：移除完全重复的消息。

**去重维度**：
- 发送者 + 时间戳 + 内容完全相同
- 时间戳相差 < 1秒，内容相同

**原因**：
- 导出工具可能产生重复记录
- 转发消息可能被记录多次

**实现**：
```python
def remove_duplicates(messages):
    """移除重复消息"""
    seen = set()
    unique_messages = []

    for msg in messages:
        key = (msg['sender'], msg['timestamp'], msg['content'])
        if key not in seen:
            seen.add(key)
            unique_messages.append(msg)

    return unique_messages
```

### 4. 对话分割

**目标**：按时间间隔分割长对话为多个会话。

**策略**：
- 如果两条消息间隔 > N 分钟（默认30分钟），则分割为新会话
- 每个会话独立处理

**原因**：
- 长时间跨度的对话通常是不同话题
- 分割后的会话更聚焦
- 提高向量搜索的语义一致性

**配置**：
```yaml
pipeline:
  data_cleaning:
    max_time_gap_minutes: 30  # 30分钟间隔分割
```

**示例**：
```python
# 原始对话
messages = [
    {"timestamp": 1000, "content": "早上好"},       # 会话1开始
    {"timestamp": 1100, "content": "今天天气不错"},
    {"timestamp": 3000, "content": "下午有空吗"},   # 会话2开始（间隔>30分钟）
    {"timestamp": 3100, "content": "可以"}
]

# 分割后
session_1 = [
    {"timestamp": 1000, "content": "早上好"},
    {"timestamp": 1100, "content": "今天天气不错"}
]

session_2 = [
    {"timestamp": 3000, "content": "下午有空吗"},
    {"timestamp": 3100, "content": "可以"}
]
```

### 5. 质量评估

**目标**：为每个对话计算质量分数，过滤低质量对话。

**评分维度**：

| 维度 | 权重 | 说明 |
|------|------|------|
| 平均消息长度 | 30% | 字符数越多越好，过滤单字回复 |
| 消息多样性 | 25% | 不同发送者的参与度 |
| 时间跨度 | 20% | 对话持续时间（排除过短） |
| 实质内容比例 | 25% | 文本消息占比（vs 图片/语音） |

**计算公式**：
```python
quality_score = (
    0.30 * avg_message_length_score +
    0.25 * sender_diversity_score +
    0.20 * time_span_score +
    0.25 * content_ratio_score
)
```

**阈值**：
- 质量分 < 0.5：移除
- 质量分 ≥ 0.5：保留

**示例**：
```python
# 低质量对话（质量分 0.3）
{
  "messages": [
    {"sender": "A", "content": "哦"},        # 太短
    {"sender": "B", "content": "[图片]"},    # 无实质内容
    {"sender": "A", "content": "嗯"}         # 太短
  ]
}
# 结果：移除

# 高质量对话（质量分 0.8）
{
  "messages": [
    {"sender": "A", "content": "周末去爬山怎么样"},
    {"sender": "B", "content": "好主意，我们去哪座山"},
    {"sender": "A", "content": "香山吧，景色不错"},
    {"sender": "C", "content": "我也想去，几点出发"}
  ]
}
# 结果：保留
```

---

## 使用方法

### 方法 1：使用清洗脚本

```bash
# 清洗单个对话文件
python scripts/clean_conversation.py \
  data/conversations/chat_data_filtered/张三/张三.json \
  --output data/conversations/cleaned/张三/张三.json

# 批量清洗整个目录
python scripts/clean_conversation.py \
  data/conversations/chat_data_filtered/ \
  --output data/conversations/cleaned/ \
  --min-messages 3 \
  --max-time-gap 30
```

### 方法 2：在 Python 中使用

```python
from data_loader.cleaner import ConversationCleaner

# 创建清洗器
cleaner = ConversationCleaner(
    min_messages=3,
    max_time_gap_minutes=30,
    quality_threshold=0.5
)

# 加载对话
with open('张三.json', 'r') as f:
    conversation = json.load(f)

# 清洗
cleaned = cleaner.clean(conversation)

# 查看清洗统计
print(cleaner.get_stats())
# {
#   'original_messages': 150,
#   'filtered_messages': 120,
#   'removed_system_messages': 25,
#   'removed_duplicates': 5,
#   'sessions_created': 3,
#   'quality_score': 0.78
# }

# 保存清洗后的数据
with open('张三_cleaned.json', 'w') as f:
    json.dump(cleaned, f, ensure_ascii=False, indent=2)
```

### 方法 3：使用配置文件

```yaml
# config/user.yaml
pipeline:
  data_cleaning:
    min_messages: 5          # 更严格：至少5条消息
    max_time_gap_minutes: 20  # 更短间隔分割
    quality_threshold: 0.6    # 更高质量要求

    filter_message_types:
      - 80   # 系统消息
      - 99   # 转账消息（可选）

    remove_duplicates: true
```

```python
from config.loader import load_config
from data_loader.cleaner import ConversationCleaner

# 从配置加载
config = load_config()
cleaner = ConversationCleaner.from_config(config.pipeline.data_cleaning)

# 清洗
cleaned = cleaner.clean(conversation)
```

---

## 评估清洗效果

使用质量评估工具查看清洗前后的对比：

```bash
# 评估清洗前的数据
python scripts/evaluate_data_quality.py \
  data/conversations/chat_data_filtered/ \
  --output reports/quality_before.json

# 清洗数据
python scripts/clean_conversation.py \
  data/conversations/chat_data_filtered/ \
  --output data/conversations/cleaned/

# 评估清洗后的数据
python scripts/evaluate_data_quality.py \
  data/conversations/cleaned/ \
  --output reports/quality_after.json

# 生成对比报告
python scripts/compare_quality_reports.py \
  reports/quality_before.json \
  reports/quality_after.json
```

**示例输出**：
```
=============================================================
数据质量评估报告
=============================================================

总体统计:
  对话数量: 138 → 95 (-31.2%)
  消息总数: 45,892 → 35,124 (-23.5%)
  平均质量分: 0.58 → 0.82 (+41.4%)

清洗统计:
  ✅ 移除系统消息: 4,521 条
  ✅ 移除重复消息: 892 条
  ✅ 过滤低质量对话: 43 个
  ✅ 分割会话: 138 → 247 个

质量分布:
  优秀 (≥0.8): 12% → 68%
  良好 (0.6-0.8): 35% → 28%
  一般 (0.4-0.6): 41% → 4%
  较差 (<0.4): 12% → 0%

推荐:
  ✅ 数据质量显著提升
  ✅ 可以继续生成向量库
```

---

## 清洗建议

### 保守策略（推荐新手）

适用于首次使用，保留更多数据：

```yaml
pipeline:
  data_cleaning:
    min_messages: 3           # 较宽松
    max_time_gap_minutes: 60  # 较长间隔
    quality_threshold: 0.4    # 较低阈值
```

### 标准策略（推荐）

平衡质量和数据量：

```yaml
pipeline:
  data_cleaning:
    min_messages: 3
    max_time_gap_minutes: 30
    quality_threshold: 0.5
```

### 严格策略

追求高质量，适用于数据量充足的情况：

```yaml
pipeline:
  data_cleaning:
    min_messages: 5
    max_time_gap_minutes: 20
    quality_threshold: 0.7
```

---

## 常见问题

### Q1: 清洗后数据量减少太多（>50%）

**原因**：
- 阈值设置过严格
- 原始数据质量确实较差

**解决方案**：
1. 降低质量阈值：`quality_threshold: 0.3`
2. 减少最小消息数：`min_messages: 2`
3. 检查是否过滤了有价值的对话类型

### Q2: 如何保留特定对话不被清洗？

**方法**：
```python
cleaner = ConversationCleaner(
    min_messages=3,
    whitelist_names=['重要客户', '家庭群']  # 白名单
)
```

### Q3: 清洗后仍有很多无用消息

**解决方案**：
1. 提高质量阈值：`quality_threshold: 0.7`
2. 增加最小消息数：`min_messages: 5`
3. 手动检查并调整评分权重

### Q4: 对话被错误分割

**原因**：时间间隔设置过短

**解决方案**：
```yaml
max_time_gap_minutes: 60  # 增加到60分钟
```

### Q5: 如何保留图片/语音对话？

**方法**：
```python
# 不过滤媒体消息
cleaner = ConversationCleaner(
    filter_empty_media=False  # 保留 [图片]、[语音] 等
)
```

---

## 最佳实践

### 1. 分阶段清洗

```bash
# 第一阶段：只过滤系统消息
python scripts/clean_conversation.py input/ --output stage1/ \
  --filter-system-only

# 第二阶段：去重和分割
python scripts/clean_conversation.py stage1/ --output stage2/ \
  --remove-duplicates --split-sessions

# 第三阶段：质量过滤
python scripts/clean_conversation.py stage2/ --output final/ \
  --quality-filter --threshold 0.5
```

### 2. 保留原始数据

```bash
# 不要覆盖原始数据，使用不同的输出目录
python scripts/clean_conversation.py \
  data/conversations/raw/ \
  --output data/conversations/cleaned/
```

### 3. 评估后再继续

```bash
# 先评估
python scripts/evaluate_data_quality.py cleaned/ --report

# 确认质量后再生成向量库
python scripts/generate_embeddings.py cleaned/
```

### 4. 针对不同对话类型使用不同策略

```python
# 私聊：较严格
private_cleaner = ConversationCleaner(
    min_messages=5,
    quality_threshold=0.6
)

# 群聊：较宽松（信息密度低但有价值）
group_cleaner = ConversationCleaner(
    min_messages=3,
    quality_threshold=0.4
)
```

---

## 清洗效果示例

### 清洗前
```json
{
  "name": "张三",
  "messages": [
    {"type": 80, "content": "你已添加了张三"},
    {"type": 0, "content": "你好"},
    {"type": 0, "content": "你好"},  // 重复
    {"type": 0, "content": "在吗"},
    {"type": 0, "content": "嗯"},
    {"type": 80, "content": "张三撤回了一条消息"},
    {"type": 0, "content": "[图片]"}
  ]
}
```

### 清洗后
```json
{
  "name": "张三",
  "sessions": [
    {
      "session_id": 1,
      "quality_score": 0.65,
      "messages": [
        {"type": 0, "content": "你好"},
        {"type": 0, "content": "在吗"}
      ]
    }
  ],
  "stats": {
    "original_messages": 7,
    "cleaned_messages": 2,
    "removed_system": 2,
    "removed_duplicates": 1,
    "removed_low_quality": 2
  }
}
```

---

## 下一步

数据清洗完成后：

1. 📊 **评估清洗效果**
   ```bash
   python scripts/evaluate_data_quality.py data/conversations/cleaned/
   ```

2. 🧠 **生成向量库**
   - 使用清洗后的数据
   - 详见：[Embedding 指南](embedding.md)

3. 🕸️ **知识抽取**
   - 高质量数据提高抽取准确率
   - 详见：[知识图谱指南](knowledge-graph.md)

---

## 参考资料

- [数据导出指南](data-export.md)
- [ChatLab 格式说明](../examples/data_samples/README.md)
- [配置系统](../config/README.md)

---

返回 [主文档](../README.md)
