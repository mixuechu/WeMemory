# AI自动生成实体合并建议

## 📋 功能说明

这个脚本会自动分析所有138个对话的实体，使用Vertex AI Claude API生成合并建议。

**处理内容：**
- ✅ 75个已编辑的对话 → 建议进一步合并
- ✅ 63个未编辑的对话 → 生成初始合并建议
- 📊 总计5648个实体

## 🚀 使用方法

### 方法1: 使用启动脚本（推荐）

```bash
cd /Users/mimimi/Desktop/personal_projects/wechat_memory/wechat_memory_curated
./start_merge_suggestions.sh
```

脚本会在后台运行，你可以关闭终端窗口去睡觉了 😴

### 方法2: 手动运行

```bash
cd /Users/mimimi/Desktop/personal_projects/wechat_memory/wechat_memory_curated
python3 generate_merge_suggestions.py
```

## 📊 查看进度

**实时查看日志：**
```bash
tail -f merge_suggestions.log
```

**查看进度文件：**
```bash
cat merge_suggestions_progress.json
```

进度文件会每10个对话保存一次，如果中断可以恢复。

## ⏱️ 预计时间

- 每个对话约需5-10秒
- 138个对话预计**2-3小时**
- 脚本会自动保存进度，可随时中断和恢复

## 📁 输出文件

完成后会生成以下文件：

1. **ai_merge_suggestions.json** - 最终的合并建议
   ```json
   {
     "metadata": {...},
     "suggestions": {
       "对话名": {
         "merge_suggestions": [
           {
             "final_name": "张涛",
             "entities": ["张涛", "涛", "小涛"],
             "reason": "同一个人的不同称呼"
           }
         ]
       }
     }
   }
   ```

2. **merge_suggestions_progress.json** - 进度文件
3. **merge_suggestions.log** - 运行日志

## 🔍 查看结果

醒来后查看结果：

```bash
# 查看完成状态
cat merge_suggestions_progress.json | grep processed

# 查看总共生成了多少建议
cat ai_merge_suggestions.json | grep -c "final_name"

# 查看有没有错误
cat ai_merge_suggestions.json | grep -A 5 "errors"
```

## 🛠️ 如果需要重新开始

```bash
# 删除进度文件重新开始
rm merge_suggestions_progress.json
./start_merge_suggestions.sh
```

## 📝 下一步

明天醒来后：
1. 打开 `entity_editor_fixed.html`
2. 加载 `ai_merge_suggestions.json` 查看建议
3. 逐个审核并应用合并建议

## ⚠️ 注意事项

- 脚本会调用Vertex AI API，会产生费用（预计$1-2）
- 如果中断，再次运行会自动恢复进度
- 不要删除 `merge_suggestions_progress.json` 除非想重新开始

---

**祝你睡个好觉！明天醒来就有AI给你准备好的合并建议了！** 😴✨
