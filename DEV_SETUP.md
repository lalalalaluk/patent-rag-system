# 開發環境設置指南

本專案支持兩種開發模式：**混合模式（推薦）** 和 **完全 Docker 模式**。

## 混合模式（推薦）⭐

服務運行在 Docker，Django 運行在本機。獲得最佳開發體驗。

### 1. 啟動服務

```bash
# 只啟動 PostgreSQL、ChromaDB、Redis
docker-compose -f docker-compose.dev.yml up -d

# 檢查服務狀態
docker-compose -f docker-compose.dev.yml ps
```

### 2. 設置 Python 環境

```bash
# 安裝依賴
poetry install

# 或使用 pip（如果沒有 Poetry）
pip install -r requirements.txt  # 需要先生成：poetry export -f requirements.txt --output requirements.txt
```

### 3. 設置環境變數

```bash
# 複製範例文件
cp .env.example .env

# 編輯 .env，確保使用 localhost 連接
# POSTGRES_HOST=localhost
# CHROMA_HOST=localhost
# REDIS_URL=redis://localhost:6379/0
```

### 4. 運行 Django

```bash
# 運行 migrations
poetry run python manage.py migrate

# 啟動開發伺服器
poetry run python manage.py runserver

# 或使用簡短命令
python manage.py runserver
```

### 5. 初始化 RAG 系統

```bash
# 抓取 Python 文檔
python manage.py scrape_docs --sections tutorial library --max-pages 50

# 處理文檔
python manage.py process_docs

# 建立向量索引
python manage.py build_index --rebuild
```

### 優點
- ✅ 熱重載超快（檔案變更立即生效）
- ✅ IDE 調試簡單（直接設斷點）
- ✅ 資源占用少
- ✅ 不需要進容器執行指令

---

## 完全 Docker 模式

所有服務包括 Django 都在 Docker 中運行。

### 1. 啟動所有服務

```bash
# 構建並啟動
docker-compose up --build -d

# 查看日誌
docker-compose logs -f django-app
```

### 2. 設置環境變數

```bash
# 編輯 .env，使用 Docker 服務名稱
# POSTGRES_HOST=postgres
# CHROMA_HOST=chromadb
# REDIS_URL=redis://redis:6379/0
```

### 3. 運行指令（需進入容器）

```bash
# 進入 Django 容器
docker-compose exec django-app bash

# 在容器內執行指令
python manage.py migrate
python manage.py scrape_docs --sections tutorial library --max-pages 50
python manage.py process_docs
python manage.py build_index --rebuild
```

### 優點
- ✅ 環境完全一致
- ✅ 適合 CI/CD 測試
- ✅ 模擬生產環境

---

## 常用指令

### 停止服務
```bash
# 混合模式
docker-compose -f docker-compose.dev.yml down

# 完全 Docker 模式
docker-compose down
```

### 查看日誌
```bash
# 混合模式（只有服務日誌）
docker-compose -f docker-compose.dev.yml logs -f postgres

# 完全 Docker 模式
docker-compose logs -f django-app
```

### 清理數據
```bash
# 清理所有 volumes（會刪除數據庫）
docker-compose down -v
```

### 重建
```bash
# 混合模式（服務不需要重建）
docker-compose -f docker-compose.dev.yml restart

# 完全 Docker 模式
docker-compose up --build --force-recreate
```

---

## 切換模式

### 從混合模式切換到完全 Docker
1. 修改 `.env`：
   ```bash
   POSTGRES_HOST=postgres
   CHROMA_HOST=chromadb
   REDIS_URL=redis://redis:6379/0
   ```
2. 停止混合模式服務：
   ```bash
   docker-compose -f docker-compose.dev.yml down
   ```
3. 啟動完全 Docker：
   ```bash
   docker-compose up -d
   ```

### 從完全 Docker 切換到混合模式
1. 修改 `.env`：
   ```bash
   POSTGRES_HOST=localhost
   CHROMA_HOST=localhost
   REDIS_URL=redis://localhost:6379/0
   ```
2. 停止完全 Docker：
   ```bash
   docker-compose down
   ```
3. 啟動混合模式：
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   python manage.py runserver
   ```

---

## 測試 API

```bash
# Health check
curl http://localhost:8000/api/health/

# Query test
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I use list comprehensions?"}'
```

---

## 故障排除

### 端口被佔用
```bash
# 查找佔用端口的進程
lsof -i :8000
lsof -i :5432

# 殺掉進程
kill -9 <PID>
```

### 數據庫連接失敗
```bash
# 檢查 PostgreSQL 是否運行
docker-compose -f docker-compose.dev.yml ps postgres

# 檢查 .env 中的 POSTGRES_HOST 設置
cat .env | grep POSTGRES_HOST
```

### ChromaDB 連接問題
```bash
# 檢查 ChromaDB 日誌
docker-compose -f docker-compose.dev.yml logs chromadb

# 測試連接
curl http://localhost:8001/api/v1/heartbeat
```
