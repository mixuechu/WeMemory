# 精简版知识图谱 v2

生成时间: 2026-03-06

## 📁 文件说明

### 新生成的文件
- **curated_knowledge_graph_v2.json** (2.58 MB)
  - 精简版建图数据
  - 只包含138个精选对话
  - 只包含重要实体（已去除2315个不需要的实体）
  - 已应用所有合并、改名规则
  - 保留了完整的映射关系

### 原始文件（已保留备份）
- **merged_entities_by_conversation.json** - 原始实体数据
- **conversation_entity_edits_curated.json** - 编辑规则
- **person_details_lite.json** - 原始事件/关系数据

## 📊 数据统计

| 项目 | 数量 |
|------|------|
| 对话数 | 138 |
| 最终实体 | 2,496 |
| 排除实体 | 2,315 |
| 合并组 | 432 |
| 事件 | 5,297 |
| 关系 | 12,907 |
| 话题 | 1,550 |

## 🔧 数据结构

```json
{
  "conversations": {
    "对话名": {
      "entities": {
        "最终实体名": {
          "final_name": "最终实体名",
          "original_names": ["原名1", "原名2", ...],  // 映射关系
          "mentions": 100,
          "events": [...],         // 所有事件（已更新参与者名）
          "relationships": [...],  // 所有关系（已更新other字段）
          "topics": [...]          // 所有话题
        }
      },
      "original_entity_count": 675,
      "final_entity_count": 257,
      "excluded_count": 418
    }
  },
  "metadata": {
    "version": "curated_v2",
    "total_conversations": 138,
    "total_entities": 2496,
    ...
  }
}
```

## ✅ 已完成的处理

1. ✅ **实体去重** - 合并了432组重复实体
   - 例: "妈" 合并了16个原名（"妈妈"、"母亲"、"米雪川的母亲"等）
   
2. ✅ **实体改名** - 纠正了32个错误的名字
   
3. ✅ **实体排除** - 删除了2315个不需要的实体
   
4. ✅ **保留映射** - 每个最终实体都保留了original_names列表
   
5. ✅ **更新引用** - 所有关系和事件中的实体名都更新为最终名
   - 关系中的"other"字段已更新
   - 事件中的"participants"字段已更新
   
6. ✅ **保留所有事件和关系** - 等待后续剪枝

## 📝 示例数据

### 合并示例
```json
{
  "final_name": "妈",
  "original_names": [
    "妈", "妈妈", "母亲", "米雪川的母亲", "米雪川的妈妈",
    "薛惠亮", "User's Mother", "Unknown Mother", ...
  ],
  "mentions": 1547,
  "events": [...],
  "relationships": [...]
}
```

### 关系示例（已更新实体名）
```json
{
  "type": "KNOWS",
  "role": "source",
  "other": "米雪川",  // 已更新为最终名
  "other_type": "Person",
  "context": "..."
}
```

### 事件示例（已更新参与者名）
```json
{
  "name": "打牌",
  "participants": ["张美阳", "米雪川"],  // 已更新为最终名
  "description": "..."
}
```

## 🎯 后续步骤

1. **关系剪枝** - 筛选重要的关系
2. **事件剪枝** - 筛选重要的事件
3. **最终建图** - 应用剪枝后生成最终知识图谱

## ⚠️ 注意事项

- 原始数据已完整保留，可随时回溯
- 映射关系已保存，可追溯每个合并操作
- 关系中引用了被排除实体的关系已自动过滤（12907 < 13120）
