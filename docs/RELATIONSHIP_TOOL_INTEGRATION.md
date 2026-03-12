# 关系查询Tool - 前端集成完成

## 集成内容

### 1. 新增Tool类
**文件**: `Meng/src/lib/tools/index.ts`

**类名**: `QueryRelationshipsTool`

**Tool定义**:
```typescript
{
  name: "query_person_relationships",
  description: "查询米雪川的核心人际关系。当用户问到某人是谁、某人的家人、某人的工作时使用。",
  input_schema: {
    type: "object",
    properties: {
      query: {
        type: "string",
        description: "查询字符串，例如：'赵萌'、'赵萌的配偶'、'谁是米雪川的妻子'"
      },
      max_results: {
        type: "number",
        description: "最大返回结果数，默认10",
        default: 10
      }
    },
    required: ["query"]
  }
}
```

**实现**:
- 调用后端API: `GET /api/relationships/query`
- 返回人物信息、简介、关系列表
- 错误处理：API失败时返回友好提示

### 2. 集成到Assistant工具集
**文件**: `Meng/src/lib/tools/index.ts`

**修改**: `getAssistantTools()` 函数

**变更**:
```typescript
// 之前：仅有search_knowledge
tools: [ComprehensiveSearchTool.getDefinition()]

// 现在：增加query_person_relationships
tools: [
  ComprehensiveSearchTool.getDefinition(),
  QueryRelationshipsTool.getDefinition(),
]

executors: new Map([
  ["search_knowledge", comprehensiveSearch],
  ["query_person_relationships", queryRelationships],  // 新增
])
```

### 3. 更新System Prompt
**文件**: `Meng/src/lib/services/agent.ts`

**新增说明**:
```
你拥有以下工具来访问用户的个人知识：

1. **search_knowledge** - 搜索聊天记忆和知识图谱
   当需要了解历史对话内容、事件记录时使用

2. **query_person_relationships** - 查询人物关系
   当用户问到某人是谁、某人的家人、某人的工作、人际关系时使用
   例如："赵萌是谁"、"我老婆是谁"、"我的家人有谁"

使用指南：
- 当用户明确询问人物关系时，优先使用 query_person_relationships
- 当需要对话内容或事件信息时，使用 search_knowledge
- 查询结果要自然地融入回答中，不要提及"使用了工具"
- 如果查不到信息，诚实告知
```

### 4. 更新日志输出
**文件**: `Meng/src/lib/services/agent.ts`

**日志**: 显示可用工具列表
```typescript
console.log(`[Agent] Assistant模式: 使用工具集 [search_knowledge, query_person_relationships]`);
```

## 启动测试

### 1. 启动后端API
```bash
# 终端1: 启动Flask后端
cd /path/to/wechat_memory
python api/main.py
```

**验证**: 访问 http://localhost:8000/docs，确认 `/api/relationships/query` 端点存在

### 2. 启动前端
```bash
# 终端2: 启动Next.js前端
cd /path/to/wechat_memory/Meng
npm run dev
```

**访问**: http://localhost:3000/chat

### 3. 测试对话

#### 测试1: 查询人物身份
**输入**: "赵萌是谁？"

**预期流程**:
1. LLM识别需要查询人物关系
2. 调用 `query_person_relationships(query="赵萌")`
3. 返回：
   ```json
   {
     "person": "赵萌",
     "profile": "赵萌已婚，配偶是米雪川。同事有宋文婷、丁梦晓。",
     "relationships": [...]
   }
   ```
4. LLM生成回答："赵萌是您的配偶。她的同事有宋文婷和丁梦晓。"

#### 测试2: 查询家庭关系
**输入**: "我的家人有谁？"

**预期流程**:
1. LLM调用 `query_person_relationships(query="米雪川的家人")`
2. 返回家庭成员列表
3. LLM生成回答

#### 测试3: 查询工作关系
**输入**: "赵萌的同事是谁？"

**预期流程**:
1. LLM调用 `query_person_relationships(query="赵萌的同事")`
2. 返回同事列表
3. LLM生成回答

## 工具选择逻辑

### 何时使用 query_person_relationships
- ✅ "XX是谁"
- ✅ "我的家人有谁"
- ✅ "XX的配偶"
- ✅ "XX在哪工作"
- ✅ "我和XX是什么关系"

### 何时使用 search_knowledge
- ✅ "我和XX聊过什么"
- ✅ "上次讨论的项目"
- ✅ "最近发生了什么事"
- ✅ "关于Python的对话"

### 两个工具配合
LLM可以在一个回答中同时使用两个工具：

**用户**: "赵萌是谁？我们最近聊过什么？"

**LLM处理**:
1. 调用 `query_person_relationships(query="赵萌")` → 获取身份
2. 调用 `search_knowledge(query="和赵萌的对话")` → 获取聊天记录
3. 综合回答

## 技术亮点

1. **轻量级**: 仅在需要时查询，不会每次对话都调用
2. **高质量**: 74人+159条手动审核的关系
3. **智能路由**: LLM自动选择正确的工具
4. **自然融入**: 查询结果自然地融入对话回复
5. **节省成本**: 按需检索，比全量注入节省90%+ token

## 成本对比

### 之前（假设全量注入）
- 115人 + 159关系 ≈ 3000+ tokens
- 每次对话都注入
- 月成本（1000次对话）: ~$10+

### 现在（按需查询）
- 仅在询问关系时调用
- 平均10次对话调用1次
- 每次查询结果<500 tokens
- 月成本（1000次对话）: ~$1

**节省**: 90%+

## 数据来源

**文件**: `data/relationships/core_relationships.json`

**内容**:
- 74个核心人物（有关系数据）
- 159条核心关系
- 手动审核的高质量数据
- 导出时间：2026-03-11

**关系类型**:
- 配偶：54条
- 兄弟姐妹：23条
- 孩子：20条
- 工作地点：19条
- 表亲：18条
- 其他：25条

## 监控和调试

### 查看Tool调用日志

**后端日志** (api/main.py):
```
[Agent] Assistant模式: 使用工具集 [search_knowledge, query_person_relationships]
[Agent] 生成完成，使用了 1 次工具
```

**前端控制台** (浏览器DevTools):
```
[QueryRelationshipsTool] 查询: 赵萌
[QueryRelationshipsTool] 成功: 返回4条关系
```

### 检查API调用

**浏览器Network面板**:
1. 查看 `/api/chat` 请求
2. 检查请求体中的 `message`
3. 查看响应中的 `message`（LLM回复）

**后端API日志**:
```bash
# 查看关系查询API调用
tail -f api.log | grep relationships
```

## 故障排查

### 1. Tool未被调用

**症状**: 用户问"赵萌是谁"，LLM直接回答"我不知道"

**检查**:
- ✅ 后端API是否运行（http://localhost:8000/docs）
- ✅ System Prompt是否包含工具说明
- ✅ `getAssistantTools()` 是否返回了工具
- ✅ LLM是否理解何时使用工具

**解决**: 增强System Prompt中的使用场景说明

### 2. API调用失败

**症状**: Tool被调用但返回错误

**检查**:
- ✅ 后端关系服务是否初始化
- ✅ `core_relationships.json` 是否存在
- ✅ API端点URL是否正确

**解决**: 检查后端日志，确认服务状态

### 3. 返回数据为空

**症状**: API成功但返回空结果

**检查**:
- ✅ 查询的人名是否在数据中
- ✅ 搜索算法是否匹配（模糊vs精确）

**解决**: 查看 `core_relationships.json`，确认人名拼写

## 下一步优化

### 短期
- [ ] 添加Tool调用状态显示（前端UI）
- [ ] 优化错误提示
- [ ] 增加更多使用场景示例

### 中期
- [ ] 支持别名映射（昵称）
- [ ] 缓存常用查询结果
- [ ] 增加关系类型过滤

### 长期
- [ ] 可视化关系图谱
- [ ] 关系推理（间接关系）
- [ ] 自动学习新关系

---

**集成完成时间**: 2026-03-12
**版本**: 1.0.0
**状态**: 已集成，待测试
