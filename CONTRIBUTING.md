# 贡献指南

感谢您考虑为 WeMemory 做出贡献！我们欢迎所有形式的贡献，包括但不限于：

- 🐛 报告 Bug
- 💡 提出新功能建议
- 📝 改进文档
- 🔧 提交代码优化
- ✅ 增加测试用例

---

## 行为准则

本项目遵循 [贡献者公约](https://www.contributor-covenant.org/)。参与本项目即表示您同意遵守其条款。

### 基本原则

- 尊重所有贡献者
- 接受建设性批评
- 关注对项目最有利的事情
- 对其他社区成员表现出同理心

---

## 如何贡献

### 报告 Bug

在提交 Bug 报告之前，请：

1. **搜索现有 Issues**：检查是否已有人报告了相同问题
2. **使用最新版本**：确认问题在最新版本中仍然存在
3. **提供详细信息**：包括复现步骤、预期行为、实际行为

**Bug 报告模板**：

```markdown
## Bug 描述
清晰简洁地描述问题

## 复现步骤
1. 执行命令 '...'
2. 查看 '...'
3. 出现错误 '...'

## 预期行为
描述您期望发生什么

## 实际行为
描述实际发生了什么

## 环境信息
- 操作系统: [例如 macOS 13.0]
- Python 版本: [例如 3.10.5]
- WeMemory 版本: [例如 v1.0.0]

## 日志输出
```
粘贴相关日志
```

## 截图（如适用）
添加截图以帮助解释问题
```

[创建 Bug 报告](https://github.com/mixuechu/WeMemory/issues/new?template=bug_report.md)

### 提出功能建议

我们欢迎新功能建议！请：

1. **搜索现有 Issues**：避免重复建议
2. **描述用例**：说明为什么需要这个功能
3. **考虑替代方案**：是否有其他解决方法

**功能建议模板**：

```markdown
## 功能描述
清晰简洁地描述您想要的功能

## 动机
解释为什么需要这个功能，它解决了什么问题

## 建议的解决方案
描述您希望如何实现这个功能

## 替代方案
描述您考虑过的其他解决方案

## 附加信息
添加任何其他相关信息或截图
```

[提出功能建议](https://github.com/mixuechu/WeMemory/issues/new?template=feature_request.md)

### 改进文档

文档改进包括：

- 修正错别字和语法错误
- 添加示例代码
- 改进现有文档的清晰度
- 翻译文档（中文/英文）

**提交文档 PR**：

1. Fork 仓库
2. 在 `docs/` 目录中进行修改
3. 提交 Pull Request

### 提交代码

#### 开发流程

1. **Fork 仓库**

```bash
# Fork 后克隆到本地
git clone https://github.com/YOUR_USERNAME/WeMemory.git
cd WeMemory
```

2. **创建分支**

```bash
# 创建功能分支
git checkout -b feature/your-feature-name

# 或创建修复分支
git checkout -b fix/your-bug-fix
```

3. **进行开发**

```bash
# 安装依赖
pip install -r requirements.txt

# 运行测试
python -m pytest tests/

# 确保代码通过测试
```

4. **提交更改**

```bash
git add .
git commit -m "feat: add your feature description"

# 提交信息格式：
# feat: 新功能
# fix: Bug 修复
# docs: 文档更新
# style: 代码格式调整
# refactor: 代码重构
# test: 测试相关
# chore: 构建/工具相关
```

5. **推送到 GitHub**

```bash
git push origin feature/your-feature-name
```

6. **创建 Pull Request**

- 访问您的 Fork 仓库
- 点击 "Compare & pull request"
- 填写 PR 描述
- 提交 PR

#### 代码规范

**Python 代码风格**：

- 遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- 使用 4 空格缩进
- 最大行长 100 字符
- 使用类型注解

**示例**：

```python
from typing import List, Dict

def search_memories(
    query: str,
    top_k: int = 5,
    filters: Dict[str, any] = None
) -> List[Dict]:
    """
    搜索记忆

    Args:
        query: 查询文本
        top_k: 返回结果数量
        filters: 过滤条件

    Returns:
        搜索结果列表
    """
    # 实现...
    pass
```

**代码检查工具**：

```bash
# 格式化代码
black .

# 检查代码风格
flake8 .

# 类型检查
mypy .
```

#### 测试要求

所有代码更改必须包含测试：

```python
# tests/test_your_feature.py

def test_your_feature():
    """测试您的功能"""
    result = your_function("test input")
    assert result == "expected output"
```

运行测试：

```bash
# 运行所有测试
python -m pytest

# 运行特定测试
python -m pytest tests/test_your_feature.py

# 查看覆盖率
python -m pytest --cov=.
```

#### Pull Request 检查清单

提交 PR 前，请确认：

- [ ] 代码通过所有测试
- [ ] 添加了必要的测试用例
- [ ] 更新了相关文档
- [ ] 提交信息清晰明确
- [ ] 代码符合项目风格
- [ ] 没有引入新的依赖（或已说明原因）

---

## Pull Request 流程

1. **审查**：维护者会审查您的 PR
2. **反馈**：可能会要求进行修改
3. **更新**：根据反馈更新代码
4. **合并**：通过审查后会被合并

### PR 审查标准

- ✅ 功能正确实现
- ✅ 代码质量良好
- ✅ 测试覆盖充分
- ✅ 文档完整准确
- ✅ 无明显性能问题

---

## 开发环境设置

### 必需工具

- Python 3.8+
- Git
- virtualenv 或 conda

### 安装开发依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖

# 安装 pre-commit hooks
pre-commit install
```

### 配置 IDE

**VSCode 配置** (`.vscode/settings.json`):

```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "editor.formatOnSave": true
}
```

---

## 项目结构

```
WeMemory/
├── api/              # API 服务
├── embedding/        # Embedding 模块
├── retrieval/        # 检索模块
├── knowledge_graph/  # 知识图谱模块
├── data_loader/      # 数据加载模块
├── tests/            # 测试代码
├── docs/             # 文档
└── examples/         # 示例代码
```

---

## 常见问题

### Q: 我不会 Python，可以贡献吗？

可以！您可以：
- 改进文档
- 报告 Bug
- 提出功能建议
- 帮助翻译

### Q: 我的 PR 多久会被审查？

通常在 1-3 个工作日内。如果超过一周没有回复，请友好地提醒我们。

### Q: 我可以一次提交多个功能吗？

建议每个 PR 只包含一个功能或修复，这样更容易审查和合并。

---

## 获取帮助

- 📚 查阅[完整文档](README.md)
- 💬 在 [Discussions](https://github.com/mixuechu/WeMemory/discussions) 提问
- 📧 联系维护者

---

## 许可证

通过贡献，您同意您的贡献将按照 [MIT License](LICENSE) 进行许可。

---

感谢您的贡献！🎉
