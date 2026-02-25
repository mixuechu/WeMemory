# 数据加载模块 (data_loader)

## 功能
负责微信聊天记录的解析、清洗和预处理，将原始JSON数据转换为结构化的会话片段。

## 模块结构

```
data_loader/
├── __init__.py         # 模块导出
├── models.py           # 数据模型定义
├── parser.py           # JSON解析器
├── session.py          # 会话切分器
└── README.md           # 本文档
```

## 核心类

### 1. Message (models.py)
单条消息的数据类

**字段**：
- `sender`: 发送者ID
- `sender_name`: 发送者昵称
- `timestamp`: 消息时间戳
- `content`: 消息内容
- `msg_type`: 消息类型（0=文本，1=图片等）

### 2. ConversationSession (models.py)
会话片段的数据类，是向量embedding的基本单位

**字段**：
- `session_id`: 唯一标识符
- `conversation_name`: 对话名称
- `conversation_type`: 对话类型（私聊/群聊）
- `participants`: 参与者列表
- `start_time`: 开始时间
- `end_time`: 结束时间
- `messages`: 消息列表
- `session_type`: 'main' 或 'overlap'

### 3. WeChatParser (parser.py)
微信聊天记录JSON解析器

**方法**：
```python
# 加载对话文件
messages, metadata = WeChatParser.load_conversation(file_path)

# 解析消息列表
messages = WeChatParser.parse_messages(raw_messages)
```

### 4. SessionBuilder (session.py)
会话切分器 - 将消息流切分为会话片段

**策略**：混合滑动窗口
- Phase 1: 严格分割（按时间间隔30分钟 + 消息数3-20条）
- Phase 2: 创建主sessions
- Phase 3: 创建边界overlaps（跨分割点的重叠片段，提高召回率）

**参数**：
- `time_gap_minutes`: 时间间隔阈值（默认30分钟）
- `min_messages`: 最小消息数（默认3条）
- `max_messages`: 最大消息数（默认20条）

**使用方法**：
```python
from data_loader import SessionBuilder

builder = SessionBuilder(
    time_gap_minutes=30,
    min_messages=3,
    max_messages=20
)

sessions = builder.split_into_sessions(messages, conv_meta)
```

## 使用示例

```python
from pathlib import Path
from data_loader import WeChatParser, SessionBuilder

# 1. 加载对话
file_path = Path("chat_data_filtered/alex_li/alex_li.json")
messages, metadata = WeChatParser.load_conversation(file_path)

print(f"对话名称: {metadata['name']}")
print(f"总消息数: {len(messages)}")

# 2. 切分会话片段
builder = SessionBuilder()
sessions = builder.split_into_sessions(messages, metadata)

print(f"生成会话片段: {len(sessions)}个")

# 3. 查看第一个片段
session = sessions[0]
print(f"\n会话ID: {session.session_id}")
print(f"参与者: {', '.join(session.participants)}")
print(f"时间范围: {session.start_time} - {session.end_time}")
print(f"消息数: {len(session.messages)}")
print(f"类型: {session.session_type}")
```

## 设计理念

### 为什么要切分会话片段？
1. **语义完整性**：单条消息上下文不足，3-20条消息组成完整的对话片段
2. **时间连续性**：30分钟内的消息通常属于同一话题
3. **向量化粒度**：片段是生成embedding的基本单位

### 为什么使用混合滑动窗口？
1. **主sessions**：严格分割，避免话题混杂
2. **边界overlaps**：跨分割点的重叠片段，提高边界话题的召回率
3. **示例**：
   ```
   消息流: [1][2][3][4][5] | [6][7][8][9][10] | [11][12][13]
   主sessions: [1-5], [6-10], [11-13]
   边界overlaps: [3-8], [8-12]
   ```

## 依赖关系
- 无外部依赖（仅使用Python标准库）
- 被 `embedding` 模块使用

## 未来扩展
1. 支持更多消息类型（图片、语音等）
2. 支持自定义分割策略
3. 支持多线程并行解析
