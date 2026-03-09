# WeChat Knowledge Graph 微信聊天记录知识图谱

从微信聊天记录中提取结构化知识图谱，存储在Neo4j图数据库中。

## 核心脚本

### 🚀 `full_extraction.py` - 主提取脚本
从Excel聊天记录中提取知识图谱实体和关系，并构建Neo4j图数据库。

**功能：**
- 提取 Person、Event、Topic、Location 实体
- 建立实体间关系（KNOWS, PARTICIPATED_IN, DISCUSSED, LOCATED_AT等）
- 使用 Gemini 2.5 Flash 进行批量提取
- 自动过滤泛指/无意义实体（如"某人"、"他"等）
- 为Event自动识别参与者并创建关系

**使用方法：**
```bash
python full_extraction.py --limit 10  # 测试模式，只处理10条消息
python full_extraction.py              # 完整提取
```

**配置：**
- Neo4j连接：修改脚本中的 `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- Gemini API：需要配置环境变量（见 `../.env`）

---

### 🧹 `auto_graph_cleaner.py` - 自动图清理器
使用LLM智能判断并清理知识图谱中的低质量实体。

**功能：**
- 批量识别泛指/无意义Person实体（如"某女性朋友"、"对话中的对方"）
- 自动删除孤立节点
- 清理低价值实体
- 支持dry-run模式预览

**使用方法：**
```bash
python auto_graph_cleaner.py --dry-run  # 预览模式
python auto_graph_cleaner.py            # 执行清理
```

---

### 🔧 `graph_manager.py` - 图管理工具
提供图谱实体管理的核心功能。

**功能：**
- 合并重复Person实体
- 删除实体
- 查找重复/孤立/低价值实体
- 设置实体别名

**注意：** 此脚本主要作为工具库使用，可被其他脚本导入。

---

### 🏗️ `build_neo4j_graph.py` - 图数据库构建
构建Neo4j图数据库的基础脚本（可能已被full_extraction.py替代，待确认是否保留）。

---

## 数据模型

### 节点类型 (Nodes)
- **Person**: 人物实体
  - `name`: 正式名称
  - `aliases`: 别名列表
  - `conversation_name`: 所属对话

- **Event**: 事件实体
  - `name`: 事件名称
  - `description`: 事件描述
  - `type`: 事件类型
  - `time_reference`: 相对时间 (past/present/future)
  - `inferred_time`: 推断的具体日期 (YYYY-MM-DD)
  - `conversation_name`: 所属对话

- **Topic**: 话题实体
- **Location**: 地点实体

### 关系类型 (Relationships)
- `KNOWS`: Person认识Person
- `PARTICIPATED_IN`: Person参与Event
- `DISCUSSED`: Person讨论Topic
- `LOCATED_AT`: Entity位于Location
- 等等...

---

## 项目结构

```
knowledge_graph/
├── README.md                    # 项目说明（本文件）
├── full_extraction.py           # 核心提取脚本
├── auto_graph_cleaner.py        # 自动清理器
├── graph_manager.py             # 图管理工具
├── build_neo4j_graph.py         # 图构建脚本
├── __init__.py                  # Python包初始化
│
├── DESIGN.md                    # 系统设计文档
├── KNOWLEDGE_GRAPH_DESIGN.md    # 知识图谱设计文档
├── README_EXTRACTION.md         # 提取流程说明
│
└── archive/                     # 归档目录
    ├── README.md                # 归档说明
    ├── completed_scripts/       # 已完成的一次性脚本
    ├── tests/                   # 测试脚本
    ├── analysis/                # 分析工具
    ├── old_versions/            # 旧版本脚本
    ├── logs/                    # 历史日志
    └── docs/                    # 历史文档
```

---

## 快速开始

### 1. 环境准备
```bash
# 安装依赖
pip install neo4j python-dotenv vertexai google-auth

# 配置环境变量（在项目根目录的.env文件）
VITE_GOOGLE_CLOUD_PROJECT=your-project-id
VITE_GOOGLE_CLOUD_LOCATION=us-central1
VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON={...}
```

### 2. 启动Neo4j
```bash
# 确保Neo4j服务运行在 bolt://localhost:7687
# 默认用户名: neo4j, 密码: password123
```

### 3. 运行提取
```bash
# 测试提取（10条消息）
python full_extraction.py --limit 10

# 完整提取
python full_extraction.py
```

### 4. 清理图谱（可选）
```bash
# 预览清理
python auto_graph_cleaner.py --dry-run

# 执行清理
python auto_graph_cleaner.py
```

---

## 当前状态 (2026-02-26 - 修复完成)

### 已完成功能 ✅
- ✅ 从微信聊天记录提取知识图谱
- ✅ Person实体去重和合并
- ✅ Person别名管理
- ✅ 智能过滤泛指/无意义实体
- ✅ Event-Person关系自动建立（支持别名识别）
- ✅ 时间信息提取和推断（54%的Event有具体日期）
- ✅ 批量并行处理
- ✅ **代码自动创建Event-Person关系**（2026-02-26修复）
- ✅ **所有节点包含conversation_name字段**（2026-02-26修复）
- ✅ **Prompt矛盾已解决**（2026-02-26修复）

### 数据统计
- 总Person数: 117个（吉月对话）
- 总Event数: 2,901个
- PARTICIPATED_IN关系: 4,439个
- Event时间覆盖率: 54%

### 示例查询
```cypher
// 查询两个人的共同事件（按时间排序）
MATCH (p1:Person {name: "米雪川"})-[:PARTICIPATED_IN]->(e:Event)<-[:PARTICIPATED_IN]-(p2:Person {name: "王露颖"})
WHERE e.inferred_time IS NOT NULL
RETURN e.name, e.inferred_time, e.description
ORDER BY e.inferred_time
LIMIT 50

// 查询某人参与的所有事件
MATCH (p:Person {name: "王露颖"})-[:PARTICIPATED_IN]->(e:Event)
RETURN e.name, e.inferred_time, e.description
ORDER BY e.inferred_time DESC
LIMIT 100

// 查询Person关系网络
MATCH (p:Person {name: "王露颖"})-[r:KNOWS]-(other:Person)
RETURN p, r, other
```

---

## 后续计划

### 🎯 重要更新（2026-02-26）

**已修复关键问题，可以安全进行全量提取：**

1. ✅ **Event-Person关系自动创建** - 代码层面保证，不依赖LLM
2. ✅ **conversation_name字段完整** - 所有节点都包含，防止误合并
3. ✅ **Prompt矛盾已解决** - 关系提取规则清晰明确

详见：`FIXES_APPLIED.md`

### 下次提取时自动完成
- ✅ Event-Person关系（代码自动创建 + prompt配置）
- ✅ 泛指实体过滤（已在提取prompt中配置）
- ✅ conversation_name字段（代码自动添加）

### 可能的改进
- [ ] 向量化存储（用于语义搜索）
- [ ] Web UI可视化界面
- [ ] 时间线视图
- [ ] 关系强度计算
- [ ] 增量更新机制

---

## 归档说明

所有临时脚本、测试代码、历史文档已归档到 `archive/` 目录。

如需查看历史脚本或文档，请参考 `archive/README.md`。

---

## License

内部项目
