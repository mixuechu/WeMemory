# 配置系统

WeMemory 使用统一的 YAML 配置系统，支持环境变量替换和配置覆盖。

---

## 快速开始

### 1. 设置环境变量

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件，填入你的配置
# 最重要的是设置 GOOGLE_CLOUD_PROJECT
nano .env
```

### 2. 验证配置

```bash
# 验证配置是否正确
python scripts/validate_config.py

# 同时测试 Vertex AI 连接（需要网络）
python scripts/validate_config.py --test-api
```

### 3. 使用配置

```python
from config.loader import load_config

# 加载默认配置
config = load_config()

# 访问配置（支持点号访问）
project_id = config.vertex_ai.project_id
embedding_model = config.vertex_ai.embedding.model
api_port = config.api.port

# 或使用字典方式
project_id = config['vertex_ai']['project_id']
```

---

## 配置文件

### default.yaml

默认配置文件，包含所有配置项的默认值和说明。

**位置**: `config/default.yaml`

**特点**:
- 完整的配置项
- 详细的注释说明
- 合理的默认值
- 支持环境变量替换

### user.yaml（可选）

用户自定义配置文件，用于覆盖默认配置。

**位置**: `config/user.yaml`

**使用场景**:
- 个人开发环境配置
- 不想修改默认配置文件
- 需要快速切换不同配置

**示例**:

```yaml
# config/user.yaml
# 只需要写要覆盖的配置项

vertex_ai:
  region: asia-northeast1  # 覆盖默认的 us-central1

api:
  port: 9000  # 覆盖默认的 8000
  reload: true  # 开发模式启用热重载

logging:
  level: DEBUG  # 开发时使用 DEBUG 级别
```

**合并规则**:
- `user.yaml` 的配置会覆盖 `default.yaml` 的相同配置
- 嵌套配置会深度合并
- `user.yaml` 不会被提交到 Git（已在 `.gitignore` 中）

---

## 环境变量替换

配置文件支持 `${VAR}` 语法自动替换环境变量。

### 基本用法

```yaml
# config/default.yaml
vertex_ai:
  project_id: ${GOOGLE_CLOUD_PROJECT}  # 从环境变量读取
  region: us-central1
```

### 带默认值

```yaml
# 如果环境变量不存在，使用默认值
api:
  port: ${API_PORT:8000}  # 默认 8000
  host: ${API_HOST:0.0.0.0}  # 默认 0.0.0.0
```

### 类型转换

环境变量会自动转换类型：

```bash
# .env
API_PORT=8000
ENABLE_CACHE=true
TEMPERATURE=0.0
```

```yaml
# 自动转换为
api:
  port: 8000  # 整数
  enable_cache: true  # 布尔值
  temperature: 0.0  # 浮点数
```

---

## 配置项说明

### Vertex AI 配置

```yaml
vertex_ai:
  project_id: ${GOOGLE_CLOUD_PROJECT}  # GCP 项目 ID（必需）
  region: us-central1                  # 区域

  embedding:
    model: text-multilingual-embedding-002  # Embedding 模型
    dimensions: 768                         # 向量维度
    batch_size: 32                          # 批量大小

  extraction:
    model: claude-3-5-sonnet-20241022  # 知识抽取模型
    max_tokens: 8192
    temperature: 0.0
```

### 路径配置

```yaml
paths:
  input_data: data/conversations/chat_data_filtered/  # 输入数据
  vector_stores: vector_stores/                       # 向量库
  knowledge_graph: data/knowledge_graph/              # 知识图谱
  checkpoints: .checkpoints/                          # 检查点
  logs: logs/                                         # 日志
```

### Pipeline 配置

```yaml
pipeline:
  data_cleaning:
    min_messages: 3              # 最小消息数
    max_time_gap_minutes: 30     # 最大时间间隔

  embedding:
    batch_size: 32               # 批量大小
    checkpoint_interval: 100     # 检查点间隔

  knowledge_extraction:
    batch_size: 10
    confidence_threshold: 0.8
```

### API 配置

```yaml
api:
  host: 0.0.0.0    # 监听地址
  port: 8000       # 端口
  reload: false    # 热重载（开发模式）
  workers: 1       # 工作进程数

  search:
    default_top_k: 5    # 默认返回结果数
    max_top_k: 20       # 最大返回结果数
```

### 日志配置

```yaml
logging:
  level: INFO  # 日志级别：DEBUG, INFO, WARNING, ERROR

  file:
    enabled: true
    path: logs/wememory.log
    max_bytes: 10485760  # 10MB
    backup_count: 5

  console:
    enabled: true
    color: true
```

---

## 高级用法

### 程序化访问

```python
from config.loader import load_config

config = load_config()

# 点号访问（推荐）
model = config.vertex_ai.embedding.model

# 字典访问
model = config['vertex_ai']['embedding']['model']

# 嵌套路径访问
model = config.get_nested('vertex_ai.embedding.model')

# 带默认值的访问
port = config.get_nested('api.port', default=8000)
```

### 验证配置

```python
from config.loader import load_config, validate_config

config = load_config()

is_valid, errors = validate_config(config)

if not is_valid:
    for error in errors:
        print(f"配置错误: {error}")
```

### 加载自定义配置

```python
# 加载生产配置
config = load_config('config/production.yaml')

# 加载绝对路径配置
config = load_config('/path/to/my/config.yaml')
```

---

## 常见问题

### Q1: 配置加载失败，提示环境变量未设置

**错误信息**:
```
ConfigError: 环境变量 GOOGLE_CLOUD_PROJECT 未设置。
请在 .env 文件或环境中设置此变量。
```

**解决方案**:
1. 确认已创建 `.env` 文件：
   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env` 文件，设置必需的环境变量：
   ```bash
   GOOGLE_CLOUD_PROJECT=your-project-id
   ```

3. 运行验证脚本检查：
   ```bash
   python scripts/validate_config.py
   ```

### Q2: 如何在不同环境使用不同配置？

**方法 1**: 使用 `user.yaml`

```bash
# 开发环境
# config/user.yaml
api:
  reload: true
logging:
  level: DEBUG
```

**方法 2**: 创建多个配置文件

```bash
# config/development.yaml
# config/production.yaml

# 加载时指定
config = load_config('config/production.yaml')
```

**方法 3**: 使用环境变量

```bash
# .env.development
DEBUG=true
LOG_LEVEL=DEBUG

# .env.production
DEBUG=false
LOG_LEVEL=INFO
```

### Q3: 配置文件中的路径是相对还是绝对？

配置文件中的路径默认是**相对于项目根目录**的相对路径。

```yaml
paths:
  input_data: data/conversations/  # 相对路径
```

如果需要使用绝对路径，直接写完整路径：

```yaml
paths:
  input_data: /absolute/path/to/data/
```

### Q4: 如何临时覆盖某个配置？

```python
from config.loader import load_config

config = load_config()

# 临时修改
config.api.port = 9000
config.logging.level = 'DEBUG'

# 使用修改后的配置
# ...
```

---

## 配置文件清单

```
config/
├── default.yaml     # 默认配置（提交到 Git）
├── user.yaml        # 用户配置（不提交到 Git）
├── loader.py        # 配置加载器
└── README.md        # 本文档
```

---

## 相关文档

- [快速开始](../docs/quickstart.md)
- [环境变量配置](../.env.example)
- [配置验证](../scripts/validate_config.py)

---

返回 [主文档](../README.md)
