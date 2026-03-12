# WeMemory - 快速开始

## 🎯 核心功能

**MENG个人助理** - 拥有记忆和关系查询能力的AI助理

### 能力
1. **聊天记忆检索** - 搜索历史对话内容
2. **关系查询** - 查询核心人物关系（74人+159条关系）
3. **智能对话** - 自然流畅的助理交互

### 技术栈
- **后端**: Python + FastAPI + FAISS
- **前端**: Next.js + TypeScript + Claude API
- **数据**: 138个精选对话 + 核心关系图谱

## 🚀 一键启动

```bash
cd /path/to/wechat_memory
./start_all.sh
```

访问：http://localhost:3000/chat

## 📖 手动启动

### 1. 启动后端API

```bash
# 终端1
cd /path/to/wechat_memory
python api/main.py
```

**验证**: 访问 http://localhost:8000/docs

### 2. 启动前端

```bash
# 终端2
cd /path/to/wechat_memory/Meng
npm run dev
```

**访问**: http://localhost:3000/chat

## 💬 测试对话

### 关系查询
- "赵萌是谁？"
- "我的家人有谁？"
- "赵萌的同事是谁？"

### 记忆检索
- "我和某某聊过什么？"
- "最近讨论的项目"
- "关于Python的对话"

### 组合查询
- "赵萌是谁？我们最近聊过什么？"

## 🛠️ 可用工具

### 1. search_knowledge
**用途**: 搜索聊天记忆和知识图谱
**示例**: "我和XX聊过什么"

### 2. query_person_relationships
**用途**: 查询人物关系
**示例**: "XX是谁"、"我的家人"

## 📊 数据概览

### 对话数据
- 138个精选对话
- text-multilingual-embedding-002 向量模型

### 关系数据
- 74个核心人物
- 159条核心关系
- 手动审核的高质量数据

## 📚 完整文档

### 后端API
- `docs/RELATIONSHIP_API_QUICKSTART.md` - API快速开始
- `docs/CORE_RELATIONSHIP_TOOL_SUMMARY.md` - 后端实现总结

### 前端集成
- `docs/RELATIONSHIP_TOOL_GUIDE.md` - Tool使用指南
- `docs/RELATIONSHIP_TOOL_INTEGRATION.md` - 前端集成说明

### 总结
- `docs/INTEGRATION_COMPLETE_SUMMARY.md` - 完整集成总结

## 🔍 监控

### 后端日志
```
✓ 关系服务初始化完成
  - 核心人物: 74人
  - 核心关系: 159条

[Agent] Assistant模式: 使用工具集 [search_knowledge, query_person_relationships]
```

### 前端控制台
```
[QueryRelationshipsTool] 查询: 赵萌
[QueryRelationshipsTool] 成功: 返回4条关系
```

## 🎯 项目结构

```
wechat_memory/
├── api/                    # 后端API
│   ├── main.py            # 主入口
│   ├── services/          # 服务层
│   └── routers/           # 路由
├── Meng/                  # 前端Next.js
│   ├── src/app/chat/      # 聊天界面
│   └── src/lib/tools/     # Tool定义
├── data/                  # 数据
│   ├── conversations/     # 对话数据
│   └── relationships/     # 关系数据
├── vector_stores/         # 向量库
├── docs/                  # 文档
├── archive/               # 归档
└── start_all.sh          # 启动脚本
```

## ⚙️ 环境要求

- Python 3.8+
- Node.js 16+
- Claude API Key (在Meng/.env中配置)

## 🆘 故障排查

### 后端启动失败
- 检查向量库是否存在: `vector_stores/conversations/embeddings.pkl`
- 检查关系数据是否存在: `data/relationships/core_relationships.json`

### 前端无法连接
- 确认后端API运行在 http://localhost:8000
- 检查CORS设置

### Tool未被调用
- 查看后端日志确认工具已注册
- 检查System Prompt是否包含工具说明

## 📌 重要提示

1. **数字人功能已归档**: 专注个人助理核心功能
2. **关系查询按需使用**: 节省90%+ token成本
3. **数据已精选**: 138对话+74人关系，质量优先

## 🎉 开始使用

```bash
./start_all.sh
```

然后访问 http://localhost:3000/chat，开始对话！

---

**版本**: 1.0.0
**更新时间**: 2026-03-12
**状态**: 生产就绪
