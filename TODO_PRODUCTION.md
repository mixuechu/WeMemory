# WeMemory 生产就绪 TODO 清单

**目标**: 将项目打磨为真正可用的端到端记忆系统

**原则**:
- 用户开箱即用（配置完即可运行）
- 流程分段可控（允许人工审核）
- 文档详略得当（关键步骤详细，外部依赖简洁）
- 代码健壮可靠（日志、断点续传、错误处理）

---

## 🔴 P0 - 核心功能缺失（必须完成）

### 1. 数据导出与格式规范

**当前问题**:
- [ ] WeFlow使用说明过于简略，没有具体操作步骤
- [ ] 未指定导出格式（ChatLab格式）
- [ ] 缺少真实数据样例
- [ ] 缺少数据格式验证脚本

**待完成**:
```
□ 1.1 补充 docs/data-export.md
  - 添加WeFlow详细操作步骤（带截图）
  - 明确指出选择"ChatLab格式"导出
  - 说明为什么选择这个格式（vs 其他格式）

□ 1.2 提供数据样例
  - 从真实数据中提取1-2个对话样例（脱敏）
  - 放到 examples/data_samples/chatlab_format_example.json
  - 在文档中引用样例

□ 1.3 创建数据验证脚本
  - scripts/validate_chatlab_format.py
  - 检查必需字段、数据类型
  - 给出友好的错误提示
```

**负责模块**: `docs/`, `examples/`, `scripts/`

---

### 2. 端到端数据处理Pipeline

**当前问题**:
- [ ] 数据处理流程分散在多个脚本中
- [ ] 没有统一的日志系统
- [ ] 缺少断点续传机制
- [ ] 缺少进度监控
- [ ] 错误处理不完善

**待完成**:
```
□ 2.1 设计Pipeline架构
  - 明确分段：数据准备 → 向量化 → 知识抽取 → 图谱构建 → API启动
  - 确定哪些步骤可自动化，哪些需人工审核
  - 设计各阶段的输入/输出格式

□ 2.2 创建统一的Pipeline框架
  - pipeline/base.py - 基础Pipeline类
    - 统一的日志接口（使用logging模块）
    - 进度保存机制（checkpoint）
    - 断点续传支持
    - 错误处理和重试
  - pipeline/config.py - 配置管理

□ 2.3 实现各阶段Pipeline
  - pipeline/data_cleaning.py - 数据清洗
    - 过滤系统消息
    - 去重
    - 质量评估
  - pipeline/embedding.py - 向量化
    - 对话向量生成
    - 批量处理
    - API限流处理
  - pipeline/knowledge_extraction.py - 知识抽取
    - 实体/事件/关系抽取
    - 批量处理
    - 失败重试
  - pipeline/graph_building.py - 图谱构建
    - 三元组生成
    - 关系剪枝
    - 三元组向量化

□ 2.4 创建主控脚本
  - scripts/run_pipeline.py
    - 支持分步执行（--step data_cleaning）
    - 支持全流程执行（--all）
    - 显示当前进度
    - 友好的命令行界面（使用click或argparse）

□ 2.5 日志系统
  - 统一的日志格式
  - 按级别输出（INFO/WARNING/ERROR）
  - 日志文件按日期分割
  - 保存到 logs/ 目录

□ 2.6 进度监控
  - 使用tqdm显示进度条
  - 保存checkpoint到 .checkpoints/ 目录
  - 支持从中断点恢复
```

**负责模块**: 新建 `pipeline/`，更新 `scripts/`

---

### 3. 统一配置管理

**当前问题**:
- [ ] 配置分散在代码中
- [ ] .env 文件管理混乱
- [ ] API keys 硬编码
- [ ] 缺少配置验证

**待完成**:
```
□ 3.1 创建配置文件
  - config/default.yaml - 默认配置
    ```yaml
    # Google Vertex AI 配置
    vertex_ai:
      project_id: ${GOOGLE_CLOUD_PROJECT}
      region: us-central1
      embedding_model: text-multilingual-embedding-002
      extraction_model: claude-3-5-sonnet-20241022

    # 数据路径
    paths:
      input_data: data/conversations/chat_data_filtered/
      vector_stores: vector_stores/
      knowledge_graph: data/knowledge_graph/
      checkpoints: .checkpoints/
      logs: logs/

    # Pipeline 配置
    pipeline:
      data_cleaning:
        min_messages: 3
        max_time_gap_minutes: 30
      embedding:
        batch_size: 32
        retry_attempts: 3
      knowledge_extraction:
        batch_size: 10
        confidence_threshold: 0.8
      graph_building:
        prune_relations: true
        valuable_relations:
          - 家庭成员
          - 同事
          - 朋友

    # API 配置
    api:
      host: 0.0.0.0
      port: 8000
      reload: false
    ```

□ 3.2 创建配置加载模块
  - config/loader.py
    - 加载YAML配置
    - 环境变量替换（${VAR}）
    - 配置验证
    - 配置合并（default + user override）

□ 3.3 更新 .env.example
  - 明确所有必需的环境变量
  - 添加详细注释
  - 提供获取方式说明

□ 3.4 配置验证脚本
  - scripts/validate_config.py
    - 检查必需配置项
    - 验证API credentials
    - 测试API连接
```

**负责模块**: `config/`

---

### 4. 数据清洗策略实现

**当前问题**:
- [ ] docs/data-cleaning.md 文档缺失
- [ ] 没有自动化的清洗脚本
- [ ] 筛选标准不明确
- [ ] 质量评估缺失

**待完成**:
```
□ 4.1 创建 docs/data-cleaning.md
  - 清洗目标（过滤无价值对话）
  - 筛选标准
    - 消息数量阈值（< 3条）
    - 系统消息过滤
    - 重复对话去重
    - 时间跨度过短
  - 质量评估指标
  - 清洗效果统计

□ 4.2 实现清洗脚本
  - data_loader/cleaner.py
    - filter_system_messages()
    - remove_duplicates()
    - filter_by_quality()
    - split_sessions()

□ 4.3 质量评估工具
  - scripts/evaluate_data_quality.py
    - 统计对话分布
    - 评估消息质量
    - 生成清洗报告
```

**负责模块**: `docs/`, `data_loader/`, `scripts/`

---

### 5. API服务完善

**当前问题**:
- [ ] docs/api-service.md 缺失
- [ ] 启动条件不明确（需要哪些向量库）
- [ ] 使用文档不完善
- [ ] 缺少端到端测试用例

**待完成**:
```
□ 5.1 创建 docs/api-service.md
  - 启动前置条件
    - 对话向量库已生成
    - 知识图谱向量库已生成（可选）
  - 启动步骤
    - 检查向量库
    - 配置环境变量
    - 启动命令
  - API使用指南
    - 各端点详细说明
    - 请求/响应示例
    - 参数说明
  - 测试方法
  - 故障排查

□ 5.2 API健康检查
  - api/routers/health.py
    - GET /health - 基础健康检查
    - GET /health/detailed - 详细状态
      - 向量库状态
      - 索引状态
      - 内存使用

□ 5.3 API启动脚本
  - scripts/start_api.py
    - 启动前检查向量库
    - 检查配置
    - 启动服务
    - 显示访问地址

□ 5.4 端到端测试
  - tests/test_api_e2e.py
    - 测试各个API端点
    - 测试真实查询
    - 性能测试
```

**负责模块**: `docs/`, `api/`, `scripts/`, `tests/`

---

## 🟡 P1 - 重要优化（建议完成）

### 6. 实体合并工作流

**当前问题**:
- [ ] 实体编辑器使用不清晰
- [ ] 合并建议生成流程缺失
- [ ] 人工审核步骤不明确

**待完成**:
```
□ 6.1 文档实体合并流程
  - 在 docs/knowledge-graph.md 中添加详细步骤
  - 实体编辑器使用指南
  - 合并建议审核标准

□ 6.2 合并建议生成脚本
  - knowledge_graph/generate_merge_suggestions.py
    - 基于AI的合并建议
    - 人工审核界面启动
    - 导出审核结果

□ 6.3 应用合并结果
  - knowledge_graph/apply_merges.py
    - 读取审核结果
    - 应用到知识图谱
    - 生成别名映射
```

**负责模块**: `docs/`, `knowledge_graph/`

---

### 7. 向量库管理

**当前问题**:
- [ ] 缺少向量库更新机制
- [ ] 缺少版本管理
- [ ] 缺少增量更新支持

**待完成**:
```
□ 7.1 向量库版本管理
  - 添加版本号到向量库文件名
  - 保存元数据（创建时间、对话数、模型版本）

□ 7.2 增量更新
  - 支持添加新对话
  - 支持更新现有对话
  - 支持删除对话

□ 7.3 向量库迁移工具
  - scripts/migrate_vector_store.py
    - 支持模型切换
    - 重新生成向量
```

**负责模块**: `retrieval/`, `scripts/`

---

### 8. 模块README完善

**当前问题**:
- [ ] Task #12 未完成
- [ ] 各模块README内容不一致
- [ ] 缺少使用示例

**待完成**:
```
□ 8.1 更新各模块README
  - api/README.md - API服务使用
  - embedding/README.md - Embedding模块
  - knowledge_graph/README.md - 知识图谱模块
  - data_loader/README.md - 数据加载
  - retrieval/README.md - 检索模块

□ 8.2 统一格式
  - 模块作用
  - 核心功能
  - 使用方法
  - API文档
  - 配置选项
  - 示例代码
```

**负责模块**: 各模块 `README.md`

---

### 9. 测试覆盖

**当前问题**:
- [ ] 单元测试缺失
- [ ] 集成测试不完善
- [ ] 缺少性能基准测试

**待完成**:
```
□ 9.1 单元测试
  - tests/test_data_loader.py
  - tests/test_embedding.py
  - tests/test_retrieval.py
  - tests/test_knowledge_graph.py

□ 9.2 集成测试
  - tests/test_pipeline_integration.py
    - 测试完整流程
    - 使用小数据集

□ 9.3 性能基准
  - tests/benchmark.py
    - 向量生成速度
    - 检索延迟
    - 内存占用
```

**负责模块**: `tests/`

---

## 🟢 P2 - 体验优化（可选完成）

### 10. 部署与运维

```
□ 10.1 Docker容器化
  - Dockerfile
  - docker-compose.yml
  - 镜像优化

□ 10.2 生产环境配置
  - 生产配置模板
  - 环境变量管理
  - 日志轮转

□ 10.3 监控和告警
  - Prometheus metrics
  - 健康检查
  - 告警规则
```

**负责模块**: 新建 `deploy/`

---

### 11. 用户体验优化

```
□ 11.1 CLI工具优化
  - 使用click美化命令行
  - 添加help信息
  - 交互式配置向导

□ 11.2 进度可视化
  - rich库美化输出
  - 实时进度显示
  - 彩色日志

□ 11.3 错误提示优化
  - 友好的错误消息
  - 提供解决建议
  - 常见问题FAQ
```

**负责模块**: `scripts/`, `pipeline/`

---

### 12. 性能优化

```
□ 12.1 并发处理
  - 批量API调用优化
  - 多线程/多进程支持
  - 内存管理优化

□ 12.2 缓存机制
  - Embedding结果缓存
  - 检索结果缓存
  - LRU缓存策略

□ 12.3 大规模数据支持
  - 分片处理
  - 流式处理
  - 增量更新
```

**负责模块**: `embedding/`, `retrieval/`, `pipeline/`

---

### 13. 安全与隐私

```
□ 13.1 数据脱敏
  - 敏感信息检测
  - 自动脱敏脚本
  - 脱敏验证

□ 13.2 安全存储
  - 加密存储建议
  - 访问控制
  - 备份策略

□ 13.3 API安全
  - API Key认证
  - 限流
  - HTTPS支持
```

**负责模块**: `utils/`, `api/`, `docs/`

---

## 📋 执行计划

### 第一阶段：核心功能完善（P0）

**Week 1-2**:
1. 数据导出规范（1.1-1.3）
2. 统一配置管理（3.1-3.4）
3. 数据清洗实现（4.1-4.3）

**Week 3-4**:
4. Pipeline框架搭建（2.1-2.3）
5. 主控脚本开发（2.4-2.6）

**Week 5-6**:
6. API服务完善（5.1-5.4）
7. 端到端测试

### 第二阶段：体验优化（P1）

**Week 7-8**:
1. 实体合并工作流（6.1-6.3）
2. 模块README完善（8.1-8.2）

**Week 9-10**:
3. 向量库管理（7.1-7.3）
4. 测试覆盖（9.1-9.3）

### 第三阶段：生产就绪（P2）

根据需求选择性完成。

---

## 📊 成功标准

完成后应达到：

- [ ] **新用户可在30分钟内完成配置**
- [ ] **端到端流程有清晰的步骤文档**
- [ ] **每个步骤有完善的日志和错误提示**
- [ ] **支持断点续传，中断后可恢复**
- [ ] **有真实数据样例和测试用例**
- [ ] **API服务开箱即用**
- [ ] **主要功能有测试覆盖**

---

## 🎯 当前优先级

**立即开始**:
1. 补充数据样例（从真实数据提取）
2. 创建统一配置文件
3. 设计Pipeline架构

**本周完成**:
- P0.1-P0.3（数据导出、配置、清洗）

**下周开始**:
- P0.2（Pipeline实现）

---

## 📝 笔记

- 假设用户使用Vertex AI（第一版）
- 流程分段执行，允许人工审核
- 文档详略得当，外部依赖简洁引用
- 代码健壮性优先于性能优化

---

**最后更新**: 2026-03-09
**负责人**: WeMemory Team
