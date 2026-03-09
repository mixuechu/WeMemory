#!/bin/bash
# 🌙 睡觉前运行这个脚本

cd /Users/mimimi/Desktop/personal_projects/wechat_memory/wechat_memory_curated

clear
echo "==========================================="
echo "🌙 AI自动生成实体合并建议"
echo "==========================================="
echo ""
echo "📊 任务规模:"
echo "  - 138个对话"
echo "  - 最大675个实体/对话"
echo "  - 实测速度: 30实体=36秒"
echo "  - 预计时间: 1.5-2小时"
echo ""
echo "💰 预计费用: ~\$2-3 (Gemini 2.5 Flash)"
echo ""
echo "🔑 配置: 从.env自动加载"
echo ""
echo "✨ 特性:"
echo "  - 自动过滤已排除的实体"
echo "  - 大量实体自动分批处理(每批250个)"
echo "  - 输出token限制: 64K"
echo "  - 每10个对话保存进度"
echo "  - 支持断点续传"
echo ""

# 检查是否已有进度
if [ -f "merge_suggestions_progress.json" ]; then
    processed=$(cat merge_suggestions_progress.json | grep -o '"processed": [0-9]*' | grep -o '[0-9]*')
    echo "⚠️  发现进度文件: 已处理 $processed 个对话"
    echo ""
    read -p "是否继续之前的进度? (y/n, 默认y): " continue_progress
    continue_progress=${continue_progress:-y}

    if [ "$continue_progress" != "y" ]; then
        echo "删除旧进度，重新开始..."
        rm -f merge_suggestions_progress.json
        rm -f ai_merge_suggestions.json
    fi
    echo ""
fi

echo "==========================================="
echo "🚀 准备启动..."
echo "==========================================="
echo ""
echo "脚本将在后台运行，你可以:"
echo "  ✓ 关闭这个终端窗口"
echo "  ✓ 关机或睡觉"
echo "  ✓ 明天查看结果"
echo ""
echo "📝 日志文件: merge_suggestions.log"
echo "📊 进度文件: merge_suggestions_progress.json"
echo ""
read -p "按回车键开始运行..."

# 后台运行
chmod +x run_merge_suggestions.py
nohup python3 run_merge_suggestions.py > merge_suggestions.log 2>&1 &

PID=$!
echo ""
echo "✅ 后台任务已启动 (PID: $PID)"
echo ""
echo "📖 查看实时日志:"
echo "   tail -f merge_suggestions.log"
echo ""
echo "📊 查看进度:"
echo "   cat merge_suggestions_progress.json | grep processed"
echo ""
echo "🛑 停止任务 (如需要):"
echo "   kill $PID"
echo ""
echo "==========================================="
echo "🎉 一切就绪！现在可以去睡觉了 😴"
echo "==========================================="
echo ""
echo "明天醒来查看:"
echo "  📁 ai_merge_suggestions.json"
echo ""
echo "晚安！🌙"
