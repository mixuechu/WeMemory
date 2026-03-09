# 🌙 睡觉前必读 - AI合并建议生成

## ✅ 已确认的关键点

###  1. **Token限制 - 已设置为最大值**
```python
"maxOutputTokens": 65536  # Gemini 2.5 Flash支持最大64K输出
```
- ✓ 输入token限制: 1M+ (充足)
- ✓ 输出token限制: 64K (最大值)

### 2. **大量实体处理方案 - 自动分批**
```python
BATCH_SIZE = 250  # 每批处理250个实体
```

**自动处理逻辑:**
- ✓ 自动过滤已排除的实体（excluded_entities）
- ✓ 如果剩余实体 > 250个，自动分批处理
- ✓ 每批独立调用API，最后合并所有建议
- ✓ 批次间延迟1秒，避免速率限制

**实际案例:**
- "妈"对话: 675个总实体
- 已排除: 假设100个
- 剩余: 575个 → 分3批处理（250+250+75）

## 📊 任务规模

```
总对话数: 138
平均实体数: 40.9
最大实体数: 675 ("妈"对话)

实测速度: 30个实体 = 36秒
超过250个实体的对话: ~5个（会自动分批，每批约4分钟）
预计总时间: 1.5-2小时 （已实测验证）
预计费用: $2-3

关键优化:
- ✓ Timeout已设置为300秒（5分钟/批）
- ✓ 每批250个实体，避免单批过大
```

## 🚀 启动方式

```bash
cd /Users/mimimi/Desktop/personal_projects/wechat_memory/wechat_memory_curated
./睡觉前运行.sh
```

## 📝 进度跟踪

- **进度文件**: `merge_suggestions_progress.json`
- **日志文件**: `merge_suggestions.log`
- **最终结果**: `ai_merge_suggestions.json`

**查看进度:**
```bash
tail -f merge_suggestions.log
cat merge_suggestions_progress.json | grep processed
```

## 🛡️ 安全保障

1. **断点续传**: 每10个对话保存进度，可随时中断和恢复
2. **错误处理**: API错误不会中断整个流程，错误会记录在errors数组
3. **批次失败**: 某一批失败不影响其他批次

## 明天醒来查看

```bash
cat ai_merge_suggestions.json
```

**数据结构:**
```json
{
  "metadata": {
    "total_conversations": 138,
    "processed": 138,
    "total_merge_groups": "...",
    "model": "gemini-2.5-flash"
  },
  "suggestions": {
    "对话名": {
      "entity_count": 575,  // 分析的实体数（排除excluded后）
      "total_entities": 675,  // 总实体数
      "excluded_count": 100,  // 已排除数
      "batches_processed": 3,  // 处理批次数
      "merge_suggestions": [...]
    }
  }
}
```

## ✅ 准备就绪

- [x] Token限制设置为最大 (64K)
- [x] 自动分批处理大量实体 (250/批)
- [x] 自动过滤已排除实体
- [x] 断点续传支持
- [x] 错误处理
- [x] 进度跟踪

**可以安心去睡了！** 🌙😴
