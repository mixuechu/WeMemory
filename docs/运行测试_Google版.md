# 运行测试 - Google Vertex AI版本

## ✅ 优势

- **免费额度**: Google提供免费的Vertex AI额度
- **无需Docker**: 使用本地文件存储
- **完全免费**: 不需要OpenAI账号

## 第1步：安装依赖

```bash
pip install google-cloud-aiplatform qdrant-client python-dotenv
```

## 第2步：直接运行

```bash
cd "D:\导出聊天记录excel"
python test_embedding_google.py
```

就这么简单！

## 脚本会自动完成

1. ✅ 使用您的Google凭证初始化Vertex AI
2. ✅ 加载"成都乖巧萌"对话（8.5万条消息）
3. ✅ 切分为约2000个会话片段
4. ✅ 生成增强文本（时间、参与者、对话内容）
5. ✅ 使用Google textembedding-gecko模型生成embeddings（768维）
6. ✅ 存储到本地向量数据库（./qdrant_local_storage）
7. ✅ 运行3个检索测试

## 预计耗时

- 会话切分: ~10秒
- Embedding生成: ~5-8分钟（Google API稍慢但免费）
- 总计: **10分钟左右**

## 成本

**完全免费！** 🎉

Google Vertex AI textembedding-gecko模型在免费额度内。

## 测试查询

脚本会自动运行3个测试：
1. "房子装修相关的讨论"
2. "旅行 出去玩"（限定2023年）
3. "工作 项目"（限定参与者）

每个查询返回Top 5最相关的会话片段。

## 查看结果

运行后会生成：
- `qdrant_local_storage/` - 向量数据库（持久化）
- `sample_sessions.json` - 前10个会话片段示例

可以查看`sample_sessions.json`了解增强后的文本格式。
