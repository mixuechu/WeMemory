# 提取流程改进检查清单

## 已完成的改进步骤回顾

1. ✅ 使用最早的脚本去抽取出实体和关系
2. ✅ 意识到原始脚本不足，升级了Prompt，以排除无效实体
3. ✅ 半自动，和Claude Code配合，合并了多组Person实体
4. ✅ 使用一次性脚本，半自动为个别Person实体分配了正确的名字和Alias
5. ✅ 意识到原始脚本Event没有正确抽取以及和Person关联，使用一次性脚本补齐了米雪川和王露颖的事件关系

---

## 当前 `full_extraction.py` 检查结果

### ✅ 已包含的改进

1. **排除无效实体的Prompt改进** ✅
   - 位置：第113-152行
   - 详细列出了所有禁止提取的泛指词类型
   - 包含：代词、泛指、占位符、单独关系词、格式错误等

2. **Event的participants字段要求** ✅
   - 位置：第173-177行
   - 明确要求填写participants字段
   - 说明每个participant都会自动建立PARTICIPATED_IN关系

3. **PARTICIPATED_IN关系类型定义** ✅
   - 位置：第291-294行
   - 明确定义了PARTICIPATED_IN关系类型
   - 要求为每个participant创建关系

4. **Event的participants完整性规则** ✅
   - 位置：第314-317行
   - 要求名称必须和people数组中的name完全一致
   - 示例：Event "聚会", participants: ["米雪川", "Hunter"] → 必须创建2个PARTICIPATED_IN关系

---

### ❌ 发现的问题

#### 🚨 严重问题：Prompt中存在**矛盾规则**

**位置：** 第342-345行

```python
7. **Relationships 精简原则**：
   - 只提取核心关系：KNOWS, WORKS_AT, FAMILY_OF, DISCUSSED
   - 不要为每个Event自动生成PARTICIPATED_IN等关系  # ❌ 矛盾！
   - **目标**：一个对话5-10个关系，不要20+个
```

**矛盾点：**
- 第317行要求："每个participant都需要在relationships中创建PARTICIPATED_IN关系"
- 第344行又说："不要为每个Event自动生成PARTICIPATED_IN等关系"

**影响：**
- LLM看到矛盾指令会困惑
- 可能导致部分Event的PARTICIPATED_IN关系缺失
- 这正是我们之前发现的问题！

---

#### ❌ 代码层面：`build_neo4j_graph.py` 不会自动创建关系

**位置：** `build_neo4j_graph.py` 第224-239行

```python
# Events
for event in entities.get('events', []):
    self.create_event(event)  # 只创建Event节点，不创建关系
print(f"    ✅ {len(entities.get('events', []))} Events")

# 创建关系
print(f"  Creating relationships...")
relationships = entities.get('relationships', [])  # 只创建relationships数组中的关系
for rel in relationships:
    try:
        self.create_relationship(rel)
        success_count += 1
```

**问题：**
- `create_event()` 只把participants存储为Event的属性
- **不会自动**根据participants创建PARTICIPATED_IN关系
- 只会创建`relationships`数组中明确列出的关系

**结论：**
- 如果LLM没有在`relationships`数组中明确创建PARTICIPATED_IN关系
- 那么即使Event有participants字段，也不会建立关系
- 这就是为什么之前Event和Person没有关系！

---

## 🔧 需要修复的内容

### 1. 修复 `full_extraction.py` 的Prompt矛盾

**需要删除或修改：** 第342-345行的"Relationships 精简原则"

**建议修改为：**
```python
7. **Relationships 完整性原则**：
   - 必须提取的关系：KNOWS, WORKS_AT, FAMILY_OF, DISCUSSED_WITH, DISCUSSED_TOPIC
   - ⚠️ **Event关系（必需）**：每个Event的participants都必须创建PARTICIPATED_IN关系
   - 示例：Event有3个participants → 必须创建3个PARTICIPATED_IN关系
   - 不要遗漏关系，即使很明显也要明确提取
```

### 2. 两个解决方案选择其一

#### 方案A：依赖LLM在relationships中创建关系（当前方案）
- ✅ 优点：LLM可以控制关系质量
- ❌ 缺点：prompt复杂，容易遗漏
- **需要做：** 修复prompt矛盾，强调必须创建

#### 方案B：代码自动创建（推荐）⭐
- ✅ 优点：100%可靠，不会遗漏
- ✅ 优点：简化prompt
- **需要做：** 修改`build_neo4j_graph.py`

**推荐实现（方案B）：**
```python
# 在 create_event() 后自动创建关系
def create_event(self, event_data, conversation_name):
    """创建Event节点并自动创建PARTICIPATED_IN关系"""
    # 1. 创建Event节点
    query = """
    MERGE (e:Event {event_id: $event_id, conversation_name: $conv})
    SET e.name = $name,
        e.type = $type,
        e.description = $description,
        e.participants = $participants,
        ...
    RETURN e
    """
    # 执行创建Event节点

    # 2. 自动为每个participant创建PARTICIPATED_IN关系
    participants = event_data.get('participants', [])
    for participant in participants:
        try:
            self.driver.session().run("""
                MATCH (p:Person {name: $person, conversation_name: $conv})
                MATCH (e:Event {event_id: $event_id, conversation_name: $conv})
                MERGE (p)-[r:PARTICIPATED_IN]->(e)
                SET r.confidence = 0.9
            """, person=participant, event_id=event_id, conv=conversation_name)
        except Exception as e:
            print(f"  ⚠️ 无法创建关系: {participant} -> {event_data['name']}")
```

---

## 🎯 其他需要注意的点

### 半自动流程（需要用户参与）

以下流程**无需**也**不应该**在自动脚本中实现：

1. ✅ **Person实体合并** - 需要用户判断
   - 工具：`graph_manager.py` 或交互式脚本
   - 原因：自动合并容易误判（如：同名不同人）

2. ✅ **设置正式名称和Alias** - 需要用户提供信息
   - 工具：类似`set_person_names_and_aliases.py`
   - 原因：只有用户知道正确的全名

### Event的conversation_name字段缺失

**发现：** 检查发现Event节点可能缺少`conversation_name`字段

**位置：** `build_neo4j_graph.py` 第116-144行

**问题：**
```python
def create_event(self, event_data):
    """创建Event节点"""
    query = """
    MERGE (e:Event {name: $name})  # ❌ 只用name作为唯一标识
    SET e.type = $type,
        ...
    """
```

**风险：**
- 不同对话中的同名Event会被合并
- 无法区分不同对话的Event

**需要修复：**
```python
def create_event(self, event_data, conversation_name):
    query = """
    MERGE (e:Event {event_id: $event_id, conversation_name: $conv})  # ✅ 使用event_id和conversation_name
    SET e.name = $name,
        e.conversation_name = $conv,  # ✅ 明确设置
        ...
    """
```

---

## 📋 修复优先级

### 高优先级（必须修复）

1. **修复prompt矛盾** - 删除第344行
2. **添加Event-Person自动关联** - 修改`build_neo4j_graph.py`
3. **添加Event的conversation_name** - 修改`build_neo4j_graph.py`

### 中优先级（建议修复）

4. **优化prompt** - 简化relationships说明
5. **添加验证逻辑** - 检查participants中的人名是否存在

### 低优先级（可选）

6. **添加进度日志** - 显示关系创建进度
7. **添加统计信息** - Event-Person关系创建统计

---

## ✅ 总结

**当前状态：**
- Prompt改进 ✅ 已包含（但有矛盾）
- Event participants字段 ✅ 已要求
- PARTICIPATED_IN关系类型 ✅ 已定义
- **自动创建关系** ❌ 缺失（关键问题）

**如果现在直接运行全量提取：**
- ❌ 可能会缺失大量Event-Person关系（因为prompt矛盾）
- ❌ Event节点可能缺少conversation_name
- ✅ 泛指实体会被过滤

**需要先修复上述3个高优先级问题，才能进行全量提取！**
