# 别名增强版自然语言三元组

## 概述

基于 `natural_language_triplets_enhanced.json`，为每条记录添加了别名信息，解决向量搜索中的人名匹配问题。

## 问题背景

在纯向量搜索场景下，同一个人的不同称呼在向量空间距离很远：
- "Jake" vs "阿吉" / "二哥" / "前端🐔"
- "王露颖" vs "Sunny" / "露露"
- "米雪川" vs "我" / "你" / "User A"

导致搜索时无法匹配到相关记录。

## 解决方案

为每条记录添加 `searchable_text` 字段，在原文本后追加别名信息：

```json
{
  "text": "目前，阿吉正准备或正在前往学校。",
  "searchable_text": "目前，阿吉正准备或正在前往学校。 [相关人物: Jake(别名: 阿吉, 二哥, 大鸡, 鸡哥)]"
}
```

## 数据统计

- **总记录数**: 7,865条
- **添加别名信息**: 6,879条 (87.5%)
- **别名来源**: 从v3.1知识图谱提取1,503个实体的别名映射
- **多别名实体**: 482个

## 使用方法

### 向量化时使用 searchable_text

```python
import json
from sentence_transformers import SentenceTransformer

# 加载数据
with open('natural_language_triplets_with_aliases.json', 'r') as f:
    data = json.load(f)

model = SentenceTransformer('your-model')

# 向量化时使用 searchable_text
for record in data['records']:
    embedding = model.encode(record['searchable_text'])
    # 存入FAISS...
```

### 展示时使用原文本

```python
# 搜索返回结果后，展示给用户时用原始text
def display_result(record):
    print(record['text'])  # 不展示别名信息
```

## 效果验证

**案例1**: 文本用别名 "阿吉"，搜索 "Jake"
```
原版: 找不到 (向量距离远)
别名增强版: ✅ 能找到 (searchable_text包含"Jake")
```

**案例2**: 文本用别名 "露露"，搜索 "王露颖"  
```
原版: 找不到
别名增强版: ✅ 能找到 (searchable_text包含"王露颖")
```

**案例3**: 文本用规范名 "Jake"，搜索 "阿吉"
```
原版: 找不到
别名增强版: ✅ 能找到 (searchable_text包含"阿吉")
```

## 文件信息

- **输入文件**: 
  - `curated_knowledge_graph_v3.1.json` (别名映射源)
  - `natural_language_triplets_enhanced.json` (LLM增强的三元组)
- **中间文件**: `entity_alias_map.json` (1,503个实体的别名映射表)
- **输出文件**: `natural_language_triplets_with_aliases.json` (6.14 MB)

## 版本历史

- v1: 规则生成的自然语言三元组
- v2: LLM增强的事件描述
- **v3 (当前)**: 添加别名信息，提升可搜索性

## 下一步

可以直接使用 `natural_language_triplets_with_aliases.json` 进行：
1. 向量化 (embedding)
2. 构建FAISS索引
3. 实现语义搜索功能
