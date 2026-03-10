# 贡献指南

## 分支管理

本项目采用双分支开发模式：

### 分支说明

- **`main`** - 稳定分支
  - 包含经过测试、可直接使用的代码
  - 所有功能都已验证通过
  - 文档与代码保持同步
  - 用户应该 clone 这个分支

- **`dev`** - 开发分支
  - 用于日常开发和测试
  - 包含最新的功能和改进
  - 可能存在未完成的功能
  - 仅供开发者使用

### 开发流程

#### 1. 日常开发

```bash
# 切换到 dev 分支
git checkout dev

# 拉取最新代码
git pull origin dev

# 进行开发...
# 修改代码、测试功能

# 提交更改
git add .
git commit -m "feat: 添加新功能"
git push origin dev
```

#### 2. 合并到 main（发布稳定版本）

当 dev 分支的功能开发完成并充分测试后：

```bash
# 切换到 main 分支
git checkout main

# 合并 dev 分支
git merge dev

# 推送到远程
git push origin main
```

#### 3. 切换分支

```bash
# 查看当前分支
git branch

# 切换到开发分支
git checkout dev

# 切换到稳定分支
git checkout main
```

### Commit 规范

使用语义化的 commit message：

- `feat:` - 新功能
- `fix:` - Bug 修复
- `docs:` - 文档更新
- `refactor:` - 代码重构
- `test:` - 测试相关
- `chore:` - 构建/工具相关

示例：
```bash
git commit -m "feat: add triplet search API endpoint"
git commit -m "fix: resolve metadata timestamp compatibility issue"
git commit -m "docs: update cost analysis in README"
```

## 开发建议

### 测试环境

在 dev 分支开发时：

1. **使用测试数据**：放在 `examples/data_samples/` 目录
2. **检查点管理**：开发时使用 `--fresh` 清除旧检查点
3. **API 测试**：使用小规模数据验证功能

### 代码质量

- 保持代码简洁，避免过度设计
- 添加必要的注释（中文）
- 确保错误处理完善
- 测试通过后再合并到 main

### 文档同步

功能开发完成后，确保更新相关文档：

- `README.md` - 主要功能说明
- 模块 `README.md` - 具体模块文档
- `CHANGELOG.md` - 版本变更记录

## 问题反馈

遇到问题请在 [GitHub Issues](https://github.com/mixuechu/WeMemory/issues) 提交。

---

**Happy Coding! 🚀**
