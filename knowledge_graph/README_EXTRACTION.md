# 知识图谱提取系统使用指南

## 📋 系统概述

本系统从 183K 微信对话记录中提取知识图谱，包括：
- **实体**: People, Organizations, Topics, Events, Locations
- **关系**: WORKS_AT, PARTICIPATED_IN, VISITED, KNOWS 等
- **时间**: 对话时间 + 事件时间推断
- **上下文**: 保存原始对话信息用于追溯

---

## 🚀 快速开始

### 1. 全量提取（首次运行）

```bash
python knowledge_graph/full_extraction.py
```

**预期**：
- 耗时：~7.6 小时（20 并行）
- 成本：~$38
- 输出：183K 个 JSON 文件（每条对话一个）
- 位置：`knowledge_graph/extractions/session_*.json`

**特性**：
- ✅ 自动重试失败的提取（最多 2 次）
- ✅ 断点续传（已提取的会自动跳过）
- ✅ 实时进度显示（每 100 条打印一次）
- ✅ 并行处理（20 workers）

---

### 2. 监控进度

```bash
python knowledge_graph/monitor_extraction.py
```

**输出**：
- 📊 成功/失败统计
- 💰 总成本和耗时
- 🎯 实体数量统计
- ❌ 错误类型分析
- 🔍 随机查看 5 个样本

**示例输出**：
```
📈 总体统计:
  - 成功: 182,500 (99.7%)
  - 失败: 500 (0.3%)
  - 总成本: $37.82
  - 总耗时: 7.54 小时
  - 平均成本: $0.000207 /条

🎯 实体统计:
  - people         : 总计 360,250 个, 平均 2.0 个/对话
  - organizations  : 总计 91,250 个, 平均 0.5 个/对话
  - topics         : 总计 638,750 个, 平均 3.5 个/对话
  - events         : 总计 365,000 个, 平均 2.0 个/对话
  - locations      : 总计 383,750 个, 平均 2.1 个/对话
  - relationships  : 总计 547,500 个, 平均 3.0 个/对话
```

---

## 📊 提取结果结构

### 单个 JSON 文件示例

```json
{
  "extraction_id": "uuid-1234-5678",
  "created_at": "2026-02-26T10:30:00Z",

  "conversation": {
    "session_id": "c6ed845e88d1dc1041f366c2eb3b1caf",
    "conversation_name": "Nick Luo",
    "conversation_type": "private",
    "start_timestamp": 1572542495,
    "end_timestamp": 1572542730,
    "year": 2019,
    "month": 11,
    "participants": ["Nick Luo", "米雪川（我）"],
    "message_count": 20,
    "content_sample": "对话内容前 500 字符..."
  },

  "entities": {
    "people": [
      {
        "name": "Nick Luo",
        "relationship_to_user": "潜在雇主/合作者",
        "occupation": "AI创业者",
        "company": "Ainia",
        "expertise": ["AI创业", "教育科技", "AI产品开发"],
        "personality": [],
        "confidence": 0.95,
        "context": "Nick Luo 联系我讨论 Ainia 的职位..."
      }
    ],

    "organizations": [
      {
        "name": "Ainia",
        "type": "公司",
        "industry": "教育科技",
        "confidence": 0.9,
        "context": "Nick Luo 创办的 AI 教育公司"
      }
    ],

    "topics": [
      {
        "name": "Ainia项目与招聘",
        "type": "工作项目",
        "keywords": ["Ainia", "招聘", "AI产品"],
        "confidence": 0.9,
        "context": "讨论 Ainia 的产品和职位机会"
      }
    ],

    "events": [
      {
        "name": "腾讯会议面试",
        "type": "会议",
        "participants": ["Nick Luo", "米雪川"],
        "location": null,
        "description": "通过腾讯会议进行面试",
        "time_reference": "present",
        "time_description": "正在进行",
        "confidence": 0.9,
        "context": "对话中提到正在腾讯会议中面试"
      }
    ],

    "locations": [
      {
        "name": "越南",
        "type": "城市",
        "parent_location": null,
        "notes": "米雪川旅游地",
        "confidence": 0.8,
        "context": "对话中提到去越南旅游"
      }
    ],

    "relationships": [
      {
        "type": "WORKS_AT",
        "source": "Nick Luo",
        "source_type": "Person",
        "target": "Ainia",
        "target_type": "Organization",
        "properties": {},
        "confidence": 0.9,
        "context": "Nick Luo 是 Ainia 创始人"
      },
      {
        "type": "PARTICIPATED_IN",
        "source": "Nick Luo",
        "source_type": "Person",
        "target": "腾讯会议面试",
        "target_type": "Event",
        "properties": {},
        "confidence": 0.95,
        "context": "Nick Luo 参加了面试"
      }
    ]
  },

  "extraction_metadata": {
    "model": "gemini-2.5-flash",
    "input_tokens": 306,
    "output_tokens": 450,
    "thoughts_tokens": 620,
    "duration_seconds": 5.9,
    "cost": 0.000158
  },

  "success": true,
  "error": null
}
```

---

## 🔧 高级功能

### 重新处理失败的提取

```python
# 1. 找出失败的会话
python knowledge_graph/monitor_extraction.py  # 查看失败列表

# 2. 删除失败的 JSON 文件
# Windows PowerShell:
cd knowledge_graph/extractions
Get-ChildItem session_*.json | ForEach-Object {
    $content = Get-Content $_.FullName | ConvertFrom-Json
    if (-not $content.success) {
        Remove-Item $_.FullName
        Write-Host "Deleted: $($_.Name)"
    }
}

# 3. 重新运行提取（会自动跳过成功的）
python knowledge_graph/full_extraction.py
```

### 提取特定范围的对话

修改 `full_extraction.py`：

```python
# 在 main() 函数中，筛选特定时间范围
all_sessions = load_all_conversations(VECTOR_STORE_PATH)

# 只处理 2019 年的对话
all_sessions = [s for s in all_sessions if s.get('year') == 2019]

# 只处理前 1000 条
all_sessions = all_sessions[:1000]
```

### 调整并行度

根据你的机器性能和网络情况调整：

```python
# 在 full_extraction.py 顶部修改
PARALLEL_WORKERS = 10  # 降低并行度（更稳定）
PARALLEL_WORKERS = 30  # 提高并行度（更快，但可能不稳定）
```

---

## 📈 性能优化建议

### 1. 如果速度慢

- 提高并行度：`PARALLEL_WORKERS = 30`
- 检查网络：Vertex AI 调用可能受网络影响
- 使用更快的磁盘：SSD 优于 HDD

### 2. 如果失败率高（>5%）

- 降低并行度：`PARALLEL_WORKERS = 10`
- 增加重试次数：`MAX_RETRIES = 3`
- 检查是否触发了 API 限流

### 3. 如果成本过高

- 检查是否有重复提取：删除 `extractions/` 目录中的文件会导致重新提取
- 确认模型：应该使用 `gemini-2.5-flash`（最便宜）

---

## 🛠️ 故障排查

### 问题1：提取卡住不动

**可能原因**：网络问题或 API 限流

**解决方案**：
```bash
# Ctrl+C 停止程序
# 重新运行（会从断点继续）
python knowledge_graph/full_extraction.py
```

### 问题2：大量 JSON 解析错误

**可能原因**：模型输出格式不规范

**解决方案**：
1. 查看失败样本：`python monitor_extraction.py`
2. 优化 prompt（在 `full_extraction.py` 中修改 `EXTRACTION_PROMPT`）
3. 增加重试次数

### 问题3：内存不足

**可能原因**：并行度过高

**解决方案**：
```python
PARALLEL_WORKERS = 5  # 降低到 5
```

---

## 📅 下一步：构建图数据库

完成提取后，进入阶段 2：

```bash
# 1. 实体消歧（合并重复实体）
python knowledge_graph/entity_disambiguation.py

# 2. 构建 Neo4j 图数据库
python knowledge_graph/build_neo4j.py

# 3. 启动 Neo4j 并查询
neo4j start
```

查询示例：
```cypher
// 查询所有人物
MATCH (p:Person) RETURN p LIMIT 100

// 查询我在哪些公司工作过
MATCH (p:Person {name: "米雪川"})-[:WORKS_AT]->(o:Organization)
RETURN o.name, o.industry

// 查询我去过的地方
MATCH (p:Person {name: "米雪川"})-[:VISITED]->(l:Location)
RETURN l.name, l.type

// 查询我参加过的面试
MATCH (p:Person {name: "米雪川"})-[:PARTICIPATED_IN]->(e:Event {type: "面试"})
RETURN e.name, e.description, e.time_description
```

---

## 📊 预期结果

基于 8 个样本的测试推算：

| 指标 | 预估值 |
|------|--------|
| **总对话数** | 183,000 |
| **成功率** | 98%+ |
| **总成本** | $38-40 |
| **总耗时** | 7-8 小时 |
| **人物数（原始）** | ~360K |
| **人物数（去重后）** | ~5K |
| **公司数** | ~2K |
| **主题数** | ~10K |
| **事件数** | ~100K |
| **地点数** | ~3K |
| **关系数** | ~500K |

---

## ✅ 检查清单

开始前确认：

- [ ] 已安装依赖：`pip install google-cloud-aiplatform python-dotenv`
- [ ] `.env` 文件配置正确（Vertex AI 凭证）
- [ ] `vector_stores/conversations_complete.pkl` 文件存在
- [ ] 磁盘空间充足（至少 10GB 用于 183K JSON 文件）
- [ ] 网络稳定（需要持续调用 Vertex AI API）

开始提取：

```bash
python knowledge_graph/full_extraction.py
```

🎉 祝提取顺利！
