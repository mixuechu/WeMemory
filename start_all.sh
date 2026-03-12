#!/bin/bash
# 一键启动 WeMemory 完整服务
# 包括：后端API + 前端Next.js

echo "=========================================="
echo "  WeMemory 完整服务启动"
echo "=========================================="
echo ""

# 检查是否在正确的目录
if [ ! -f "api/main.py" ]; then
    echo "❌ 错误：请在项目根目录运行此脚本"
    echo "   cd $(pwd)"
    exit 1
fi

# 检查依赖
echo "📋 检查依赖..."

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装"
    exit 1
fi

echo "✅ 依赖检查通过"
echo ""

# 启动后端API
echo "🚀 启动后端API服务..."
echo "   位置: http://localhost:8000"
echo "   文档: http://localhost:8000/docs"
echo ""

cd api
python3 main.py &
BACKEND_PID=$!
cd ..

# 等待后端启动
echo "⏳ 等待后端启动（5秒）..."
sleep 5

# 检查后端是否启动成功
if curl -s http://localhost:8000/api/health > /dev/null; then
    echo "✅ 后端启动成功"
else
    echo "⚠️  后端可能未完全启动，继续尝试..."
fi
echo ""

# 启动前端
echo "🚀 启动前端Next.js服务..."
echo "   位置: http://localhost:3000"
echo "   聊天: http://localhost:3000/chat"
echo ""

cd Meng
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "=========================================="
echo "  ✅ 服务启动完成！"
echo "=========================================="
echo ""
echo "📍 服务地址:"
echo "   - 后端API:  http://localhost:8000"
echo "   - API文档:  http://localhost:8000/docs"
echo "   - 前端界面: http://localhost:3000"
echo "   - 聊天页面: http://localhost:3000/chat"
echo ""
echo "🛠️  可用工具:"
echo "   - search_knowledge          (搜索聊天记忆)"
echo "   - query_person_relationships (查询人物关系)"
echo ""
echo "💡 测试示例:"
echo "   - \"赵萌是谁？\""
echo "   - \"我的家人有谁？\""
echo "   - \"赵萌的同事是谁？\""
echo ""
echo "⏹️  停止服务: Ctrl+C"
echo "=========================================="
echo ""

# 等待用户中断
wait $BACKEND_PID $FRONTEND_PID
