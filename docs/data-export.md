# 数据导出指南

本文档详细说明如何从微信客户端导出聊天记录，并转换为 WeMemory 可用的 JSON 格式。

---

## 概述

### 为什么需要导出数据？

微信聊天记录默认存储在客户端本地数据库中，无法直接访问。要构建个人记忆系统，首先需要：

1. **获取数据主权**：将聊天记录从微信客户端导出
2. **标准化格式**：转换为结构化的 JSON 格式
3. **隐私保护**：所有数据仅存储在本地，不上传第三方

---

## 方案一：使用 WeFlow（推荐）

[WeFlow](https://github.com/hicccc77/WeFlow) 是一个开源的微信聊天记录导出工具，支持直接导出为 JSON 格式。

### 优点

- ✅ 开源、免费
- ✅ 支持 Windows/Mac 微信客户端
- ✅ 直接导出 JSON 格式
- ✅ 保留完整的消息元数据（时间、发送者、消息类型）

### 导出步骤

#### 1. 安装 WeFlow

```bash
# 克隆 WeFlow 仓库
git clone https://github.com/hicccc77/WeFlow.git
cd WeFlow

# 安装依赖
pip install -r requirements.txt
```

#### 2. 运行导出

```bash
# 启动 WeFlow
python main.py

# 或使用图形界面（如果支持）
python gui.py
```

#### 3. 选择导出选项

在 WeFlow 界面中：

1. **选择数据源**：微信数据库路径
   - Windows: `C:\Users\{用户名}\Documents\WeChat Files\{微信ID}\Msg\`
   - Mac: `~/Library/Containers/com.tencent.xinWeChat/Data/Library/Application Support/com.tencent.xinWeChat/{微信ID}/Message/`

2. **选择导出格式**：JSON

3. **选择导出对话**：
   - 全部对话
   - 或指定特定联系人/群组

4. **配置导出选项**：
   - ✅ 包含消息内容
   - ✅ 包含时间戳
   - ✅ 包含发送者信息
   - ⬜ 包含图片/文件（可选）

#### 4. 导出完成

导出的 JSON 文件会保存到指定目录，结构如下：

```
exports/
├── 家庭群_20240101-20241231.json
├── 公司项目组_20240101-20241231.json
├── 张三_20240101-20241231.json
└── ...
```

---

## JSON 数据格式

### 标准格式

WeFlow 导出的 JSON 格式如下：

```json
{
  "conversation_id": "12345678",
  "conversation_name": "家庭群",
  "conversation_type": "group",
  "participants": ["我", "妈妈", "爸爸", "弟弟"],
  "message_count": 1523,
  "time_range": {
    "start": "2024-01-01 00:00:00",
    "end": "2024-12-31 23:59:59"
  },
  "messages": [
    {
      "message_id": "msg_001",
      "timestamp": "2024-01-01 10:30:00",
      "sender_name": "妈妈",
      "sender_id": "wxid_abc123",
      "content": "今天晚上回家吃饭吗？",
      "msg_type": "text"
    },
    {
      "message_id": "msg_002",
      "timestamp": "2024-01-01 10:32:15",
      "sender_name": "我",
      "sender_id": "wxid_me",
      "content": "好的，6点到家",
      "msg_type": "text"
    },
    {
      "message_id": "msg_003",
      "timestamp": "2024-01-01 10:35:00",
      "sender_name": "爸爸",
      "sender_id": "wxid_def456",
      "content": "[图片]",
      "msg_type": "image",
      "media_path": "images/img_20240101_103500.jpg"
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 说明 | 是否必需 |
|------|------|------|---------|
| `conversation_id` | string | 对话唯一标识 | 可选 |
| `conversation_name` | string | 对话名称（联系人/群名） | **必需** |
| `conversation_type` | string | 对话类型：`private`/`group` | 可选 |
| `participants` | array | 参与者列表 | 可选 |
| `message_count` | number | 消息总数 | 可选 |
| `time_range` | object | 时间范围 | 可选 |
| `messages` | array | 消息列表 | **必需** |
| `messages[].timestamp` | string | 消息时间戳 | **必需** |
| `messages[].sender_name` | string | 发送者名称 | **必需** |
| `messages[].content` | string | 消息内容 | **必需** |
| `messages[].msg_type` | string | 消息类型：`text`/`image`/`voice`/`video` | **必需** |

---

## 方案二：其他导出工具

如果 WeFlow 不适用，可以考虑以下替代方案：

### 1. WeChatMsg（Windows）

- GitHub: [https://github.com/LC044/WeChatMsg](https://github.com/LC044/WeChatMsg)
- 支持：Windows 微信客户端
- 导出格式：HTML、CSV、TXT
- **需要手动转换为 JSON**

### 2. 手动导出（不推荐）

通过直接读取微信数据库：

```python
import sqlite3
import json
from datetime import datetime

# 连接微信数据库
db_path = "path/to/WeChat/Msg/MicroMsg.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查询消息
cursor.execute("""
    SELECT talker, content, createTime, type
    FROM message
    WHERE talker = 'wxid_target'
    ORDER BY createTime
""")

messages = []
for row in cursor.fetchall():
    messages.append({
        "sender_name": row[0],
        "content": row[1],
        "timestamp": datetime.fromtimestamp(row[2]/1000).strftime('%Y-%m-%d %H:%M:%S'),
        "msg_type": "text" if row[3] == 1 else "other"
    })

# 保存为 JSON
with open('export.json', 'w', encoding='utf-8') as f:
    json.dump({"messages": messages}, f, ensure_ascii=False, indent=2)
```

**注意**：
- 需要root/管理员权限
- 微信数据库结构可能随版本变化
- 风险较高，可能损坏数据库

---

## 数据存放位置

导出完成后，将 JSON 文件放到以下目录：

```
WeMemory/
└── data/
    └── conversations/
        └── chat_data_filtered/
            ├── 家庭群_20240101-20241231.json
            ├── 公司项目组_20240101-20241231.json
            └── ...
```

### 目录结构建议

```bash
# 创建目录
mkdir -p data/conversations/chat_data_filtered/

# 复制导出的 JSON 文件
cp exports/*.json data/conversations/chat_data_filtered/

# 验证
ls -lh data/conversations/chat_data_filtered/
```

---

## 数据验证

导出完成后，建议验证数据格式：

### 验证脚本

```python
import json
import os

def validate_json_files(directory):
    """验证 JSON 文件格式"""
    issues = []

    for filename in os.listdir(directory):
        if not filename.endswith('.json'):
            continue

        filepath = os.path.join(directory, filename)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 检查必需字段
            if 'messages' not in data:
                issues.append(f"{filename}: 缺少 'messages' 字段")
                continue

            # 检查消息格式
            for i, msg in enumerate(data['messages']):
                required_fields = ['timestamp', 'sender_name', 'content', 'msg_type']
                for field in required_fields:
                    if field not in msg:
                        issues.append(f"{filename}: 消息 {i} 缺少 '{field}' 字段")

            print(f"✓ {filename}: {len(data['messages'])} 条消息")

        except json.JSONDecodeError as e:
            issues.append(f"{filename}: JSON 格式错误 - {e}")
        except Exception as e:
            issues.append(f"{filename}: 验证失败 - {e}")

    if issues:
        print("\n⚠️  发现问题：")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✅ 所有文件验证通过！")

# 运行验证
validate_json_files('data/conversations/chat_data_filtered/')
```

---

## 数据清洗预处理

导出的原始数据可能包含：

- 系统消息（撤回、拍一拍等）
- 重复消息
- 无意义的表情符号
- 敏感信息

建议在生成向量库之前进行清洗，详见 [数据清洗指南](data-cleaning.md)。

---

## 隐私与安全

### 数据安全建议

1. **本地存储**：
   - 所有数据仅存储在本地
   - 不上传到任何云服务
   - Git 忽略 `data/` 目录（已配置在 `.gitignore`）

2. **敏感信息处理**：
   ```python
   # 脱敏示例
   import re

   def mask_sensitive_info(text):
       # 隐藏手机号
       text = re.sub(r'\d{11}', '***手机号***', text)
       # 隐藏身份证号
       text = re.sub(r'\d{17}[\dXx]', '***身份证***', text)
       # 隐藏银行卡号
       text = re.sub(r'\d{16,19}', '***银行卡***', text)
       return text
   ```

3. **访问控制**：
   ```bash
   # 设置文件权限（Linux/Mac）
   chmod 600 data/conversations/chat_data_filtered/*.json
   ```

4. **加密存储**（可选）：
   ```python
   from cryptography.fernet import Fernet

   # 生成密钥
   key = Fernet.generate_key()
   cipher = Fernet(key)

   # 加密 JSON
   with open('data.json', 'rb') as f:
       encrypted = cipher.encrypt(f.read())

   with open('data.json.enc', 'wb') as f:
       f.write(encrypted)
   ```

---

## 常见问题

### Q: WeFlow 导出失败，提示数据库已加密

**原因**：部分微信版本会加密数据库

**解决方案**：
1. 更新到最新版本的 WeFlow
2. 或使用其他导出工具（如 WeChatMsg）
3. 参考 WeFlow 文档的解密教程

### Q: 导出的 JSON 文件太大，无法处理

**解决方案**：
1. 按时间范围分割：
   ```bash
   # 只导出最近一年的数据
   python main.py --start-date 2024-01-01
   ```

2. 按对话分割：
   ```bash
   # 每个对话单独导出
   python main.py --split-by-conversation
   ```

### Q: 如何批量导出多个对话？

**方法 1**：使用 WeFlow 的批量导出功能

**方法 2**：编写脚本：
```python
conversations = ["家庭群", "公司项目组", "同学群"]

for conv in conversations:
    os.system(f"python main.py --conversation '{conv}' --output exports/{conv}.json")
```

---

## 下一步

数据导出完成后：

1. 📖 [数据清洗与筛选](data-cleaning.md)
2. 🧠 [生成向量库](embedding.md)
3. 🚀 [启动服务](quickstart.md#第四步启动服务)

---

返回 [主文档](../README.md)
