# ChatLab 格式数据样例

本目录包含脱敏后的 WeChat 对话数据样例，展示 WeFlow 导出的 ChatLab 格式结构。

## 文件说明

### `chatlab_format_private_chat.json`
私聊对话样例，展示：
- 基础的私聊格式
- 文本消息（type: 0）
- 系统消息（type: 80）
- 转账消息（type: 99）

### `chatlab_format_group_chat.json`
群聊对话样例，展示：
- 群聊特有的 `groupId` 字段
- 多个成员的消息交互
- 图片消息（type: 1）

## ChatLab 格式结构

### 顶层结构
```json
{
  "chatlab": { ... },    // 元数据
  "meta": { ... },       // 对话信息
  "members": [ ... ],    // 参与者列表
  "messages": [ ... ]    // 消息列表
}
```

### chatlab 元数据
```json
{
  "version": "0.0.2",           // ChatLab格式版本
  "exportedAt": 1771866312,     // 导出时间戳（Unix时间）
  "generator": "WeFlow"         // 生成工具
}
```

### meta 对话信息

**私聊**：
```json
{
  "name": "联系人名称",
  "platform": "wechat",
  "type": "private",
  "groupAvatar": "头像URL"
}
```

**群聊**：
```json
{
  "name": "群聊名称",
  "platform": "wechat",
  "type": "group",
  "groupId": "123456789@chatroom",  // 群聊特有
  "groupAvatar": "群头像URL"
}
```

### members 参与者列表
```json
[
  {
    "platformId": "wxid_xxx",     // 微信ID
    "accountName": "昵称",        // 显示名称
    "avatar": "头像URL"           // 头像地址
  }
]
```

**注意**：
- 私聊：包含两个成员（对方和自己）
- 群聊：第一个成员是群本身，后续是群成员

### messages 消息列表
```json
[
  {
    "sender": "wxid_xxx",         // 发送者ID
    "accountName": "发送者名称",  // 发送者昵称
    "timestamp": 1744384972,      // 消息时间戳（Unix时间）
    "type": 0,                    // 消息类型
    "content": "消息内容"         // 消息正文
  }
]
```

## 消息类型 (type)

| 类型码 | 说明 | 示例 |
|--------|------|------|
| 0 | 文本消息 | "你好" |
| 1 | 图片消息 | "[图片]" |
| 3 | 语音消息 | "[语音]" |
| 34 | 音频消息 | "[音频]" |
| 43 | 视频消息 | "[视频]" |
| 47 | 表情包 | "[表情]" |
| 49 | 链接/小程序 | "[链接]" |
| 80 | 系统消息 | "你已添加了xxx" |
| 99 | 转账/红包 | "[转账] ¥7.65" |

## 数据脱敏说明

样例数据已进行脱敏处理：
- ✅ `platformId` 替换为示例ID
- ✅ `accountName` 替换为通用名称（张三、李四等）
- ✅ `avatar` URL 截断
- ✅ 消息内容改为通用对话
- ✅ 时间戳保留真实格式但使用示例数值

## 使用方式

### 验证数据格式
```bash
python scripts/validate_chatlab_format.py examples/data_samples/chatlab_format_private_chat.json
```

### 作为测试数据
```python
import json

with open('examples/data_samples/chatlab_format_private_chat.json', 'r') as f:
    sample_data = json.load(f)

# 检查格式
assert 'chatlab' in sample_data
assert 'meta' in sample_data
assert 'members' in sample_data
assert 'messages' in sample_data
```

## 参考资料

- [WeFlow 项目](https://github.com/hicccc77/WeFlow) - 微信数据导出工具
- [docs/data-export.md](../../docs/data-export.md) - 完整的数据导出指南
