# 台灣專利 RAG 系統 - 資料處理說明

本文件說明台灣專利資料的爬取流程與 RAG (Retrieval-Augmented Generation) 向量處理方式。

---

## 📊 資料集概況

### 當前資料集 (Demo)
- **資料來源**: 智慧財產局 (TIPO) FTPS 伺服器
- **資料範圍**: 112-114 年 (2023-2025)
- **專利總數**: 10,746 件
- **文本區塊數**: 23,552 chunks
- **資料大小**: 約 51MB (JSON 格式)

### 資料分布
\`\`\`
年份分布:
- 114年 (2025): 1,059 件
- 113年 (2024): 6,279 件
- 112年 (2023): 3,408 件

熱門 IPC 分類:
- H01L (半導體裝置): 10.7%
- G06F (數位資料處理): 4.6%
- H04L (數位資訊傳輸): 2.2%

主要申請人:
- 台灣積體電路製造股份有限公司 (TSMC): 194 件
- 南亞科技股份有限公司: 167 件
- 美商應用材料股份有限公司: 125 件
\`\`\`

---

## 🔄 三階段資料爬取流程

### 階段 1: Web Scraping (網頁爬取)
**工具**: Playwright (瀏覽器自動化)  
**檔案**: \`rag/services/tipo_web_scraper.py\`

\`\`\`python
class TIPOWebScraper:
    """爬取 TIPO 網站上的 FTPS 下載連結"""

    def scrape_ftps_links(self, year, section='invention'):
        # 使用 Playwright 瀏覽器自動化
        # 從 TIPO 網站取得 FTPS 檔案清單
        # 返回: [(年份, 期別, FTPS路徑), ...]
\`\`\`

**爬取策略**:
- 目標網站: 智慧財產局專利資料開放平台
- 動態網頁處理: JavaScript 渲染內容
- 延遲控制: 每個請求間隔 0.5 秒 (尊重伺服器負載)

### 階段 2: FTPS Download (檔案下載)
**工具**: Implicit FTPS (FTP over TLS on port 990)  
**檔案**: \`rag/services/tipo_ftps_downloader.py\`

\`\`\`python
class ImplicitFTP_TLS(FTP):
    """Implicit FTPS 客戶端 (port 990)

    TIPO 使用 Implicit FTPS,連接時立即建立 TLS,不使用 STARTTLS
    """

    def connect(self, host='', port=990, timeout=-999):
        # 建立 socket 連接
        self.sock = socket.create_connection((host, port), timeout)
        # 立即包裝為 TLS (Implicit FTPS)
        self.sock = self.context.wrap_socket(self.sock, server_hostname=host)
\`\`\`

**下載策略**:
- 伺服器: \`tipoftps.tipo.gov.tw:990\`
- 認證方式: 匿名登入 (anonymous)
- 路徑結構: \`/PatentIsuRegSpecXMLA/{年份}/{期別}/\`
- 檔案格式: XML (每個專利一個檔案)
- 錯誤處理: 連接中斷時自動重連

**實際下載範例**:
\`\`\`bash
# 下載 112-114 年資料 (3年 demo 資料集)
python manage.py scrape_docs --section invention \\
    --latest-only \\
    --max-periods 5 \\
    --max-files-per-period 100
\`\`\`

### 階段 3: XML Parsing (資料解析)
**工具**: ElementTree (Python 標準庫)  
**檔案**: \`rag/services/tipo_xml_parser.py\`

\`\`\`python
class TIPOXMLParser:
    """解析 TIPO XML 檔案為結構化專利文件"""

    def parse_patent_xml(self, xml_path):
        # 解析 <tw-patent-grant> XML 結構
        # 提取欄位:
        return {
            'patent_number': 'I826142',
            'title': '差分分級式類比數位轉換器...',
            'abstract': '本發明提供一種...',
            'description': '【技術領域】本發明...',
            'claims': ['1. 一種類比數位轉換器...'],
            'inventor': '克里斯多福·派屈克·瑞安',
            'applicant': '美商豪威科技股份有限公司',
            'application_date': '2020-12-30',
            'publication_date': '2024-03-11',
            'ipc_classification': 'H03M1/46',
            'patent_type': 'invention',
        }
\`\`\`

**解析的專利結構**:
\`\`\`xml
<tw-patent-grant>
  <bibliographic-data>
    <publication-reference>
      <document-id>
        <doc-number>I826142</doc-number>  <!-- 專利號 -->
      </document-id>
    </publication-reference>
    <classifications-ipcr>
      <classification-ipcr>H03M1/46</classification-ipcr>  <!-- IPC分類 -->
    </classifications-ipcr>
    <parties>
      <applicants>
        <applicant>美商豪威科技股份有限公司</applicant>
      </applicants>
      <inventors>
        <inventor>克里斯多福·派屈克·瑞安</inventor>
      </inventors>
    </parties>
  </bibliographic-data>
  <abstract>本發明提供一種...</abstract>
  <description>【技術領域】本發明...</description>
  <claims>
    <claim id="1">一種類比數位轉換器...</claim>
  </claims>
</tw-patent-grant>
\`\`\`

---

## 🤖 RAG 向量處理流程

### 1. Document Processing (文件分塊)
**檔案**: \`rag/services/document_processor.py\`

\`\`\`python
class DocumentProcessor:
    """專利文件分塊處理器"""

    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,        # 每個區塊 1000 字元
            chunk_overlap=100,      # 區塊間重疊 100 字元
            separators=["\\n\\n", "\\n", ". ", " ", ""]
        )

    def process_document(self, document):
        """將專利文件分為三個部分處理"""
        parts = []

        # 1. 摘要 (Abstract)
        if document.get('abstract'):
            parts.append({
                'content': document['abstract'],
                'part': 'abstract',
                'heading': '摘要'
            })

        # 2. 說明書 (Description)
        if document.get('description'):
            parts.append({
                'content': document['description'],
                'part': 'description',
                'heading': '說明書'
            })

        # 3. 申請專利範圍 (Claims)
        if document.get('claims'):
            parts.append({
                'content': '\\n'.join(document['claims']),
                'part': 'claims',
                'heading': '申請專利範圍'
            })

        # 分塊並保留元資料
        chunks = []
        for part in parts:
            text_chunks = self.text_splitter.split_text(part['content'])

            for i, chunk_text in enumerate(text_chunks):
                chunks.append({
                    'text': chunk_text,
                    'metadata': {
                        'patent_number': document['patent_number'],
                        'title': document['title'],
                        'heading': part['heading'],
                        'part': part['part'],
                        'chunk_index': i,
                        'applicant': document['applicant'],
                        'inventor': document['inventor'],
                        'ipc_classification': document['ipc_classification'],
                    }
                })

        return chunks
\`\`\`

**分塊策略說明**:
- **chunk_size=1000**: 平衡檢索精度與語義完整性
- **chunk_overlap=100**: 避免重要資訊在區塊邊界遺失
- **分離器優先級**: 段落 → 行 → 句子 → 單詞 → 字元
- **元資料保留**: 每個區塊保留完整專利資訊,用於來源引用

**實際處理結果**:
\`\`\`
輸入: 10,746 件專利文件
輸出: 23,552 個文本區塊
平均區塊長度: 738 字元
\`\`\`

### 2. Embedding Generation (向量嵌入)
**檔案**: \`rag/services/embedding_service.py\`

\`\`\`python
from sentence_transformers import SentenceTransformer

class EmbeddingService:
    """本地嵌入向量生成服務 (無 API 費用)"""

    def __init__(self):
        # 使用輕量級模型: all-MiniLM-L6-v2
        # - 向量維度: 384
        # - 模型大小: ~90MB
        # - 速度: 快速 (適合 demo)
        # - 品質: 良好 (SBERT 預訓練)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def embed_text(self, text):
        """將文本轉換為 384 維向量"""
        return self.model.encode(text, convert_to_numpy=True)

    def embed_batch(self, texts, batch_size=32):
        """批次處理提升效率"""
        return self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )
\`\`\`

**向量模型選擇**:

| 模型 | 維度 | 大小 | 速度 | 品質 | 用途 |
|------|------|------|------|------|------|
| all-MiniLM-L6-v2 | 384 | 90MB | 快 | 良好 | **Demo (當前使用)** |
| all-mpnet-base-v2 | 768 | 420MB | 中 | 最佳 | 生產環境 |
| multilingual-e5-base | 768 | 1.1GB | 慢 | 優秀 | 多語言支援 |

### 3. Vector Storage (向量儲存)
**資料庫**: ChromaDB (輕量級向量資料庫)  
**檔案**: \`rag/services/rag_engine.py\`

\`\`\`python
import chromadb

class RAGEngine:
    """RAG 查詢引擎"""

    def __init__(self):
        # 連接 ChromaDB (Docker 容器)
        self.chroma_client = chromadb.HttpClient(
            host='chromadb',
            port=8000
        )

        # 建立或取得集合
        self.collection = self.chroma_client.get_or_create_collection(
            name="taiwan_patents",
            metadata={"description": "台灣專利向量資料庫"}
        )

        # 嵌入服務
        self.embedding_service = EmbeddingService()

    def index_chunks(self, chunks, batch_size=100):
        """批次建立索引"""
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]

            # 提取文本
            texts = [c['text'] for c in batch]

            # 生成向量 (384維)
            embeddings = self.embedding_service.embed_batch(texts)

            # 儲存到 ChromaDB
            self.collection.add(
                documents=texts,
                embeddings=embeddings.tolist(),
                metadatas=[c['metadata'] for c in batch],
                ids=[f"chunk_{i+j}" for j in range(len(batch))]
            )
\`\`\`

**ChromaDB 架構**:
\`\`\`
Collection: taiwan_patents
├── Documents: 23,552 個文本區塊
├── Embeddings: 23,552 × 384 維向量
├── Metadata: 專利號、標題、申請人、IPC 等
└── IDs: chunk_0 ~ chunk_23551
\`\`\`

**向量儲存優勢**:
- **快速檢索**: 使用 HNSW 索引,毫秒級搜尋
- **語義搜尋**: 基於向量相似度,非關鍵字匹配
- **可擴展性**: 支援百萬級文件索引
- **元資料過濾**: 可根據專利號、申請人等過濾

### 4. Query Pipeline (查詢流程)
**完整 RAG 查詢流程**:

\`\`\`python
def query(self, question, top_k=5):
    """
    RAG 查詢流程:
    1. 問題向量化
    2. 檢索相關文件
    3. 建構提示詞
    4. LLM 生成回答
    """

    # Step 1: 將問題轉為向量 (384維)
    query_embedding = self.embedding_service.embed_text(question)


    # Step 2: 向量相似度檢索 (Top-K)
    results = self.collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=top_k  # 預設檢索 5 個最相關區塊
    )

    # Step 3: 建構 Context
    context = ""
    sources = []

    for i, (doc, metadata) in enumerate(zip(results['documents'][0],
                                            results['metadatas'][0])):
        context += f"\\n[文件 {i+1}]\\n"
        context += f"專利號: {metadata['patent_number']}\\n"
        context += f"標題: {metadata['title']}\\n"
        context += f"申請人: {metadata['applicant']}\\n"
        context += f"內容: {doc}\\n"
        context += "-" * 80 + "\\n"

        sources.append({
            'patent_number': metadata['patent_number'],
            'title': metadata['title'],
            'applicant': metadata['applicant'],
            'part': metadata['heading']
        })

    # Step 4: 使用 LLM 生成回答
    prompt = f"""你是台灣專利檢索助手。請根據以下專利文件回答問題。

問題: {question}

參考文件:
{context}

請提供準確、專業的回答,並引用相關專利號。"""

    # 使用 Google Gemini Pro (免費)
    response = self.llm.predict(prompt)

    return {
        'answer': response,
        'sources': sources,
        'query_time_ms': elapsed_time
    }
\`\`\`

**檢索範例**:
\`\`\`python
# 查詢: "請找出與半導體製程相關的專利"

# 1. 向量化問題 → [0.123, -0.456, 0.789, ...]  (384維)

# 2. ChromaDB 檢索 Top-5 相關區塊:
#    - 相似度 0.87: I826142 (類比數位轉換器 - 半導體元件)
#    - 相似度 0.82: M664742 (霍爾感測器 - 半導體應用)
#    - ...

# 3. 建構 Prompt 包含 5 個專利區塊內容

# 4. Gemini 生成回答:
#    "根據檢索結果,以下專利與半導體製程相關:
#     專利 I826142 涉及類比數位轉換器..."
\`\`\`

---

## 📈 效能指標

### 資料處理效能
\`\`\`
爬取速度: ~100 檔案/分鐘 (FTPS 下載)
解析速度: ~200 專利/秒 (XML 解析)
分塊速度: ~150 專利/秒
向量化速度: ~500 區塊/秒 (batch_size=32)
索引建立: ~23,000 區塊 in 5 分鐘
\`\`\`

### 查詢效能
\`\`\`
向量檢索: ~50ms (Top-5)
LLM 生成: ~15 秒 (Gemini Pro)
端到端查詢: ~16 秒
\`\`\`

### 資源使用
\`\`\`
ChromaDB 記憶體: ~500MB (23,552 × 384維)
向量模型: 90MB (all-MiniLM-L6-v2)
原始資料: 51MB (JSON)
總儲存空間: ~640MB
\`\`\`

---

## 🔧 技術堆疊

### 後端框架
- **Django 5.0**: Web 框架
- **Django REST Framework**: API 開發

### 資料爬取
- **Playwright**: JavaScript 渲染網頁爬取
- **FTP_TLS**: Implicit FTPS 檔案下載
- **BeautifulSoup4**: HTML 解析 (備用)
- **ElementTree**: XML 解析

### RAG 核心
- **ChromaDB**: 向量資料庫
- **LangChain**: LLM 編排框架
- **Google Gemini Pro**: 大型語言模型 (gemini-2.5-flash)
- **Sentence-Transformers**: 本地嵌入模型

### 資料庫
- **PostgreSQL**: 關聯式資料庫 (查詢歷史)
- **Redis**: 快取層

### 部署
- **Docker & Docker Compose**: 容器化
- **Poetry**: Python 依賴管理

---

## 📁 資料目錄結構

\`\`\`
data/
├── README.md                          # 本文件
├── raw/                               # 原始資料
│   ├── patent_data/                   # FTPS 下載的 XML 檔案
│   │   ├── 112/                       # 2023年
│   │   │   ├── 1120101/               # 第1期
│   │   │   │   ├── I123456.xml
│   │   │   │   └── I123457.xml
│   │   │   └── 1120115/               # 第2期
│   │   ├── 113/                       # 2024年
│   │   └── 114/                       # 2025年
│   ├── demo_patents.json              # 解析後的專利資料 (10,746 件)
│   └── invention_docs.json            # DocumentProcessor 輸入格式
├── processed/                         # 處理後的資料
│   └── invention_chunks.json          # 分塊結果 (23,552 chunks)
└── vector_store/                      # ChromaDB 持久化 (如啟用)
    └── chroma.sqlite3
\`\`\`

---

## 🚀 快速開始 (面試展示)

### 1. 環境啟動
\`\`\`bash
# 啟動所有服務 (Django, ChromaDB, PostgreSQL, Redis)
docker-compose up -d

# 檢查服務狀態
docker-compose ps
\`\`\`

### 2. 資料準備 (已完成)
\`\`\`bash
# ✅ 已下載 10,746 件專利 (112-114年)
# ✅ 已處理為 23,552 個文本區塊
# ✅ 已建立向量索引
\`\`\`

### 3. 測試查詢
\`\`\`bash
# CLI 測試
python manage.py test_query "請找出台積電的半導體專利"

# Web UI 測試
# 瀏覽器開啟: http://localhost:8000/

# API 測試
curl -X POST http://localhost:8000/api/query/ \\
  -H "Content-Type: application/json" \\
  -d '{"question": "請找出與人工智慧相關的專利"}'
\`\`\`

### 4. 查看系統狀態
\`\`\`bash
# 健康檢查 API
curl http://localhost:8000/api/health/

# 回應範例:
{
  "status": "healthy",
  "vector_db": "connected",
  "total_patents": 23552,
  "collection": "taiwan_patents"
}
\`\`\`

---

## 📊 面試展示重點

### 1. 技術深度
- ✅ **三階段爬蟲**: Web Scraping → FTPS Download → XML Parsing
- ✅ **Implicit FTPS**: 客製化 FTP_TLS 處理 TIPO 特殊協定
- ✅ **向量檢索**: 使用 sentence-transformers + ChromaDB
- ✅ **語義搜尋**: 非關鍵字匹配,基於向量相似度
- ✅ **LLM 整合**: Google Gemini Pro (免費方案)

### 2. 系統架構
- ✅ **微服務設計**: Django + ChromaDB + PostgreSQL + Redis
- ✅ **Docker 容器化**: 一鍵啟動所有服務
- ✅ **RESTful API**: 標準化查詢介面
- ✅ **批次處理**: 大量資料高效處理

### 3. 資料品質
- ✅ **完整度**: 100% 標題、申請人覆蓋率
- ✅ **結構化**: 保留專利號、IPC、申請人等元資料
- ✅ **可擴展**: 支援增量更新與多年份資料

### 4. 實際應用價值
- ✅ **專利檢索**: 根據技術關鍵字找出相關專利
- ✅ **競爭分析**: 查詢特定公司的專利布局
- ✅ **技術趨勢**: 分析 IPC 分類分布
- ✅ **智慧問答**: 自然語言互動,非精確匹配

---

## 🎯 可改進方向 (面試延伸)

### 短期優化
1. **查詢效能**: 增加快取層減少重複查詢時間
2. **向量模型**: 升級至 all-mpnet-base-v2 提升檢索品質
3. **批次更新**: 定期增量爬取最新專利資料
4. **多語言支援**: 使用 multilingual 模型支援英文查詢

### 長期擴展
1. **知識圖譜**: 建立專利引用關係網路
2. **時序分析**: 技術趨勢隨時間演變
3. **圖表視覺化**: IPC 分類分布、申請人排名
4. **自動摘要**: 為長專利文件生成摘要
5. **相似專利推薦**: 基於向量相似度推薦

---

## 📝 授權與使用

- **資料來源**: 智慧財產局 (TIPO) 開放資料
- **使用限制**: 僅供學習與展示,請遵守 TIPO 使用條款
- **商業使用**: 需向 TIPO 申請授權

---

**文件更新日期**: 2025-10-25  
**系統版本**: v1.0 (Demo)  
**作者**: Patent RAG System Team
