# 核心关系查询Tool - 使用指南

## 概述

核心关系查询Tool提供轻量级的人物关系查询能力，专为个人助理LLM设计。

### 设计理念

- **按需检索**: 不需要每次都注入全部关系到prompt
- **节省成本**: 仅在需要时查询，避免token浪费
- **高质量数据**: 115个核心人物 + 159条手动审核的关系
- **智能查询**: 支持自然语言查询，自动匹配人名

## Tool定义（供LLM使用）

### 1. 查询人物关系（主要接口）

```json
{
  "name": "query_person_relationships",
  "description": "查询米雪川的核心人际关系。当用户问到某人是谁、某人的家人、某人的工作等问题时使用。支持自然语言查询。",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "查询字符串，如'赵萌'、'赵萌的配偶'、'谁是米雪川的妻子'"
      },
      "max_results": {
        "type": "integer",
        "description": "最大返回结果数（可选，默认10）",
        "default": 10
      }
    },
    "required": ["query"]
  }
}
```

**API调用**:
```bash
GET /api/relationships/query?query=赵萌&max_results=10
```

**响应示例**:
```json
{
  "success": true,
  "query": "赵萌",
  "person": "赵萌",
  "profile": "赵萌已婚，配偶是米雪川。同事有宋文婷、丁梦晓。",
  "relationships": [
    {
      "text": "米雪川是赵萌的配偶",
      "type": "HAS_SPOUSE",
      "subject": "赵萌",
      "object": "米雪川"
    },
    {
      "text": "宋文婷和赵萌是同事",
      "type": "HAS_COLLEAGUE",
      "subject": "宋文婷",
      "object": "赵萌"
    }
  ]
}
```

### 2. 获取家族树

```json
{
  "name": "get_family_tree",
  "description": "获取某人的直系家属（配偶、父母、孩子、兄弟姐妹）。当用户问到家庭成员时使用。",
  "parameters": {
    "type": "object",
    "properties": {
      "person_name": {
        "type": "string",
        "description": "人物名字，如'赵萌'"
      }
    },
    "required": ["person_name"]
  }
}
```

**API调用**:
```bash
GET /api/relationships/family/赵萌
```

**响应示例**:
```json
{
  "success": true,
  "person": "赵萌",
  "family": {
    "spouse": ["米雪川"],
    "parents": [],
    "children": [],
    "siblings": []
  }
}
```

## 使用场景示例

### 场景1: 用户问某人是谁

**用户**: "赵萌是谁？"

**LLM思考**: 需要查询赵萌的基本信息和关系

**调用Tool**:
```python
query_person_relationships(query="赵萌")
```

**LLM回复**: "赵萌是您的配偶。她的同事有宋文婷、丁梦晓。"

### 场景2: 用户问家庭成员

**用户**: "我的直系亲属有哪些？"

**LLM思考**: 需要查询米雪川的家族树

**调用Tool**:
```python
get_family_tree(person_name="米雪川")
```

**LLM回复**: "您的配偶是赵萌，父母有..."

### 场景3: 用户问工作关系

**用户**: "赵萌的同事有谁？"

**LLM思考**: 需要查询赵萌的工作关系

**调用Tool**:
```python
query_person_relationships(query="赵萌的同事")
```

**LLM回复**: "赵萌的同事有宋文婷和丁梦晓。"

## 关系类型说明

数据中包含以下关系类型：

| 类型 | 说明 | 数量 |
|------|------|------|
| HAS_SPOUSE | 配偶关系 | 54条 |
| HAS_SIBLING | 兄弟姐妹 | 23条 |
| HAS_CHILD | 孩子 | 20条 |
| WORKS_AT | 工作地点 | 19条 |
| HAS_COUSIN | 表亲 | 18条 |
| LOCATED_AT | 居住地 | 9条 |
| HAS_PARENT | 父母 | 9条 |
| HAS_EX_PARTNER | 前任 | 3条 |
| HAS_COLLEAGUE | 同事 | 2条 |
| HAS_GRANDPARENT | 祖父母 | 1条 |
| STUDIED_AT | 就读学校 | 1条 |

## API端点列表

### 完整端点

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/relationships/query` | 智能查询（推荐） |
| GET | `/api/relationships/person/{person_name}` | 获取人物所有关系 |
| GET | `/api/relationships/family/{person_name}` | 获取家族树 |
| GET | `/api/relationships/related/{person_name}` | 获取相关人物 |
| GET | `/api/relationships/search` | 搜索人物 |
| GET | `/api/relationships/stats` | 获取统计信息 |

## 最佳实践

### 1. 优先使用智能查询

`/api/relationships/query` 接口支持自然语言，最灵活：

```bash
# 直接查人名
GET /api/relationships/query?query=赵萌

# 查关系
GET /api/relationships/query?query=赵萌的配偶

# 自然问句
GET /api/relationships/query?query=谁是米雪川的妻子
```

### 2. 仅在必要时查询

不要在每次对话时都查询关系，仅在用户明确问到人物关系时才调用Tool。

### 3. 缓存常用关系

如果对话中多次提到同一人物，可以在首次查询后缓存结果，避免重复调用。

### 4. 处理未找到的情况

查询可能返回 `success: false`，需要妥善处理：

```json
{
  "success": false,
  "message": "未找到相关人物: XXX"
}
```

LLM应该回复："抱歉，我没有关于XXX的关系信息。"

## 数据质量保证

- ✅ 手动审核的核心关系
- ✅ 仅包含重要关系（家庭、工作、地点）
- ✅ 无低价值关系（friend/knows）
- ✅ 115个核心人物，159条关系
- ✅ 数据导出时间：2026-03-11

## 与向量检索的配合

关系查询Tool与向量检索是互补的：

- **向量检索**: 查找相关对话内容
- **关系查询**: 快速获取人物关系背景

两者配合使用，为个人助理提供完整的记忆能力。

## 示例System Prompt片段

```
你是MENG个人助理，拥有以下能力：

1. 记忆召回：通过向量检索查找相关对话
2. 关系查询：查询米雪川的核心人际关系

当用户问到某人是谁、某人的家人、某人的工作等问题时，
使用 query_person_relationships 工具查询关系信息。

注意：
- 仅在用户明确询问人物关系时才查询
- 查询结果要自然地融入回答中
- 如果查不到，诚实告知
```

## 未来扩展

可能的扩展方向：

1. **别名支持**: 支持昵称、外号查询
2. **关系推理**: 间接关系推导（A的配偶的兄弟）
3. **时间维度**: 关系变化历史
4. **关系强度**: 量化关系亲密度
5. **自动更新**: 从新对话中学习关系

---

**更新时间**: 2026-03-12
**数据版本**: core_relationships.json (2026-03-11)
