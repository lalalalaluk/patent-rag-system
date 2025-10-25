#!/bin/bash

# VPS 部署腳本
# 用於在 VPS 上重新構建和啟動服務

echo "🚀 開始 VPS 部署流程"
echo "================================"

# 1. 停止所有容器
echo "📦 步驟 1: 停止現有容器"
docker-compose -f docker-compose.prod.yml down
echo "✅ 容器已停止"
echo ""

# 2. 清理舊的 Docker 映像
echo "🧹 步驟 2: 清理舊的 Docker 映像"
docker rmi patent-rag-system-django-app 2>/dev/null || true
echo "✅ 舊映像已清理"
echo ""

# 3. 清理 Docker build cache (可選，但建議)
echo "🗑️  步驟 3: 清理 Docker build cache"
read -p "是否清理 Docker build cache? 這會確保完全重建但需要更長時間 (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker builder prune -f
    echo "✅ Build cache 已清理"
else
    echo "⏭️  跳過 cache 清理"
fi
echo ""

# 4. 確認 poetry.lock 存在
echo "📝 步驟 4: 檢查依賴文件"
if [ ! -f "poetry.lock" ]; then
    echo "❌ poetry.lock 不存在，請先在本地運行 'poetry lock' 生成"
    exit 1
fi
echo "✅ poetry.lock 文件存在"
echo ""

# 5. 重新構建 Docker 映像
echo "🔨 步驟 5: 構建 Docker 映像 (這可能需要幾分鐘)"
docker-compose -f docker-compose.prod.yml build --no-cache

if [ $? -ne 0 ]; then
    echo "❌ Docker 映像構建失敗"
    exit 1
fi
echo "✅ Docker 映像構建成功"
echo ""

# 6. 啟動服務
echo "🚢 步驟 6: 啟動服務"
docker-compose -f docker-compose.prod.yml up -d

if [ $? -ne 0 ]; then
    echo "❌ 服務啟動失敗"
    exit 1
fi
echo "✅ 服務已啟動"
echo ""

# 7. 等待服務啟動
echo "⏳ 步驟 7: 等待服務完全啟動 (15秒)"
sleep 15
echo ""

# 8. 檢查容器狀態
echo "🔍 步驟 8: 檢查容器狀態"
docker-compose -f docker-compose.prod.yml ps
echo ""

# 9. 檢查日誌
echo "📋 步驟 9: 檢查最近的日誌"
echo "--- Django App 日誌 ---"
docker-compose -f docker-compose.prod.yml logs --tail=20 django-app
echo ""
echo "--- ChromaDB 日誌 ---"
docker-compose -f docker-compose.prod.yml logs --tail=10 chromadb
echo ""

# 10. 測試健康檢查
echo "🏥 步驟 10: 測試 API 健康檢查"
echo "等待 5 秒後測試..."
sleep 5
curl -s http://localhost:8002/api/health/ | python3 -m json.tool || echo "❌ API 測試失敗"
echo ""

echo "================================"
echo "✅ 部署完成!"
echo ""
echo "📌 後續步驟:"
echo "1. 如果看到 'status: degraded'，這是正常的，表示還沒有向量資料"
echo "2. 在 Nginx Proxy Manager 中設定反向代理到 port 8002"
echo "3. 爬取專利資料: docker-compose -f docker-compose.prod.yml exec django-app bash"
echo "   然後運行: python manage.py scrape_docs --section invention --latest-only --max-periods 5"
echo "4. 查看實時日誌: docker-compose -f docker-compose.prod.yml logs -f django-app"
echo ""
