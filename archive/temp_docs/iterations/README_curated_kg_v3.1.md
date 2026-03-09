# 精简版知识图谱 v3.1 - 关系剪枝版

生成时间: 2026-03-06

## 🎯 v3.1的主要优化

在v3的基础上，对关系进行了大幅剪枝，只保留对"个人助理"应用场景真正有价值的结构化关系。

### 优化原则

**保留的关系（19.9%）**：
1. ✅ **家庭关系** - 所有`HAS_SPOUSE/PARENT/CHILD/SIBLING/COUSIN`等
2. ✅ **工作/职业** - `WORKS_AT/IS_COLLEAGUE_OF/STUDIED_AT`等
3. ✅ **位置信息** - `LOCATED_AT`
4. ✅ **强人际关系** - `FRIENDS_WITH/MENTOR_OF`

**删除的关系（80.1%）**：
1. ❌ **冗余关系** - `KNOWS`（废话，能对话就认识）
2. ❌ **重复信息** - `PARTICIPATED_IN`（events中已有participants）
3. ❌ **对话元信息** - `DISCUSSED_WITH/DISCUSSED_TOPIC`（对话本身说明）
4. ❌ **一次性关系** - 出现<5次的各种琐碎关系

## 📊 版本对比

| 项目 | v3 | v3.1 | 变化 |
|------|----|----|------|
| 对话数 | 138 | 138 | - |
| 实体数 | 2,496 | 2,496 | - |
| 事件数 | 5,297 | 5,297 | - |
| **关系数** | **12,907** | **2,568** | **-10,339 (-80.1%)** |
| 话题数 | 1,550 | 1,550 | - |
| 别名数 | 4,605 | 4,605 | - |
| 文件大小 | 6.05 MB | 3.54 MB | -2.51 MB (-41.5%) |

## 🔧 关系剪枝统计

### 保留的关系类型（57种，2,568个）

**家庭关系（主要）**：
- HAS_SPOUSE（配偶）: 575个
- HAS_PARENT（父母）: 488个
- HAS_CHILD（子女）: 365个
- HAS_SIBLING（兄弟姐妹）: 348个
- HAS_COUSIN（表亲）: 96个
- HAS_GRANDPARENT（祖父母）: 22个
- HAS_AUNT/UNCLE（姑姨舅）: 38个
- 其他各种亲属关系...

**工作/职业**：
- WORKS_AT（工作地点）: 268个
- IS_COLLEAGUE_OF（同事）: 3个
- STUDIED_AT（学习地点）: 3个
- WORKS_WITH/WORKS_AS等

**位置**：
- LOCATED_AT（所在位置）: 248个

**人际关系**：
- FRIENDS_WITH（朋友）: 4个
- MENTOR_OF（导师）: 1个

### 删除的关系类型（68种，10,339个）

**冗余关系（占79.4%）**：
- KNOWS: 6,396个 ❌
- PARTICIPATED_IN: 2,471个 ❌
- DISCUSSED_WITH: 788个 ❌
- DISCUSSED_TOPIC: 590个 ❌

**一次性关系（89个）**：
- 各种出现<5次的琐碎关系
- 如：GUESSED_OWNER_OF、WILL_BE_INTRODUCED_TO、OPPOSED_TO等

## ✅ 优化效果

### 1. 关系数量大幅优化
- 从12,907个减少到2,568个
- 删除率: **80.1%**
- 只保留对个人助理真正有用的关系

### 2. 数据质量提升
- ✅ 家庭关系完整保留（回答"谁是我妻子/父母"）
- ✅ 工作关系完整保留（回答"我在哪工作/谁是同事"）
- ✅ 教育关系完整保留（回答"我在哪上学"）
- ❌ 冗余废话全部删除（"认识谁"这种没意义的关系）

### 3. 文件大小优化
- 从6.05 MB降至3.54 MB
- 减少41.5%，查询和加载更快

### 4. 符合应用场景
对于"个人助理 + 向量知识库"的应用：
- **结构化关系**（如家庭、工作）→ 通过图谱查询
- **复杂语义**（如"讨论过什么话题"）→ 通过向量检索
- **事件内容** → 完整保留，通过向量检索

## 🎯 为什么这样优化？

### 理由1: 关系类型明确性
- "我妻子是谁？" → 需要`HAS_SPOUSE`关系 ✓
- "我在哪工作？" → 需要`WORKS_AT`关系 ✓
- "我认识谁？" → `KNOWS`关系是废话 ✗（能对话就认识）

### 理由2: 避免信息重复
- `PARTICIPATED_IN`（参与事件）→ events中已有participants字段
- `DISCUSSED_TOPIC`（讨论话题）→ topics中已有
- 保留这些关系只会造成冗余

### 理由3: 向量检索互补
- "我和某人聊过什么？" → 向量检索对话内容
- "我参加过什么活动？" → 向量检索事件
- 不需要`DISCUSSED_WITH`这种关系

## 📝 数据结构

```json
{
  "conversations": {
    "对话名": {
      "entities": {
        "米雪川": {
          "final_name": "米雪川",
          "all_aliases": ["米雪川", "雪川", ...],
          "mentions": 1547,
          "events": [...],              // ✅ 完整保留
          "relationships": [            // ⚠️ 只保留重要关系
            {
              "type": "HAS_SPOUSE",     // ✓ 保留
              "other": "赵萌",
              "other_type": "Person",
              "context": "..."
            }
            // ❌ KNOWS, PARTICIPATED_IN等已删除
          ],
          "topics": [...]               // ✅ 完整保留
        }
      }
    }
  },
  "metadata": {
    "version": "curated_v3.1",
    "relationship_stats": {
      "original_count": 12907,
      "filtered_count": 2568,
      "deleted_count": 10339,
      "retention_rate": "19.9%"
    }
  }
}
```

## 🚀 后续步骤

v3.1已完成关系剪枝，数据已经非常干净，可以：
1. **直接导入Neo4j** - 构建知识图谱
2. **构建向量索引** - 对events和topics内容做向量化
3. **混合检索** - 结构化关系查询 + 向量语义检索

## 📁 文件位置

**curated_knowledge_graph_v3.1.json** (3.54 MB)
- 位置: `/Users/mimimi/Desktop/personal_projects/wechat_memory/wechat_memory_curated/`
- 推荐使用此版本进行最终建图

## ⚠️ 备份说明

- v3版本已保留: `curated_knowledge_graph_v3.json` (6.05 MB)
- v2版本已保留: `curated_knowledge_graph_v2.json` (2.58 MB)
- 原始数据已保留: `merged_entities_by_conversation.json`
- 编辑规则已保留: `conversation_entity_edits_curated.json`

所有历史版本都可回溯，确保数据安全。

## 💡 设计理念

**核心思想**：关系不是越多越好，而是**有用的关系才有价值**。

对于个人助理场景：
- ✅ 需要知道"谁是我妻子"（结构化关系）
- ✅ 需要知道"我在哪工作"（结构化关系）
- ❌ 不需要知道"我认识谁"（废话）
- ❌ 不需要知道"我参与了什么事件"（events中已有）

**结论**：v3.1是最适合个人助理应用的知识图谱版本，既保留了必要的结构化信息，又删除了冗余废话，文件更小、查询更快、数据更干净。
