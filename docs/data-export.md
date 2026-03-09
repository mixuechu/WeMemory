# 数据导出指南

本文档详细说明如何使用 WeFlow 从微信客户端导出聊天记录，并生成 WeMemory 可用的 **ChatLab 格式** JSON 数据。

---

## 概述

### 为什么需要导出数据？

微信聊天记录默认存储在客户端本地数据库中，无法直接访问。要构建个人记忆系统，首先需要：

1. **获取数据主权**：将聊天记录从微信客户端导出
2. **标准化格式**：转换为结构化的 **ChatLab JSON 格式**
3. **隐私保护**：所有数据仅存储在本地，不上传第三方

---

## 使用 WeFlow 导出数据（推荐）

[WeFlow](https://github.com/hicccc77/WeFlow) 是一个开源的微信聊天记录导出工具，支持直接导出为 **ChatLab 格式** JSON。

### 为什么选择 WeFlow？

- ✅ **开源、免费**：代码完全公开，可审查安全性
- ✅ **跨平台**：支持 Windows/Mac 微信客户端
- ✅ **ChatLab 格式**：导出的 JSON 格式规范、结构清晰
- ✅ **完整元数据**：保留时间戳、发送者、消息类型、头像等
- ✅ **活跃维护**：社区活跃，问题响应快

### 导出步骤

#### 第一步：安装 WeFlow

```bash
# 克隆 WeFlow 仓库
git clone https://github.com/hicccc77/WeFlow.git
cd WeFlow

# 安装 Python 依赖
pip install -r requirements.txt
```

**系统要求**：
- Python 3.8+
- 微信 PC 客户端（Windows 或 Mac）

#### 第二步：定位微信数据库

WeFlow 需要访问微信本地数据库，路径通常为：

**Windows**:
```
C:\Users\{用户名}\Documents\WeChat Files\{微信ID}\Msg\
```

**Mac**:
```
~/Library/Containers/com.tencent.xinWeChat/Data/Library/Application Support/com.tencent.xinWeChat/{微信ID}/Message/
```

**小技巧**：
- 在微信中查找你的微信ID：设置 → 账号与安全 → 微信号
- 确保微信客户端已完全退出（否则数据库被锁定）

#### 第三步：运行 WeFlow

```bash
# 启动 WeFlow（图形界面）
python gui.py
```

或者使用命令行：
```bash
python main.py --db-path /path/to/wechat/db --output-dir exports/
```

#### 第四步：配置导出选项（重要）

在 WeFlow 界面中，按照以下步骤操作：

1. **选择数据源**
   - 点击"选择数据库路径"
   - 导航到上一步找到的微信数据库目录
   - 选择 `MicroMsg.db` 文件

2. **选择导出格式** ⚠️ **关键步骤**
   - 在"导出格式"下拉菜单中选择 **"ChatLab 格式"**
   - ❌ **不要**选择其他格式（如 TXT、HTML、CSV）
   - ✅ **必须**选择 "ChatLab 格式" 才能与 WeMemory 兼容

3. **选择要导出的对话**
   - 全部对话（推荐用于完整记忆系统）
   - 或勾选特定联系人/群组

4. **配置导出选项**
   - ✅ 包含消息内容
   - ✅ 包含时间戳
   - ✅ 包含发送者信息
   - ✅ 包含头像URL（用于知识图谱展示）
   - ⬜ 导出媒体文件（图片/视频，可选，会大幅增加空间）

5. **设置输出目录**
   - 选择导出文件保存位置
   - 建议创建专门目录：`wechat_exports/`

6. **开始导出**
   - 点击"开始导出"按钮
   - 等待导出完成（时间取决于对话数量）

#### 第五步：验证导出结果

导出完成后，检查输出目录：

```
wechat_exports/
├── 张三/
│   ├── 张三.json          # ChatLab 格式 JSON 文件
│   └── media/             # 媒体文件（如果导出了）
├── 家庭群/
│   ├── 家庭群.json
│   └── media/
└── 公司项目组/
    ├── 公司项目组.json
    └── media/
```

**目录结构说明**：
- 每个联系人/群组一个独立文件夹
- `{名称}.json` 是 ChatLab 格式的对话数据
- `media/` 存放图片、视频等媒体文件（如果勾选了）

---

## ChatLab JSON 格式详解

### 什么是 ChatLab 格式？

ChatLab 是一种标准化的聊天记录 JSON 格式，由 WeFlow 定义和导出。它提供了：
- 📋 **规范的结构**：统一的字段命名和嵌套结构
- 🔢 **完整的元数据**：版本号、导出时间、生成工具
- 👤 **详细的参与者信息**：ID、昵称、头像URL
- 📝 **丰富的消息类型**：文本、图片、语音、转账等

### 格式结构

#### 顶层结构

```json
{
  "chatlab": { ... },      // ChatLab 元数据
  "meta": { ... },         // 对话信息（私聊/群聊）
  "members": [ ... ],      // 参与者列表
  "messages": [ ... ]      // 消息列表
}
```

#### 1. chatlab 元数据

```json
{
  "chatlab": {
    "version": "0.0.2",           // ChatLab 格式版本
    "exportedAt": 1771866312,     // 导出时间戳（Unix 时间戳，秒）
    "generator": "WeFlow"         // 生成工具名称
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `version` | string | ChatLab 格式版本号 |
| `exportedAt` | integer | 导出时间（Unix 时间戳） |
| `generator` | string | 生成工具（通常为 "WeFlow"） |

#### 2. meta 对话信息

**私聊 (type: "private")**:
```json
{
  "meta": {
    "name": "张三",                 // 联系人名称
    "platform": "wechat",          // 平台（固定为 wechat）
    "type": "private",             // 对话类型
    "groupAvatar": "https://..."   // 头像 URL
  }
}
```

**群聊 (type: "group")**:
```json
{
  "meta": {
    "name": "家庭群",               // 群聊名称
    "platform": "wechat",          // 平台（固定为 wechat）
    "type": "group",               // 对话类型
    "groupId": "123456789@chatroom", // 群组 ID（群聊特有）
    "groupAvatar": "https://..."   // 群头像 URL
  }
}
```

| 字段 | 类型 | 说明 | 私聊 | 群聊 |
|------|------|------|------|------|
| `name` | string | 对话名称 | ✅ | ✅ |
| `platform` | string | 平台（通常为 "wechat"） | ✅ | ✅ |
| `type` | string | 对话类型："private" 或 "group" | ✅ | ✅ |
| `groupId` | string | 群组 ID | ❌ | ✅ |
| `groupAvatar` | string | 头像/群头像 URL | ✅ | ✅ |

#### 3. members 参与者列表

```json
{
  "members": [
    {
      "platformId": "wxid_abc123",      // 微信 ID
      "accountName": "张三",            // 昵称
      "avatar": "https://..."           // 头像 URL
    },
    {
      "platformId": "wxid_self",
      "accountName": "我自己",
      "avatar": "https://..."
    }
  ]
}
```

**注意**：
- **私聊**：包含 2 个成员（对方 + 自己）
- **群聊**：第一个成员是群本身，后续是群成员列表

| 字段 | 类型 | 说明 |
|------|------|------|
| `platformId` | string | 平台用户 ID（微信 wxid） |
| `accountName` | string | 用户昵称/显示名称 |
| `avatar` | string | 头像 URL |

#### 4. messages 消息列表

```json
{
  "messages": [
    {
      "sender": "wxid_abc123",          // 发送者 ID
      "accountName": "张三",            // 发送者昵称
      "timestamp": 1744384972,          // 消息时间戳（Unix）
      "type": 0,                        // 消息类型码
      "content": "今天晚上回家吃饭吗？" // 消息内容
    },
    {
      "sender": "wxid_self",
      "accountName": "我自己",
      "timestamp": 1744390353,
      "type": 0,
      "content": "好的，6点到家"
    },
    {
      "sender": "wxid_abc123",
      "accountName": "张三",
      "timestamp": 1744390400,
      "type": 1,
      "content": "[图片]"
    },
    {
      "sender": "wxid_abc123",
      "accountName": "张三",
      "timestamp": 1751721612,
      "type": 99,
      "content": "[转账] ¥7.65"
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `sender` | string | 发送者 ID（对应 members 中的 platformId） |
| `accountName` | string | 发送者昵称 |
| `timestamp` | integer | 消息时间戳（Unix 秒） |
| `type` | integer | 消息类型码（见下表） |
| `content` | string | 消息内容 |

### 消息类型码 (type)

| 类型码 | 说明 | content 示例 |
|--------|------|--------------|
| **0** | 文本消息 | "你好" |
| **1** | 图片消息 | "[图片]" |
| **3** | 语音消息 | "[语音]" |
| **34** | 音频消息 | "[音频]" |
| **43** | 视频消息 | "[视频]" |
| **47** | 表情包 | "[表情]" |
| **49** | 链接/小程序 | "[链接]" 或 "[小程序]" |
| **80** | 系统消息 | "你已添加了xxx" / "xxx撤回了一条消息" |
| **99** | 转账/红包 | "[转账] ¥7.65" / "[红包]" |

**常见系统消息 (type: 80)**:
- "你已添加了xxx，现在可以开始聊天了。"
- "xxx邀请你加入了群聊"
- "xxx撤回了一条消息"
- "xxx拍了拍你"

### 完整样例

WeMemory 提供了两个脱敏的真实数据样例：

1. **私聊样例**: [`examples/data_samples/chatlab_format_private_chat.json`](../examples/data_samples/chatlab_format_private_chat.json)
2. **群聊样例**: [`examples/data_samples/chatlab_format_group_chat.json`](../examples/data_samples/chatlab_format_group_chat.json)

详细格式说明见: [`examples/data_samples/README.md`](../examples/data_samples/README.md)

---

## 其他导出工具（可选）

如果 WeFlow 不适用于您的环境，可以考虑以下替代方案。**但注意**：这些工具导出的格式需要手动转换为 ChatLab 格式才能在 WeMemory 中使用。

### WeChatMsg（Windows）

- **GitHub**: [LC044/WeChatMsg](https://github.com/LC044/WeChatMsg)
- **平台**：仅支持 Windows 微信
- **导出格式**：HTML、CSV、TXT
- ⚠️ **需要手动转换为 ChatLab JSON 格式**

### 手动数据库读取（不推荐）

**仅供参考**，不建议直接操作微信数据库：

```python
# 此方法风险较高，可能损坏数据库或违反微信服务条款
# 仅作为技术参考，实际使用请选择 WeFlow
import sqlite3

db_path = "path/to/WeChat/Msg/MicroMsg.db"
conn = sqlite3.connect(db_path)
# ... 查询和转换逻辑
```

**风险**：
- ❌ 需要管理员权限
- ❌ 数据库结构随微信版本变化
- ❌ 可能损坏数据库或导致微信崩溃
- ❌ 导出格式需要大量手动转换工作

**结论**：强烈建议使用 WeFlow 而非手动方法。

---

## 数据存放位置

导出完成后，将 WeFlow 导出的文件夹放到 WeMemory 项目的数据目录：

### 推荐目录结构

```
WeMemory/
└── data/
    └── conversations/
        └── chat_data_filtered/
            ├── 张三/
            │   ├── 张三.json          # ChatLab 格式 JSON
            │   └── media/             # 媒体文件（可选）
            ├── 家庭群/
            │   ├── 家庭群.json
            │   └── media/
            └── 公司项目组/
                ├── 公司项目组.json
                └── media/
```

### 操作步骤

```bash
# 1. 创建数据目录
mkdir -p data/conversations/chat_data_filtered/

# 2. 复制 WeFlow 导出的文件夹
cp -r wechat_exports/* data/conversations/chat_data_filtered/

# 3. 验证目录结构
ls -lh data/conversations/chat_data_filtered/
# 应该看到多个子目录，每个对应一个联系人/群组

# 4. 检查 JSON 文件
find data/conversations/chat_data_filtered/ -name "*.json" -type f
```

**注意**：
- 保留 WeFlow 导出的目录结构（每个联系人/群组一个文件夹）
- JSON 文件名应与文件夹名一致（例如：`张三/张三.json`）
- `media/` 子目录可选（如果不需要媒体文件，可以删除以节省空间）

---

## 数据验证

导出完成后，**强烈建议**使用 WeMemory 提供的验证脚本检查数据格式。

### 使用验证脚本

WeMemory 提供了专门的 ChatLab 格式验证工具：

```bash
# 验证单个 JSON 文件
python scripts/validate_chatlab_format.py \
  data/conversations/chat_data_filtered/张三/张三.json

# 验证整个目录
python scripts/validate_chatlab_format.py \
  data/conversations/chat_data_filtered/
```

### 验证输出示例

**单个文件验证**：
```
============================================================
ChatLab 格式验证工具
============================================================

📄 验证文件: data/conversations/chat_data_filtered/张三/张三.json

✅ 验证通过！数据格式完全符合 ChatLab 规范

✅ 验证成功！
```

**目录批量验证**：
```
📁 找到 138 个JSON文件，开始验证...

[1/138] 验证: 张三.json
  ✅ 通过

[2/138] 验证: 家庭群.json
  ✅ 通过

[3/138] 验证: 公司项目组.json
  ❌ 失败 (2 个错误)
     - meta 缺少必需键: type
     - messages[5].type 应为整数类型
     ... 还有 0 个错误

...

============================================================
验证汇总
============================================================
总计: 138 个文件
✅ 通过: 136 个
❌ 失败: 2 个
通过率: 98.6%
```

### 常见验证错误及解决方案

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `缺少必需的顶层键: chatlab` | JSON 格式不是 ChatLab | 确认 WeFlow 选择了"ChatLab 格式"导出 |
| `meta.type 必须是 ['private', 'group'] 之一` | 对话类型字段缺失或错误 | 重新导出数据 |
| `JSON解析失败` | JSON 格式错误 | 检查文件是否完整，重新导出 |
| `messages[X].type 应为整数类型` | 消息类型字段类型错误 | 更新 WeFlow 到最新版本 |
| `群聊 (type: group) 必须包含 groupId 字段` | 群聊缺少 groupId | 重新导出群聊数据 |

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

### Q1: WeFlow 导出失败，提示"数据库已加密"

**原因**：部分微信版本（特别是 Mac 版本）会加密本地数据库。

**解决方案**：
1. 确保微信客户端已完全退出（不是最小化，是完全退出）
2. 更新到最新版本的 WeFlow：
   ```bash
   cd WeFlow
   git pull origin main
   pip install -r requirements.txt --upgrade
   ```
3. 参考 WeFlow 文档中的数据库解密教程
4. 如果仍无法解决，在 WeFlow Issues 中搜索或提问

### Q2: 导出的 JSON 文件格式不是 ChatLab

**原因**：在 WeFlow 中选择了错误的导出格式。

**解决方案**：
1. 重新运行 WeFlow
2. 在"导出格式"下拉菜单中，**必须选择 "ChatLab 格式"**
3. 不要选择 TXT、HTML、CSV 等其他格式
4. 导出后使用验证脚本检查：
   ```bash
   python scripts/validate_chatlab_format.py data/conversations/chat_data_filtered/
   ```

### Q3: 某些对话导出后消息数量为 0

**原因**：
- 对话只包含系统消息（如撤回、拍一拍）
- 对话时间范围不在导出范围内
- 数据库损坏或数据丢失

**解决方案**：
1. 在 WeChat 客户端中检查该对话是否有实际内容
2. 调整 WeFlow 的时间范围设置
3. 尝试重新导出该对话

### Q4: 导出的 JSON 文件太大（>100MB），处理很慢

**原因**：对话历史记录太多（通常是群聊）。

**解决方案**：

**方法 1**: 按时间范围导出（推荐）
```bash
# 只导出最近一年的数据
python main.py --start-date 2025-01-01 --end-date 2025-12-31
```

**方法 2**: 数据清洗后再处理
- 先导出全部数据
- 使用 WeMemory 的数据清洗功能过滤无用消息
- 详见 [数据清洗指南](data-cleaning.md)

**方法 3**: 选择性导出对话
- 不导出不重要的群聊
- 专注于有价值的私聊和小群组

### Q5: 如何批量导出多个对话？

**答**：WeFlow 支持批量导出。

在 WeFlow 界面中：
1. 勾选"全部对话"，或
2. 按住 Ctrl/Cmd 多选特定对话
3. 点击"开始导出"

WeFlow 会自动为每个对话创建独立的文件夹。

### Q6: 验证脚本报错：`缺少必需键: groupId`

**原因**：群聊数据缺少 `groupId` 字段。

**解决方案**：
1. 这通常是 WeFlow 版本较旧导致的
2. 更新 WeFlow 到最新版本
3. 重新导出该群聊

### Q7: 媒体文件（图片/视频）占用空间太大

**建议**：
1. 如果只需要文本记忆，**不勾选**"导出媒体文件"选项
2. WeMemory 的向量搜索和知识图谱主要基于文本内容
3. 图片描述（如 "[图片]"）仍会保留在 JSON 中

### Q8: 导出后发现敏感信息（手机号、地址等）

**隐私保护方案**：
1. 使用数据脱敏脚本（即将提供）
2. 手动编辑 JSON 文件删除敏感内容
3. 确保 `data/` 目录在 `.gitignore` 中（已配置）
4. 不要将原始数据上传到任何云服务或代码仓库

---

## 总结：导出检查清单

在进入下一步之前，请确认：

- ✅ 使用 WeFlow 导出数据
- ✅ **选择了 "ChatLab 格式"** 导出选项
- ✅ 数据已放置在 `data/conversations/chat_data_filtered/` 目录
- ✅ 每个对话有独立的文件夹（包含 `{名称}.json` 文件）
- ✅ 运行验证脚本检查格式：
  ```bash
  python scripts/validate_chatlab_format.py data/conversations/chat_data_filtered/
  ```
- ✅ 验证通过率 >95%
- ✅ 确认敏感信息已脱敏或妥善保护

---

## 下一步

数据导出和验证完成后，继续以下步骤：

1. 📝 **数据清洗**（可选）
   - 过滤系统消息、去重、质量评估
   - 详见：[数据清洗指南](data-cleaning.md)（即将提供）

2. 🧠 **生成向量库**
   - 使用 text-multilingual-embedding-002 模型
   - 构建对话向量和三元组向量
   - 详见：[Embedding 指南](embedding.md)

3. 🕸️ **构建知识图谱**
   - 抽取实体、事件、关系
   - 生成自然语言三元组
   - 详见：[知识图谱指南](knowledge-graph.md)

4. 🚀 **启动 API 服务**
   - 混合搜索（向量 + BM25）
   - 知识图谱查询
   - 详见：[快速开始](quickstart.md)

---

## 参考资料

- 📦 [WeFlow 项目](https://github.com/hicccc77/WeFlow) - 微信数据导出工具
- 📋 [ChatLab 格式说明](../examples/data_samples/README.md) - 详细格式文档
- 🔍 [验证脚本](../scripts/validate_chatlab_format.py) - 数据格式验证工具
- 📄 [数据样例](../examples/data_samples/) - 脱敏后的真实数据样例

---

返回 [主文档](../README.md)
