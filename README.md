# 台灣專利搜尋系統 (Taiwan Patent RAG System)

一個基於 RAG (Retrieval-Augmented Generation) 技術的台灣專利智能搜尋與分析系統。

## 功能特點

- 🔍 智能檢索台灣專利文件
- 💬 自然語言專利問答
- 📚 專利來源追蹤 (專利號、申請人、發明人等)
- 🐳 完整 Docker 容器化部署
- 🚀 RESTful API 介面
- 🇹🇼 支援繁體中文

## 技術棧

- **後端框架**: Django + Django REST Framework
- **向量資料庫**: ChromaDB
- **LLM**: Google Gemini Pro (FREE)
- **Embeddings**: Sentence-Transformers (本地運行, 免費)
- **依賴管理**: Poetry
- **容器化**: Docker Compose
- **語言**: 繁體中文 (zh-hant)

## 快速開始

### 1. 設定環境變數

```bash
# 編輯 .env 文件，填入你的 Google API Key
nano .env
```

必須設定 `GOOGLE_API_KEY` (免費取得: https://makersuite.google.com/app/apikey):
```
GOOGLE_API_KEY=your-google-api-key-here
```

**優點**:
- ✅ Google Gemini API 完全免費
- ✅ Embeddings 使用本地模型,不需要 API 呼叫
- ✅ 無需信用卡

### 2. 啟動服務

**開發環境 (本地測試)**:
```bash
# 啟動所有容器
docker-compose up -d

# 查看日誌
docker-compose logs -f django-app
```

**生產環境 (VPS 部署)**:
```bash
# 重要: 必須使用 --no-cache 確保依賴正確安裝
docker compose -f docker-compose.prod.yml build --no-cache

# 啟動服務 (運行在 port 8002)
docker compose -f docker-compose.prod.yml up -d

# 查看日誌
docker compose -f docker-compose.prod.yml logs -f django-app
```

**⚠️ 常見問題**: 如果遇到 `ModuleNotFoundError: No module named 'langchain_core.pydantic_v1'` 錯誤:
```bash
# 1. 停止容器
docker compose -f docker-compose.prod.yml down

# 2. 清理舊映像
docker rmi patent-rag-system-django-app

# 3. 重新構建 (必須使用 --no-cache)
docker compose -f docker-compose.prod.yml build --no-cache

# 4. 啟動服務
docker compose -f docker-compose.prod.yml up -d
```

詳細部署說明請參考 [DEPLOYMENT.md](DEPLOYMENT.md)

### 3. 初始化系統

**⚠️ 重要**: 專利爬蟲需要實作。請參考 `rag/services/patent_scraper_template.py` 了解如何實作台灣專利資料爬取。

```bash
# 進入容器
docker-compose exec django-app bash

# 1. 爬取台灣專利資料 (需要先實作爬蟲)
# TODO: 實作專利爬蟲後執行
python manage.py scrape_docs --sections invention utility --max-pages 50

# 2. 處理專利文檔成chunks
python manage.py process_docs

# 3. 建立向量索引
python manage.py build_index --rebuild
```

### 4. 測試系統

#### 🌐 使用 Web 介面 (推薦)
打開瀏覽器訪問:
```
http://localhost:8000/
```

#### 使用 Management Command
```bash
docker-compose exec django-app python manage.py test_query "請找出與人工智慧相關的專利"
```

#### 使用 API
```bash
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{"question": "請找出與半導體製程相關的專利"}'
```

#### 健康檢查
Web: http://localhost:8000/health-page/
API: http://localhost:8000/api/health/

## API 文檔

### POST /api/query/

查詢台灣專利相關問題

**請求:**
```json
{
  "question": "請找出與人工智慧相關的專利"
}
```

**回應:**
```json
{
  "answer": "根據搜尋結果,以下是與人工智慧相關的專利...",
  "sources": [
    {
      "title": "智慧型影像辨識系統",
      "patent_number": "I123456",
      "url": "https://...",
      "section": "invention",
      "excerpt": "..."
    }
  ],
  "response_time_ms": 1234
}
```

### GET /api/health/

系統健康檢查

**回應:**
```json
{
  "status": "healthy",
  "vector_db_stats": {
    "total_documents": 1000,
    "collection_name": "taiwan_patents",
    "embedding_dimension": 384
  }
}
```

## Management Commands

### scrape_docs
爬取台灣專利資料

**⚠️ 需要先實作爬蟲** - 請參考 `rag/services/patent_scraper_template.py`

```bash
# 爬取所有專利類別（最多200件每類別）
python manage.py scrape_docs

# 只爬取發明專利和新型專利
python manage.py scrape_docs --sections invention utility

# 限制每章節最多50頁
python manage.py scrape_docs --max-pages 50
```

### process_docs
將爬取的文檔處理成 chunks

```bash
# 處理所有可用的文檔
python manage.py process_docs

# 只處理特定章節
python manage.py process_docs --sections tutorial
```

### build_index
建立向量資料庫索引

```bash
# 建立索引（增量）
python manage.py build_index

# 重建索引（刪除現有資料）
python manage.py build_index --rebuild

# 只索引特定章節
python manage.py build_index --sections tutorial
```

### test_query
測試查詢

```bash
python manage.py test_query "How do decorators work?"
```

## 專案結構

```
python-rag-system/
├── config/                  # Django 設定
│   ├── settings.py
│   └── urls.py
├── rag/                     # RAG 應用
│   ├── services/            # 核心服務
│   │   ├── scraper.py              # 文檔爬蟲
│   │   ├── document_processor.py   # 文檔處理
│   │   ├── embedding_service.py    # Embedding 生成
│   │   └── rag_engine.py           # RAG 核心邏輯
│   ├── management/
│   │   └── commands/        # 管理指令
│   ├── views.py             # API endpoints
│   ├── serializers.py
│   └── urls.py
├── data/                    # 資料目錄
│   ├── raw/                 # 原始爬取資料
│   ├── processed/           # 處理後的 chunks
│   └── vector_store/        # 向量資料庫
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── manage.py
└── .env
```

## 開發指令

```bash
# 本地開發 (需要先安裝依賴)
python manage.py runserver

# 進入 Django shell
python manage.py shell

# 查看可用的 management commands
python manage.py help
```

## 故障排除

### 1. ChromaDB 連接失敗
確保 ChromaDB 容器正在運行:
```bash
docker-compose ps chromadb
docker-compose logs chromadb
```

### 2. OpenAI API 錯誤
檢查 `.env` 檔案中的 `OPENAI_API_KEY` 是否正確設定

### 3. 資料庫連接失敗
確保 PostgreSQL 容器正在運行:
```bash
docker-compose ps postgres
```

### 4. 查看容器日誌
```bash
docker-compose logs -f django-app
docker-compose logs -f chromadb
```

## 測試問題範例

```bash
# 基礎語法
python manage.py test_query "How do I create a dictionary?"
python manage.py test_query "What is the difference between list and tuple?"

# 進階主題
python manage.py test_query "How do I use async/await?"
python manage.py test_query "How do decorators work?"

# 實用問題
python manage.py test_query "How do I read a JSON file?"
python manage.py test_query "What's the best way to handle exceptions?"
```

## 系統配置

可以在 `.env` 文件中調整以下參數:

- `CHUNK_SIZE`: 文檔分塊大小（預設: 1000字元）
- `CHUNK_OVERLAP`: 分塊重疊大小（預設: 100字元）
- `TOP_K_RESULTS`: 檢索的文檔數量（預設: 5）
- `MAX_PAGES_TO_SCRAPE`: 每章節最大爬取頁數（預設: 50）

## License

MIT
