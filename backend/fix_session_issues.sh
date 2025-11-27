#!/bin/bash

# 快速修复脚本 - 解决Session创建和代码拉取问题

echo "🔧 修复Git配置和Workspace问题..."

# 1. 设置Git HTTP/1.1（解决HTTP/2 framing问题）
echo "设置Git HTTP/1.1..."
git config --global http.version HTTP/1.1
echo "✅ Git配置已更新"

# 2. 确保workspace目录存在
echo "检查workspace目录..."
mkdir -p workspaces
echo "✅ Workspace目录已就绪"

# 3. 清理旧的失败session工作目录
echo "清理失败的session工作目录..."
find workspaces/ -maxdepth 1 -type d -empty -name "*-*" -exec rmdir {} + 2>/dev/null || true
echo "✅ 已清理空目录"

# 4. 测试Git clone是否正常
echo "测试Git clone功能..."
TEST_DIR="workspaces/test-git-$(date +%s)"
mkdir -p "$TEST_DIR"
if git clone https://github.com/1723229/wegent-test.git "$TEST_DIR" &>/dev/null; then
    echo "✅ Git clone测试成功"
    rm -rf "$TEST_DIR"
else
    echo "❌ Git clone仍然失败，请检查网络连接"
    rm -rf "$TEST_DIR"
fi

echo ""
echo "🎉 修复完成！请重启后端服务，然后："
echo "1. 重新打开前端页面 http://localhost:5173"
echo "2. 尝试创建新的session"
echo "3. 选择仓库并等待代码拉取完成"
echo ""
echo "📋 如果还有问题，请检查："
echo "- 网络连接是否正常"
echo "- GitHub token是否有效"
echo "- 仓库是否为公开或有访问权限"