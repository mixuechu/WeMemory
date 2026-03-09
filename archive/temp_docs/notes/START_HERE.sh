#!/bin/bash
# 开始生成AI合并建议 - 睡觉前运行这个脚本

cd /Users/mimimi/Desktop/personal_projects/wechat_memory/wechat_memory_curated

echo "==========================================="
echo "🌙 AI自动生成实体合并建议"
echo "==========================================="
echo ""
echo "📊 任务规模:"
echo "  - 138个对话"
echo "  - 5648个实体"
echo "  - 预计时间: 2-3小时"
echo ""
echo "💰 预计费用: ~\$1-2 (Vertex AI)"
echo ""

# 检查是否已有进度
if [ -f "merge_suggestions_progress.json" ]; then
    processed=$(cat merge_suggestions_progress.json | grep -o '"processed": [0-9]*' | grep -o '[0-9]*')
    echo "⚠️  发现进度文件: 已处理 $processed 个对话"
    echo ""
    read -p "是否继续之前的进度? (y/n): " continue_progress

    if [ "$continue_progress" != "y" ]; then
        echo "删除旧进度，重新开始..."
        rm -f merge_suggestions_progress.json
    fi
    echo ""
fi

# 询问使用哪个API
echo "选择API服务:"
echo "  1) Vertex AI (需要配置project ID)"
echo "  2) Anthropic API (需要API key)"
echo ""
read -p "选择 (1 或 2): " api_choice

if [ "$api_choice" = "1" ]; then
    # Vertex AI
    echo ""
    echo "请输入你的Vertex AI Project ID:"
    echo "(可以在https://console.cloud.google.com找到)"
    read -p "Project ID: " project_id

    if [ -z "$project_id" ]; then
        echo "❌ Project ID不能为空"
        exit 1
    fi

    export USE_VERTEX_AI=true
    export VERTEX_PROJECT=$project_id
    export VERTEX_REGION=us-east5

    echo "✓ 配置完成: Vertex AI ($project_id)"

elif [ "$api_choice" = "2" ]; then
    # Anthropic API
    echo ""
    echo "请输入你的Anthropic API Key:"
    read -p "API Key: " api_key

    if [ -z "$api_key" ]; then
        echo "❌ API Key不能为空"
        exit 1
    fi

    export USE_VERTEX_AI=false
    export ANTHROPIC_API_KEY=$api_key

    echo "✓ 配置完成: Anthropic API"

else
    echo "❌ 无效选择"
    exit 1
fi

echo ""
echo "==========================================="
echo "🚀 开始运行..."
echo "==========================================="
echo ""
echo "📝 日志文件: merge_suggestions.log"
echo "📊 进度文件: merge_suggestions_progress.json"
echo ""
echo "你可以:"
echo "  - 关闭这个终端窗口"
echo "  - 关机或睡觉"
echo "  - 明天查看结果"
echo ""
read -p "按回车键开始运行..."

# 后台运行
chmod +x generate_merge_suggestions_flexible.py
nohup python3 generate_merge_suggestions_flexible.py > merge_suggestions.log 2>&1 &

PID=$!
echo ""
echo "✅ 后台任务已启动 (PID: $PID)"
echo ""
echo "📖 查看实时日志:"
echo "   tail -f merge_suggestions.log"
echo ""
echo "🛑 停止任务 (如需要):"
echo "   kill $PID"
echo ""
echo "🎉 一切就绪！现在可以去睡觉了 😴"
echo ""
echo "明天醒来查看 ai_merge_suggestions.json"
echo "==========================================="
