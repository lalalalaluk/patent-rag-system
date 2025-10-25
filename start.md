# Python 官方文檔 RAG 問答系統 - 開發指南

## 系統架構

```
python-doc-rag/
├── docker-compose.yml           # 容器編排
├── Dockerfile                   # Django 應用容器
├── pyproject.toml              # Poetry 依賴管理
├── poetry.lock
├── .env.example                # 環境變數範例
├── .gitignore
├── README.md
│
├── django_rag/                 # Django 專案根目錄
│   ├── manage.py
│   ├── config/                 # Django 設定
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   │
│   ├── rag/                    # RAG 應用
│   │   ├── __init__.py
│   │   ├── models.py           # 資料模型（對話歷史等）
│   │   ├── views.py            # API endpoints
│   │   ├── urls.py
│   │   ├── serializers.py      # DRF serializers
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── document_processor.py  # 文檔處理
│   │   │   ├── scraper.py             # 爬取 Python 文檔
│   │   │   ├── embedding_service.py   # Embedding 生成
│   │   │   └── rag_engine.py          # RAG 核心邏輯
│   │   ├── management/
│   │   │   └── commands/
│   │   │       ├── scrape_docs.py     # 下載文檔指令
│   │   │       └── build_index.py     # 建立向量索引
│   │   └── templates/          # 前端模板（可選）
│   │
│   └── data/                   # 資料目錄
│       ├── raw/                # 原始 HTML
│       ├── processed/          # 處理後文本
│       └── vector_store/       # 向量資料庫持久化
│
└── tests/
    ├── test_scraper.py
    ├── test_rag_engine.py
    └── test_api.py
```

## Docker Compose 配置

### Services 說明

**1. django-app**
- Django + DRF 後端
- 處理 API 請求
- RAG 邏輯執行
- Port: 8000

**2. chromadb**
- 向量資料庫
- 儲存文檔 embeddings
- Port: 8001（內部）

**3. postgres**（可選，用於儲存對話歷史）
- 持久化對話記錄
- 用戶查詢日誌
- Port: 5432

**4. redis**（可選，用於快取）
- 快取常見查詢結果
- Port: 6379

### docker-compose.yml 結構

```yaml
version: '3.9'

services:
  django-app:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - ./django_rag:/app
      - ./data:/app/data
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - chromadb
      - postgres
      - redis

  chromadb:
    image: chromadb/chroma:latest
    volumes:
      - chroma-data:/chroma/chroma
    ports:
      - "8001:8000"
    environment:
      - IS_PERSISTENT=TRUE

  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=rag_db
      - POSTGRES_USER=raguser
      - POSTGRES_PASSWORD=ragpass

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

volumes:
  chroma-data:
  postgres-data:
  redis-data:
```

## Poetry 配置

### pyproject.toml 主要依賴

```toml
[tool.poetry]
name = "python-doc-rag"
version = "0.1.0"
description = "RAG system for Python documentation"
authors = ["Your Name <your.email@example.com>"]

[tool.poetry.dependencies]
python = "^3.11"
django = "^5.0"
djangorestframework = "^3.14"
chromadb = "^0.4.22"
langchain = "^0.1.0"
openai = "^1.10.0"
beautifulsoup4 = "^4.12"
requests = "^2.31"
python-dotenv = "^1.0"
psycopg2-binary = "^2.9"
redis = "^5.0"
celery = "^5.3"  # 可選：異步任務
gunicorn = "^21.2"  # 生產環境

[tool.poetry.group.dev.dependencies]
pytest = "^7.4"
pytest-django = "^4.7"
black = "^23.12"
flake8 = "^7.0"
ipython = "^8.18"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

## Dockerfile 結構

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安裝 Poetry
RUN pip install poetry

# 複製依賴文件
COPY pyproject.toml poetry.lock ./

# 安裝依賴（不包含虛擬環境）
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# 複製專案文件
COPY ./django_rag /app

# 暴露端口
EXPOSE 8000

# 啟動命令（開發環境）
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

## 核心功能模組

### 1. Document Scraper (`scraper.py`)

**功能：**
- 爬取 Python 官方文檔特定章節
- 過濾不需要的頁面（索引頁、導航頁）
- 儲存為結構化格式

**建議爬取範圍：**
- Tutorial (`/tutorial/`)
- Library Reference (`/library/`)
- Language Reference (`/reference/`)
- 限制：前 100-200 頁（避免過大）

**輸出格式：**
```json
{
  "url": "https://docs.python.org/3/tutorial/introduction.html",
  "title": "An Informal Introduction to Python",
  "content": "...",
  "section": "tutorial",
  "scraped_at": "2025-10-16T10:00:00Z"
}
```

### 2. Document Processor (`document_processor.py`)

**功能：**
- 解析 HTML，提取純文本
- 保留程式碼區塊標記
- 文本分塊（Chunking）策略

**Chunking 參數：**
- Chunk size: 512-1024 tokens
- Overlap: 50-100 tokens
- 按段落和程式碼區塊分割

**Metadata 保留：**
- 原始 URL
- 標題層級
- 所屬章節
- 程式碼/文本類型

### 3. Embedding Service (`embedding_service.py`)

**功能：**
- 將文本轉換為向量
- 批次處理優化

**選項：**
- **OpenAI embeddings**（`text-embedding-3-small`）
  - 需要 API key
  - 效果好
  
- **本地模型**（sentence-transformers）
  - `all-MiniLM-L6-v2`（輕量）
  - `all-mpnet-base-v2`（效果較好）
  - 免費但較慢

### 4. RAG Engine (`rag_engine.py`)

**核心流程：**

```python
class RAGEngine:
    def __init__(self):
        self.vector_store = ChromaDB(...)
        self.llm = OpenAI(...)  # 或 Claude
        
    def query(self, question: str) -> dict:
        # 1. 檢索相關文檔
        relevant_docs = self.vector_store.similarity_search(
            question, 
            k=5
        )
        
        # 2. 重排序（可選）
        reranked_docs = self.rerank(question, relevant_docs)
        
        # 3. 構建 prompt
        context = self.build_context(reranked_docs)
        prompt = self.build_prompt(question, context)
        
        # 4. 生成回答
        answer = self.llm.generate(prompt)
        
        # 5. 返回結果 + 來源
        return {
            "answer": answer,
            "sources": [doc.metadata for doc in relevant_docs],
            "confidence": self.calculate_confidence(...)
        }
```

**Prompt Template：**
```python
PROMPT_TEMPLATE = """
You are a helpful assistant for Python programming questions.
Use the following documentation excerpts to answer the question.
If the answer cannot be found in the documentation, say so.

Documentation:
{context}

Question: {question}

Answer (include relevant code examples if applicable):
"""
```

### 5. Django Views/API (`views.py`)

**API Endpoints：**

```python
# POST /api/query/
{
  "question": "How do I use list comprehensions?"
}

# Response
{
  "answer": "...",
  "sources": [
    {
      "title": "Data Structures",
      "url": "https://docs.python.org/3/tutorial/datastructures.html",
      "excerpt": "..."
    }
  ],
  "response_time_ms": 1234
}

# GET /api/health/
# 檢查系統狀態

# POST /api/feedback/
# 用戶回饋（答案好壞）
```

## Django Management Commands

### 1. 爬取文檔
```bash
python manage.py scrape_docs --sections tutorial library --max-pages 100
```

### 2. 建立向量索引
```bash
python manage.py build_index --rebuild
```

### 3. 測試查詢
```bash
python manage.py test_query "How do I read files in Python?"
```

## 開發流程

### Phase 1: 環境設置（Day 1）
1. 初始化 Poetry 專案
2. 設定 Docker Compose
3. 建立基本 Django 專案結構
4. 測試容器啟動

### Phase 2: 文檔收集（Day 1-2）
1. 實作 scraper
2. 爬取並儲存文檔（100-200 頁）
3. 實作 document processor
4. 測試分塊效果

### Phase 3: RAG 核心（Day 2-3）
1. 整合 ChromaDB
2. 實作 embedding service
3. 建立向量索引
4. 實作 RAG engine
5. 測試檢索品質

### Phase 4: API 開發（Day 3-4）
1. 建立 Django REST API
2. 實作查詢端點
3. 加入錯誤處理
4. 寫基本測試

### Phase 5: 優化與測試（Day 4-5）
1. 準備測試問題集
2. 評估答案品質
3. 調整參數（chunk size, top-k 等）
4. 加入快取
5. 完善 README

## 測試問題集範例

```python
TEST_QUESTIONS = [
    # 基礎語法
    "How do I create a list in Python?",
    "What is the difference between list and tuple?",
    
    # 進階主題
    "How do decorators work?",
    "Explain Python's GIL",
    
    # 實用問題
    "How do I read a CSV file?",
    "What's the best way to handle exceptions?",
    
    # 邊界案例
    "How do I use blockchain in Python?",  # 應該說文檔中沒有
    "What is JavaScript?",  # 不相關問題
]
```

## 評估指標

**手動評估：**
- 答案正確性（1-5 分）
- 來源相關性
- 回答完整度

**自動評估（進階）：**
- 檢索精確度（使用標註資料集）
- 回答與來源的 faithfulness
- 回應時間

## 環境變數 (.env)

```bash
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://raguser:ragpass@postgres:5432/rag_db

# ChromaDB
CHROMA_HOST=chromadb
CHROMA_PORT=8000

# OpenAI (或使用本地模型則不需要)
OPENAI_API_KEY=sk-...

# Redis
REDIS_URL=redis://redis:6379/0
```

## 啟動指令

```bash
# 1. 安裝依賴
poetry install

# 2. 啟動所有服務
docker-compose up -d

# 3. 初始化資料庫
docker-compose exec django-app python manage.py migrate

# 4. 爬取文檔
docker-compose exec django-app python manage.py scrape_docs

# 5. 建立索引
docker-compose exec django-app python manage.py build_index

# 6. 測試
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I use f-strings?"}'
```

## 面試展示重點

1. **系統架構**：展示 Docker Compose、服務分離
2. **RAG 流程**：解釋檢索和生成的邏輯
3. **程式碼品質**：Poetry 管理、測試、錯誤處理
4. **可擴展性**：如何加入更多文檔源、改進檢索
5. **實際演示**：現場問答，展示來源引用

## 進階功能（可選）

- **對話記憶**：使用 PostgreSQL 儲存歷史
- **多輪對話**：context 維護
- **Hybrid Search**：結合關鍵字和向量搜尋
- **Query Rewriting**：改善查詢品質
- **簡單前端**：React/Vue 介面

## 給 Claude Code 的指令範例

把這份指南給 Claude Code 時，可以這樣說：

```
請根據這份指南，幫我建立完整的 Python 文檔 RAG 系統。

要求：
1. 使用 Docker Compose 管理服務
2. 使用 Poetry 管理 Python 依賴
3. 使用 Django + DRF 建立 API
4. 實作所有核心功能模組
5. 包含完整的錯誤處理
6. 寫基本的測試
7. 提供清楚的 README

請一步步實作，並在每個階段說明你在做什麼。
```

## 常見問題

### Q: 應該使用 OpenAI API 還是本地模型？
**A:** 如果有 API key，用 OpenAI 效果較好且快速。如果想展示本地部署能力，可以用 sentence-transformers + Ollama。

### Q: 文檔要爬多少頁？
**A:** 建議 100-200 頁即可，涵蓋 Tutorial 和常用的 Library Reference。太多會導致索引建立過慢。

### Q: 需要加入身份驗證嗎？
**A:** Demo 專案可以先不加，面試時提到「可以加入 JWT 認證」即可。

### Q: 如何部署展示？
**A:** 可以部署到：
- Render（免費方案）
- Railway（有免費額度）
- Fly.io
- 或準備好本地展示

### Q: 前端需要做嗎？
**A:** 要

## 參考資源

- [LangChain 文檔](https://python.langchain.com/)
- [ChromaDB 文檔](https://docs.trychroma.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Poetry 文檔](https://python-poetry.org/docs/)
- [Docker Compose 文檔](https://docs.docker.com/compose/)
