# WeMemory 脚本工具

本目录包含 WeMemory 项目的实用脚本工具。

---

## 核心脚本

### 1. run_pipeline.py

**功能**: Pipeline 主控脚本，执行端到端数据处理流程

**支持的步骤**:
- `data_cleaning` - 数据清洗
- `embedding` - 向量生成
- `knowledge_extraction` - 知识抽取
- `graph_building` - 图谱构建

**使用方法**:
```bash
# 执行特定步骤
python scripts/run_pipeline.py --step data_cleaning

# 执行全流程
python scripts/run_pipeline.py --all

# 从头开始（清除检查点）
python scripts/run_pipeline.py --step data_cleaning --fresh

# 查看当前进度
python scripts/run_pipeline.py --status

# 清除所有检查点
python scripts/run_pipeline.py --clear
```

**详细文档**: [pipeline/README.md](../pipeline/README.md)

---

### 2. validate_chatlab_format.py

**功能**: 验证 ChatLab 格式的对话数据

**使用方法**:
```bash
# 验证单个文件
python scripts/validate_chatlab_format.py data/conversations/chat_data_filtered/张三.json

# 验证整个目录
python scripts/validate_chatlab_format.py data/conversations/chat_data_filtered/

# 静默模式（只输出错误）
python scripts/validate_chatlab_format.py data/ --quiet
```

**检查项目**:
- JSON 格式正确性
- 必需字段完整性
- 时间戳格式
- 消息类型有效性
- 发送者信息

**详细说明**: [examples/data_samples/README.md](../examples/data_samples/README.md)

---

### 3. validate_config.py

**功能**: 验证配置文件和环境变量

**使用方法**:
```bash
# 基本验证
python scripts/validate_config.py

# 包含 API 连接测试
python scripts/validate_config.py --check-api
```

**检查项目**:
- 环境变量设置
- 配置文件结构
- 必需路径存在
- Google Cloud 配置（可选）
- API 连接测试（可选）

**详细文档**: [config/README.md](../config/README.md)

---

### 4. clean_conversation.py

**功能**: 清洗对话数据

**使用方法**:
```bash
# 清洗单个文件
python scripts/clean_conversation.py \
    --input data/conversations/raw/张三.json \
    --output data/conversations/cleaned/张三.json

# 批量清洗目录
python scripts/clean_conversation.py \
    --input data/conversations/raw/ \
    --output data/conversations/cleaned/

# 使用自定义配置
python scripts/clean_conversation.py \
    --input data/conversations/raw/ \
    --output data/conversations/cleaned/ \
    --config config/custom.yaml
```

**清洗策略**:
1. 移除系统消息
2. 去除重复消息
3. 分割长会话
4. 质量评分过滤
5. 最小消息数过滤

**详细文档**: [docs/data-cleaning.md](../docs/data-cleaning.md)

---

### 5. evaluate_data_quality.py

**功能**: 评估对话数据质量

**使用方法**:
```bash
# 评估单个文件
python scripts/evaluate_data_quality.py data/conversations/cleaned/张三.json

# 评估整个目录
python scripts/evaluate_data_quality.py data/conversations/cleaned/

# 对比清洗前后
python scripts/evaluate_data_quality.py \
    data/conversations/cleaned/ \
    --before data/conversations/raw/
```

**评估维度**:
- 平均消息长度
- 发送者多样性
- 时间跨度
- 内容比率（文本 vs 系统消息）
- 综合质量分（0-1）

**详细说明**: [docs/data-cleaning.md](../docs/data-cleaning.md)

---

### 6. start_api.py

**功能**: 启动 WeMemory API 服务

**使用方法**:
```bash
# 默认启动（localhost:8000）
python scripts/start_api.py

# 自定义端口
python scripts/start_api.py --port 8080

# 生产模式
python scripts/start_api.py --host 0.0.0.0 --port 8000

# 启用热重载（开发模式）
python scripts/start_api.py --reload
```

**预检查项**:
- 向量库文件存在
- 配置文件有效
- 环境变量设置

**详细文档**: [docs/api-service.md](../docs/api-service.md)

---

### 7. generate_embeddings.py

**功能**: 生成对话向量库

**使用方法**:
```bash
# 使用默认配置
python scripts/generate_embeddings.py

# 指定输入/输出目录
python scripts/generate_embeddings.py \
    --input data/conversations/cleaned/ \
    --output vector_stores/conversations/
```

**说明**: 此脚本是早期版本，建议使用新的 Pipeline 系统：

```bash
# 推荐使用 Pipeline
python scripts/run_pipeline.py --step embedding
```

**详细文档**: [docs/embedding.md](../docs/embedding.md)

---

## 辅助脚本

### start_embedding.bat

Windows 批处理脚本，用于快速启动 embedding 生成。

**使用方法**:
```batch
# Windows 命令行
start_embedding.bat
```

---

## 脚本开发指南

### 创建新脚本

1. 在 `scripts/` 目录创建脚本文件
2. 添加 shebang: `#!/usr/bin/env python3`
3. 使用 argparse 处理命令行参数
4. 添加详细的帮助信息
5. 使用项目配置系统（`config.loader`）

**示例**:
```python
#!/usr/bin/env python3
"""
我的新脚本

功能说明...
"""
import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.loader import load_config

def main():
    parser = argparse.ArgumentParser(
        description='我的新脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='输入文件或目录'
    )

    args = parser.parse_args()

    # 加载配置
    config = load_config()

    # 脚本逻辑...

if __name__ == '__main__':
    main()
```

### 使脚本可执行

```bash
# Linux/Mac
chmod +x scripts/my_script.py

# Windows
# 不需要特殊权限
```

---

## 常用工作流

### 从零开始

```bash
# 1. 验证配置
python scripts/validate_config.py

# 2. 验证数据格式
python scripts/validate_chatlab_format.py data/conversations/chat_data_filtered/

# 3. 数据清洗
python scripts/run_pipeline.py --step data_cleaning

# 4. 生成向量库
python scripts/run_pipeline.py --step embedding

# 5. 启动 API
python scripts/start_api.py
```

### 数据质量评估

```bash
# 评估原始数据
python scripts/evaluate_data_quality.py data/conversations/raw/

# 清洗数据
python scripts/clean_conversation.py \
    --input data/conversations/raw/ \
    --output data/conversations/cleaned/

# 对比清洗效果
python scripts/evaluate_data_quality.py \
    data/conversations/cleaned/ \
    --before data/conversations/raw/
```

### 增量更新

```bash
# 清洗新数据
python scripts/clean_conversation.py \
    --input data/conversations/new/ \
    --output data/conversations/cleaned/

# 增量生成向量（从检查点恢复）
python scripts/run_pipeline.py --step embedding
```

---

## 故障排查

### 配置问题

```bash
# 检查配置
python scripts/validate_config.py --check-api
```

常见错误:
- `GOOGLE_CLOUD_PROJECT` 未设置
- `GOOGLE_APPLICATION_CREDENTIALS` 路径错误
- API 权限不足

**解决方案**: 查看 [config/README.md](../config/README.md)

### 数据格式问题

```bash
# 验证数据格式
python scripts/validate_chatlab_format.py data/
```

常见错误:
- 时间戳格式错误
- 缺少必需字段
- 消息类型无效

**解决方案**: 查看 [examples/data_samples/README.md](../examples/data_samples/README.md)

### Pipeline 错误

```bash
# 查看 Pipeline 状态
python scripts/run_pipeline.py --status

# 清除检查点重新开始
python scripts/run_pipeline.py --step data_cleaning --fresh
```

**解决方案**: 查看 [pipeline/README.md](../pipeline/README.md)

### API 启动失败

```bash
# 检查向量库
ls -lh vector_stores/conversations/embeddings.pkl

# 检查配置
python scripts/validate_config.py
```

常见错误:
- 向量库文件不存在
- 端口被占用
- 内存不足

**解决方案**: 查看 [docs/api-service.md](../docs/api-service.md)

---

## 参考文档

### 系统文档
- [快速开始](../docs/quickstart.md)
- [配置系统](../config/README.md)
- [Pipeline 框架](../pipeline/README.md)

### 功能文档
- [数据导出](../docs/data-export.md)
- [数据清洗](../docs/data-cleaning.md)
- [Embedding 生成](../docs/embedding.md)
- [API 服务](../docs/api-service.md)

### 示例代码
- [使用示例](../examples/README.md)
- [数据样例](../examples/data_samples/README.md)

---

返回 [主文档](../README.md)
