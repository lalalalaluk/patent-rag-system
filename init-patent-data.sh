#!/bin/bash

# 專利資料初始化腳本
# 用於首次部署或重新初始化專利資料庫

set -e  # 遇到錯誤立即退出

echo "🚀 台灣專利資料初始化腳本"
echo "================================"
echo ""

# 檢查是否在正確目錄
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "❌ 錯誤: 請在專案根目錄執行此腳本"
    exit 1
fi

# 檢查容器是否運行
if ! docker compose -f docker-compose.prod.yml ps django-app | grep -q "Up"; then
    echo "❌ 錯誤: Django 容器未運行"
    echo "請先啟動容器: docker compose -f docker-compose.prod.yml up -d"
    exit 1
fi

echo "📋 選擇初始化模式:"
echo "1) 快速測試 (少量資料, ~5分鐘)"
echo "2) 中等規模 (中量資料, ~30分鐘)"
echo "3) 完整資料 (大量資料, ~數小時)"
echo ""
read -p "請選擇 (1/2/3): " mode

case $mode in
    1)
        echo ""
        echo "🎯 快速測試模式"
        echo "================================"
        MAX_FILES=100
        ;;
    2)
        echo ""
        echo "🎯 中等規模模式"
        echo "================================"
        MAX_FILES=1000
        ;;
    3)
        echo ""
        echo "🎯 完整資料模式"
        echo "================================"
        MAX_FILES=0  # 0 表示不限制
        ;;
    *)
        echo "❌ 無效選擇"
        exit 1
        ;;
esac

echo ""
echo "⚠️  注意: 此操作將:"
echo "  - 檢查現有專利資料"
echo "  - 處理專利文檔成 chunks"
echo "  - 重建向量索引 (會刪除現有索引)"
echo ""
read -p "確定要繼續嗎? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 已取消"
    exit 1
fi

echo ""
echo "================================"
echo "開始處理..."
echo "================================"
echo ""

# 進入容器執行命令
docker compose -f docker-compose.prod.yml exec django-app bash -c "
set -e

echo '📊 步驟 1/4: 檢查專利資料'
echo '--------------------------------'
file_count=\$(find data/raw/patent_data -name '*.xml' 2>/dev/null | wc -l)
echo \"找到 \$file_count 個 XML 檔案\"

if [ \"\$file_count\" -eq 0 ]; then
    echo '❌ 錯誤: 沒有找到專利資料'
    echo '請先使用 scraper 容器下載專利資料'
    echo '或參考 DEPLOYMENT.md 的步驟 8'
    exit 1
fi
echo '✅ 專利資料檢查完成'
echo ''

echo '🔄 步驟 2/4: 解析專利 XML 檔案'
echo '--------------------------------'
python manage.py parse_patents
echo '✅ XML 解析完成'
echo ''

echo '📝 步驟 3/4: 處理專利文檔成 chunks'
echo '--------------------------------'
if [ $MAX_FILES -gt 0 ]; then
    python manage.py process_docs --max-files $MAX_FILES
else
    python manage.py process_docs
fi
echo '✅ 文檔處理完成'
echo ''

echo '🗂️  步驟 4/4: 建立向量索引'
echo '--------------------------------'
python manage.py build_index --rebuild
echo '✅ 索引建立完成'
echo ''

echo '🧪 步驟 5/4: 測試查詢'
echo '--------------------------------'
python manage.py test_query '請找出與人工智慧相關的專利'
echo ''
"

if [ $? -eq 0 ]; then
    echo ""
    echo "================================"
    echo "✅ 初始化完成!"
    echo "================================"
    echo ""
    echo "📊 系統統計:"
    docker compose -f docker-compose.prod.yml exec django-app python manage.py shell -c "
from rag.services.rag_engine import RAGEngine
engine = RAGEngine()
stats = engine.get_stats()
print(f\"  - 總文檔數: {stats.get('total_documents', 0)}\")
print(f\"  - 集合名稱: {stats.get('collection_name', 'N/A')}\")
print(f\"  - 向量維度: {stats.get('embedding_dimension', 0)}\")
" 2>/dev/null || echo "  (無法取得統計資料)"

    echo ""
    echo "🎉 您現在可以使用系統了!"
    echo ""
    echo "📍 訪問網址:"
    echo "  - Web UI: http://localhost:8002/"
    echo "  - API: http://localhost:8002/api/query/"
    echo "  - 健康檢查: http://localhost:8002/api/health/"
    echo ""
else
    echo ""
    echo "================================"
    echo "❌ 初始化失敗"
    echo "================================"
    echo ""
    echo "請檢查上方錯誤訊息,或查看日誌:"
    echo "  docker compose -f docker-compose.prod.yml logs django-app"
    echo ""
    exit 1
fi
