# VPS 部署指南 (使用 Docker + Nginx Proxy Manager)

本指南適用於在 VPS 上部署台灣專利搜尋系統，使用 SQLite 資料庫和既有的 Nginx Proxy Manager。

## 📋 前置需求

- VPS (建議至少 2GB RAM)
- 已安裝 Docker 和 Docker Compose
- 已設定好 Nginx Proxy Manager
- 網域名稱 (可選，可用 IP 訪問)
- Google Gemini API Key (免費取得: https://makersuite.google.com/app/apikey)

## 🚀 快速部署步驟

### 步驟 1: 連接到 VPS 並準備目錄

```bash
ssh root@your-vps-ip
# 或
ssh your-username@your-vps-ip

# 建立 /var/www 目錄（如果不存在）
mkdir -p /var/www
```

### 步驟 2: 安裝 Docker (如果尚未安裝)

```bash
# 安裝 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 啟動 Docker
systemctl start docker
systemctl enable docker

# 驗證安裝
docker --version
docker compose version
```

### 步驟 3: 克隆專案到 VPS

```bash
# 切換到 web 應用目錄
cd /var/www

# 克隆專案 (請替換成你的 Git repository URL)
git clone https://your-repo-url/patent-rag-system.git
cd patent-rag-system

# 或者使用 rsync 從本地傳輸
# 在本地執行:
# rsync -avz --exclude='data/' --exclude='db/' --exclude='chroma-data/' \
#   /path/to/patent-rag-system/ root@your-vps-ip:/var/www/patent-rag-system/
```

### 步驟 4: 設定環境變數

```bash
# 複製環境變數範例
cp .env.prod.example .env.prod

# 編輯環境變數
nano .env.prod
```

**編輯 `.env.prod` 內容**:

```bash
# Django 設定
SECRET_KEY=請用以下指令產生隨機key: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
DEBUG=False
ALLOWED_HOSTS=your-domain.com,your-vps-ip,localhost

# Google Gemini API (免費取得: https://makersuite.google.com/app/apikey)
GOOGLE_API_KEY=your-google-api-key-here

# 使用 SQLite (無需 PostgreSQL)
USE_SQLITE=true

# ChromaDB 設定
CHROMA_HOST=chromadb
CHROMA_PORT=8000

# RAG 系統參數
CHUNK_SIZE=1000
CHUNK_OVERLAP=100
TOP_K_RESULTS=5
EMBEDDING_MODEL=all-MiniLM-L6-v2

# 語言設定
LANGUAGE_CODE=zh-hant
TIME_ZONE=Asia/Taipei
```

**生成 SECRET_KEY**:

```bash
# 臨時啟動 Python 容器生成 SECRET_KEY
docker run --rm python:3.11-slim python -c 'from secrets import token_urlsafe; print(token_urlsafe(50))'

# 或在本地生成後複製
```

### 步驟 5: 建立必要的目錄

```bash
# 建立資料目錄
mkdir -p data/raw data/processed data/vector_store
mkdir -p db
mkdir -p chroma-data

# 設定權限
chmod -R 755 data
chmod -R 755 db
chmod -R 755 chroma-data
```

### 步驟 6: 構建並啟動容器

**方法 1: 使用自動部署腳本 (推薦)**

```bash
# 使用提供的部署腳本
chmod +x deploy-to-vps.sh
./deploy-to-vps.sh
```

**方法 2: 手動部署**

```bash
# 重要: 必須使用 --no-cache 確保依賴正確安裝
docker compose -f docker-compose.prod.yml build --no-cache

# 啟動服務
docker compose -f docker-compose.prod.yml up -d

# 查看日誌
docker compose -f docker-compose.prod.yml logs -f
```

**⚠️ 常見問題: `ModuleNotFoundError: No module named 'langchain_core.pydantic_v1'`**

如果遇到此錯誤,請確保:
1. 使用 `--no-cache` 重新構建: `docker compose -f docker-compose.prod.yml build --no-cache`
2. 確認 `poetry.lock` 文件已正確上傳到 VPS
3. 清理舊的 Docker 映像: `docker rmi patent-rag-system-django-app`
4. 重新構建並啟動

或直接使用提供的 `deploy-to-vps.sh` 腳本,它會自動處理這些問題。

### 步驟 7: 初始化系統

```bash
# 進入 Django 容器
docker compose -f docker-compose.prod.yml exec django-app bash

# 資料庫已在啟動時自動執行 migrate，如需重新執行:
python manage.py migrate

# (可選) 建立超級使用者
python manage.py createsuperuser

# 退出容器
exit
```

### 步驟 8: 爬取專利資料並建立索引

```bash
# 進入 Django 容器
docker compose -f docker-compose.prod.yml exec django-app bash

# 1. 爬取台灣專利資料 (從 TIPO FTPS 伺服器)
# 選項 1: 快速測試 (最新年份，少量資料)
python manage.py scrape_docs --section invention --latest-only --max-periods 2 --max-files-per-period 50

# 選項 2: 中等規模 (最新年份，中量資料)
python manage.py scrape_docs --section invention --latest-only --max-periods 5 --max-files-per-period 200

# 選項 3: 大規模 (所有年份，大量資料) - 需要較長時間和較大儲存空間
python manage.py scrape_docs --section invention --max-periods 10

# 2. 處理專利文檔成 chunks
python manage.py process_docs

# 3. 建立向量索引
python manage.py build_index --rebuild

# 4. 測試查詢
python manage.py test_query "請找出與人工智慧相關的專利"

# 退出容器
exit
```

**注意**:
- 爬取時間取決於資料量，可能需要數小時
- 確保 VPS 有足夠的磁碟空間 (建議至少 10GB 可用空間)

### 步驟 9: 在 Nginx Proxy Manager 設定反向代理

1. 登入 Nginx Proxy Manager 管理介面 (通常是 http://your-vps-ip:81)
   - 預設帳號: `admin@example.com`
   - 預設密碼: `changeme`

2. 新增 Proxy Host:
   - **Domain Names**: `your-domain.com` (或你的網域)
   - **Scheme**: `http`
   - **Forward Hostname / IP**: `專案所在VPS的IP` 或 `localhost` (如果 NPM 在同一台機器)
   - **Forward Port**: `8002`
   - **Cache Assets**: 開啟
   - **Block Common Exploits**: 開啟
   - **Websockets Support**: 開啟

3. (可選) 設定 SSL:
   - 切換到 **SSL** 標籤
   - 選擇 **Request a new SSL Certificate**
   - 勾選 **Force SSL**
   - 勾選 **HTTP/2 Support**
   - 輸入你的 Email
   - 勾選 **I Agree to the Let's Encrypt Terms of Service**
   - 點擊 **Save**

4. 儲存設定

### 步驟 10: 測試系統

```bash
# 本地測試
curl http://localhost:8002/api/health/

# 透過網域測試
curl https://your-domain.com/api/health/

# 或直接在瀏覽器開啟
# https://your-domain.com/
```

## 🔧 管理指令

### 查看服務狀態

```bash
cd /var/www/patent-rag-system
docker compose -f docker-compose.prod.yml ps
```

### 查看日誌

```bash
# 查看所有服務日誌
docker compose -f docker-compose.prod.yml logs -f

# 只看 Django 日誌
docker compose -f docker-compose.prod.yml logs -f django-app

# 只看 ChromaDB 日誌
docker compose -f docker-compose.prod.yml logs -f chromadb
```

### 重啟服務

```bash
# 重啟所有服務
docker compose -f docker-compose.prod.yml restart

# 重啟 Django 服務
docker compose -f docker-compose.prod.yml restart django-app
```

### 停止服務

```bash
docker compose -f docker-compose.prod.yml stop
```

### 啟動服務

```bash
docker compose -f docker-compose.prod.yml start
```

### 完全移除服務 (保留資料)

```bash
docker compose -f docker-compose.prod.yml down
```

### 完全移除服務和資料 (危險!)

```bash
docker compose -f docker-compose.prod.yml down -v
```

## 📂 資料備份

### 備份資料庫

```bash
cd /var/www/patent-rag-system

# 備份 SQLite 資料庫
tar -czf backup_db_$(date +%Y%m%d).tar.gz db/

# 備份專利資料
tar -czf backup_patent_data_$(date +%Y%m%d).tar.gz data/

# 備份 ChromaDB 向量資料
tar -czf backup_chroma_$(date +%Y%m%d).tar.gz chroma-data/

# 全部備份
tar -czf backup_all_$(date +%Y%m%d).tar.gz db/ data/ chroma-data/
```

### 恢復備份

```bash
# 停止服務
docker compose -f docker-compose.prod.yml stop

# 恢復資料
tar -xzf backup_all_YYYYMMDD.tar.gz

# 重啟服務
docker compose -f docker-compose.prod.yml start
```

### 自動備份 (Cron Job)

```bash
# 編輯 crontab
crontab -e

# 添加每天凌晨 2 點備份
0 2 * * * cd /var/www/patent-rag-system && tar -czf /backup/patent_rag_$(date +\%Y\%m\%d).tar.gz db/ data/ chroma-data/

# 添加每週清理 30 天前的備份
0 3 * * 0 find /backup -name "patent_rag_*.tar.gz" -mtime +30 -delete
```

## 🔍 故障排除

### 1. 容器無法啟動

```bash
# 查看詳細錯誤
docker compose -f docker-compose.prod.yml logs

# 檢查 .env.prod 是否正確
cat .env.prod

# 檢查 8002 port 是否被佔用
netstat -tulpn | grep 8002
```

### 2. ChromaDB 連接失敗

```bash
# 檢查 ChromaDB 容器狀態
docker compose -f docker-compose.prod.yml ps chromadb

# 重啟 ChromaDB
docker compose -f docker-compose.prod.yml restart chromadb

# 查看 ChromaDB 日誌
docker compose -f docker-compose.prod.yml logs chromadb
```

### 3. 向量資料庫為空

```bash
# 進入容器
docker compose -f docker-compose.prod.yml exec django-app bash

# 檢查索引狀態
python manage.py shell
>>> from rag.services.rag_engine import RAGEngine
>>> engine = RAGEngine()
>>> stats = engine.get_stats()
>>> print(stats)
>>> exit()

# 如果顯示 0 documents，重新建立索引
python manage.py build_index --rebuild
```

### 4. API 回應緩慢

```bash
# 檢查系統資源
free -h
df -h
top

# 增加 Gunicorn workers (編輯 docker-compose.prod.yml)
# 將 --workers 2 改為 --workers 4

# 重啟服務
docker compose -f docker-compose.prod.yml restart django-app
```

### 5. 無法訪問網站

```bash
# 檢查防火牆
ufw status

# 如果需要開放 8002 port
ufw allow 8002

# 檢查 Nginx Proxy Manager 設定
# 確認 Forward Port 設為 8002
# 確認 Forward Hostname 正確

# 測試本地連接
curl http://localhost:8002/api/health/
```

## 🔐 安全建議

1. **防火牆設定**

```bash
# 安裝 ufw
apt install ufw

# 基本規則
ufw default deny incoming
ufw default allow outgoing

# 允許 SSH
ufw allow 22

# 允許 HTTP/HTTPS (Nginx Proxy Manager)
ufw allow 80
ufw allow 443

# 不要直接開放 8002 port (由 Nginx Proxy Manager 代理)

# 啟用防火牆
ufw enable

# 查看狀態
ufw status
```

2. **定期更新**

```bash
# 更新系統
apt update && apt upgrade -y

# 更新 Docker 映像
cd /opt/patent-rag-system
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

3. **強化 Django 安全設定**

在 `.env.prod` 中確保:
- `DEBUG=False`
- 使用強 `SECRET_KEY`
- `ALLOWED_HOSTS` 只包含你的網域和 IP

4. **監控與日誌**

```bash
# 安裝 fail2ban 防止暴力破解
apt install fail2ban

# 監控磁碟空間
df -h

# 設定日誌輪轉 (避免日誌檔過大)
nano /etc/docker/daemon.json

# 添加:
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}

# 重啟 Docker
systemctl restart docker
```

## 📊 性能優化

### 1. 調整 Gunicorn Workers

根據 CPU 核心數調整:

```bash
# 查看 CPU 核心數
nproc

# 建議 workers 數量 = (2 * CPU 核心數) + 1
# 編輯 docker-compose.prod.yml
# 將 --workers 2 改為適合的數量
```

### 2. 啟用 Redis 快取 (可選)

編輯 `docker-compose.prod.yml` 添加:

```yaml
redis:
  image: redis:7-alpine
  volumes:
    - ./redis-data:/data
  expose:
    - "6379"
  networks:
    - rag-network
  restart: unless-stopped
```

## 📞 獲取協助

如遇到問題:
1. 查看日誌: `docker compose -f docker-compose.prod.yml logs`
2. 檢查 GitHub Issues
3. 參考主要 README.md

## 🎉 部署完成！

你的台灣專利搜尋系統已成功部署到 VPS！

訪問: `https://your-domain.com/`

API 健康檢查: `https://your-domain.com/api/health/`
