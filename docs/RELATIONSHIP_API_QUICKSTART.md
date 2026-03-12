# 核心关系API - 快速开始

## 启动API服务

```bash
cd /path/to/wechat_memory
python api/main.py
```

访问API文档：http://localhost:8000/docs

## 快速测试

### 1. 查询赵萌的关系

```bash
curl "http://localhost:8000/api/relationships/query?query=赵萌"
```

**响应**:
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
    }
  ]
}
```

### 2. 获取家族树

```bash
curl "http://localhost:8000/api/relationships/family/赵萌"
```

**响应**:
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

### 3. 获取统计信息

```bash
curl "http://localhost:8000/api/relationships/stats"
```

**响应**:
```json
{
  "total_persons": 74,
  "total_relationships": 159,
  "reviewed_persons": 106,
  "export_time": "2026-03-11T17:19:18.631Z"
}
```

## Python示例

```python
import requests

BASE_URL = "http://localhost:8000"

# 查询人物关系
def query_person(name: str):
    response = requests.get(
        f"{BASE_URL}/api/relationships/query",
        params={"query": name}
    )
    return response.json()

# 使用示例
result = query_person("赵萌")
if result["success"]:
    print(f"人物: {result['person']}")
    print(f"简介: {result['profile']}")
    print(f"关系数: {len(result['relationships'])}")
```

## LLM Tool集成示例

### OpenAI Function Calling

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "query_person_relationships",
            "description": "查询米雪川的核心人际关系。当用户问到某人是谁、某人的家人时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "查询字符串，如'赵萌'或'赵萌的配偶'"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

# 实现tool调用
def query_person_relationships(query: str):
    response = requests.get(
        f"{BASE_URL}/api/relationships/query",
        params={"query": query}
    )
    return response.json()
```

### Claude Tool Use

```python
tools = [
    {
        "name": "query_person_relationships",
        "description": "查询米雪川的核心人际关系。当用户问到某人是谁、某人的家人、某人的工作等问题时使用。支持自然语言查询。",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "查询字符串，如'赵萌'、'赵萌的配偶'、'谁是米雪川的妻子'"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大返回结果数（可选，默认10）"
                }
            },
            "required": ["query"]
        }
    }
]
```

## 常见查询

```bash
# 查某人是谁
curl "http://localhost:8000/api/relationships/query?query=赵萌"

# 查配偶
curl "http://localhost:8000/api/relationships/query?query=赵萌的配偶"

# 查家人
curl "http://localhost:8000/api/relationships/family/米雪川"

# 搜索人名
curl "http://localhost:8000/api/relationships/search?query=萌"

# 获取某人的所有关系
curl "http://localhost:8000/api/relationships/person/赵萌"
```

## 作为个人助理Tool使用

当集成到个人助理时，关系查询Tool应该：

1. **按需调用**: 仅在用户询问人物关系时调用
2. **自然融入**: 查询结果自然地融入对话回复
3. **处理失败**: 查不到时诚实告知
4. **避免滥用**: 不要每次对话都查询

### 示例对话

**用户**: "赵萌是谁？"

**助理思考**: 用户询问人物，需要调用关系查询Tool

**调用Tool**: `query_person_relationships(query="赵萌")`

**Tool返回**:
```json
{
  "person": "赵萌",
  "profile": "赵萌已婚，配偶是米雪川。同事有宋文婷、丁梦晓。",
  "relationships": [...]
}
```

**助理回复**: "赵萌是您的配偶。她的同事有宋文婷和丁梦晓。"

---

**API版本**: 1.0.0
**数据版本**: core_relationships.json (2026-03-11)
**更新时间**: 2026-03-12
