# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Taiwan Patent RAG (Retrieval-Augmented Generation) system that searches and analyzes Taiwan patent data. Built with Django REST Framework, ChromaDB for vector storage, Google Gemini Pro (free) for LLM, and local sentence-transformers for embeddings.

This system enables intelligent search and question-answering over Taiwan Patent Office documents, allowing users to find relevant patents by keywords, technical classifications, applicants, and more.

## Development Commands

### Container Management
```bash
# Start all services
docker-compose up -d

# View Django app logs
docker-compose logs -f django-app

# Enter Django container
docker-compose exec django-app bash

# Stop all services
docker-compose down
```

### Local Development (outside Docker)
```bash
# Install dependencies with Poetry
poetry install

# Run database migrations
python manage.py migrate

# Run Django server
python manage.py runserver

# Django shell for debugging
python manage.py shell

# Code formatting with Black
poetry run black .

# Linting with Flake8
poetry run flake8

# Run tests with pytest
poetry run pytest
poetry run pytest --cov  # with coverage
```

**Environment Setup for Local Development:**
When running locally (outside Docker), update `.env` to use `localhost` instead of Docker service names:
- `POSTGRES_HOST=localhost` (instead of `postgres`)
- `CHROMA_HOST=localhost` (instead of `chromadb`)
- `REDIS_URL=redis://localhost:6379/0` (instead of `redis://redis:6379/0`)

### RAG System Initialization

**Complete setup workflow (inside container or local environment):**
```bash
# 1. Scrape Taiwan patent data from TIPO
# Three-stage process: Web scraping → FTPS download → XML parsing
python manage.py scrape_docs --section invention --latest-only --max-periods 5 --max-files-per-period 100

# Available sections: invention, utility, design, invention_pub, all

# 2. Process patent documents into chunks
python manage.py process_docs

# 3. Build vector index
python manage.py build_index --rebuild
```

**Incremental updates (add new patents or refresh):**
```bash
# Scrape additional patent types
python manage.py scrape_docs --section utility --latest-only --max-periods 3

# Scrape more periods from all years
python manage.py scrape_docs --section design --max-periods 10

# Process only new patent sections
python manage.py process_docs --sections design

# Add to existing index (without --rebuild)
python manage.py build_index --sections design
```

**Important Notes on Patent Scraping:**
- The system uses a three-stage pipeline:
  1. **Web Scraper** (Playwright): Scrapes FTPS download links from TIPO website
  2. **FTPS Downloader** (FTP_TLS): Downloads patent XML files from TIPO FTPS server
  3. **XML Parser** (ElementTree): Parses patent XML into structured documents
- `--latest-only`: Only scrapes the most recent year (faster, smaller dataset)
- `--max-periods`: Controls how many periods (issues) to scrape per year
- `--max-files-per-period`: Limits files per period to control download size
- Data is saved to `data/raw/{section}_docs.json` after parsing

### Testing
```bash
# Test query via management command
python manage.py test_query "請找出與人工智慧相關的專利"

# Run pytest tests
poetry run pytest
poetry run pytest --cov  # with coverage report

# Test via API (curl)
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{"question": "請找出與半導體製程相關的專利"}'

# Test via Web UI
# Open browser: http://localhost:8000/

# Check system health
curl http://localhost:8000/api/health/
# or open: http://localhost:8000/health-page/
```

## Architecture

### Project Structure
- **config/**: Django project configuration (settings, URLs, WSGI/ASGI)
- **rag/**: Main Django app containing all RAG functionality
  - **services/**: Core business logic (scraper, document processor, embeddings, RAG engine)
    - **scraper.py**: `TaiwanPatentScraper` - Main orchestrator for three-stage pipeline
    - **tipo_web_scraper.py**: `TIPOWebScraper` - Playwright-based web scraper for FTPS links
    - **tipo_ftps_downloader.py**: `TIPOFTPSDownloader` - FTPS file downloader using FTP_TLS
    - **tipo_xml_parser.py**: `TIPOXMLParser` - XML parser for patent documents
    - **document_processor.py**: Patent document chunking with support for patent-specific fields
    - **embedding_service.py**: Local embedding generation
    - **rag_engine.py**: Patent RAG engine with Taiwan-specific prompts
  - **management/commands/**: Django management commands for data pipeline
  - **views.py**: API endpoints (DRF) and template views
  - **serializers.py**: DRF serializers for request/response validation (includes patent_number field)
  - **urls.py**: URL routing for the rag app
- **data/**: Data storage (raw patent data, processed chunks, vector store)
- **templates/**: HTML templates for web UI

### Three-Stage Data Pipeline
1. **Scraping** (`scraper.py`):
   - Stage 1: `TIPOWebScraper` scrapes FTPS download links from TIPO website using Playwright
   - Stage 2: `TIPOFTPSDownloader` downloads XML files via FTPS (FTP over TLS)
   - Stage 3: `TIPOXMLParser` parses XML into structured patent documents
   - Output: Saves to `data/raw/{section}_docs.json`
2. **Processing** (`document_processor.py`): Chunks patent documents (abstract, description, claims) using RecursiveCharacterTextSplitter, saves to `data/processed/{section}_chunks.json`
3. **Indexing** (`rag_engine.py`): Generates embeddings and stores in ChromaDB collection "taiwan_patents"

### RAG Query Flow
The `RAGEngine.query()` method in `rag/services/rag_engine.py` executes:
1. Convert question to embedding vector (local sentence-transformers model)
2. Query ChromaDB for top-K similar patent chunks (default: 5)
3. Build context from retrieved patent chunks with metadata (patent number, applicant, etc.)
4. Generate answer using Google Gemini with Taiwan patent-specific prompt template
5. Return answer + patent source citations

### Service Layer Components
- `TaiwanPatentScraper`: Main orchestrator integrating web scraper, FTPS downloader, and XML parser
- `TIPOWebScraper`: Playwright-based web scraper for extracting FTPS download links from TIPO website
- `TIPOFTPSDownloader`: Secure FTPS file downloader using FTP_TLS for anonymous connections
- `TIPOXMLParser`: XML parser extracting patent fields (number, title, abstract, description, claims, inventor, applicant, IPC)
- `DocumentProcessor`: Patent document chunking - supports patent-specific fields with separate processing for abstract/description/claims
- `EmbeddingService`: Local sentence-transformers wrapper (no API costs)
- `RAGEngine`: Core retrieval and generation orchestration with Taiwan patent-specific prompts

### Docker Services
- **django-app** (port 8000): Django + DRF application
- **chromadb** (port 8001): Vector database for embeddings
- **postgres** (port 5432): Stores conversation history and query logs
- **redis** (port 6379): Caching layer (configured but optional)

## Configuration

### Required Environment Variables (.env)
```bash
GOOGLE_API_KEY=your-key-here  # Get free at https://makersuite.google.com/app/apikey
TAIWAN_PATENT_API_KEY=your-patent-api-key-here  # Taiwan Patent Office API key (if required)
```

### Optional RAG Parameters (can be set in .env or config/settings.py)
- `CHUNK_SIZE`: Text chunk size in characters (default: 1000)
- `CHUNK_OVERLAP`: Overlap between chunks (default: 100)
- `TOP_K_RESULTS`: Number of documents to retrieve (default: 5)
- `MAX_PAGES_TO_SCRAPE`: Max pages per section (default: 200)
- `EMBEDDING_MODEL`: Sentence-transformers model name (default: `all-MiniLM-L6-v2`)

### Dependency Management
This project uses Poetry for dependency management. Key dependencies:
- **Django 5.0+**: Web framework
- **djangorestframework**: REST API
- **chromadb**: Vector database client
- **langchain**: LLM orchestration framework
- **langchain-google-genai**: Google Gemini integration
- **sentence-transformers**: Local embedding generation
- **playwright**: Browser automation for dynamic web scraping
- **beautifulsoup4**: HTML parsing
- **psycopg2-binary**: PostgreSQL adapter

To add new dependencies:
```bash
poetry add package-name          # Add to main dependencies
poetry add --group dev package   # Add to dev dependencies
```

**After installing Playwright:**
```bash
# Install browser binaries (required for Playwright)
poetry run playwright install chromium
```

## Key Files and Locations

### Core Logic
- `rag/services/scraper.py`: TaiwanPatentScraper class - main orchestrator (scraper.py:20)
- `rag/services/tipo_web_scraper.py`: TIPOWebScraper class - Playwright web scraper (tipo_web_scraper.py:15)
- `rag/services/tipo_ftps_downloader.py`: TIPOFTPSDownloader class - FTPS downloader (tipo_ftps_downloader.py:16)
- `rag/services/tipo_xml_parser.py`: TIPOXMLParser class - XML parser (tipo_xml_parser.py:15)
- `rag/services/document_processor.py`: DocumentProcessor - patent document chunking (abstract, description, claims)
- `rag/services/rag_engine.py`: RAGEngine class - patent search and Q&A logic, collection name: "taiwan_patents"
- `rag/services/embedding_service.py`: EmbeddingService - local embeddings

### Management Commands
All in `rag/management/commands/`:
- `scrape_docs.py`: Scrape Taiwan patent data from TIPO (three-stage pipeline)
- `process_docs.py`: Create text chunks from raw docs
- `build_index.py`: Generate embeddings and populate ChromaDB
- `test_query.py`: Quick query testing

### API Endpoints
- `POST /api/query/`: Main patent query endpoint (accepts JSON with `question` field)
- `GET /api/health/`: System health check with vector DB stats (shows total indexed patents)
- `GET /`: Web UI home page with patent search form
- `POST /` (form submit): Process patent query from web form
- `GET /health-page/`: Web health check page

### Data Directories
- `data/raw/`: Raw patent data JSON files (format: `{section}_docs.json`)
- `data/processed/`: Chunked patent documents ready for embedding (format: `{section}_chunks.json`)
- `data/vector_store/`: ChromaDB persistence (if configured)

### Patent Document Structure
Expected patent data format (see `patent_scraper_template.py` for details):
```json
{
  "patent_number": "I123456",
  "title": "專利標題",
  "abstract": "專利摘要...",
  "description": "詳細說明...",
  "claims": ["請求項1...", "請求項2..."],
  "inventor": "發明人姓名",
  "applicant": "申請人/公司",
  "application_date": "2024-01-01",
  "publication_date": "2024-06-01",
  "ipc_classification": "G06F",
  "patent_type": "invention",
  "status": "granted",
  "url": "https://..."
}
```

## Development Workflow

### Implementing Patent Scraping
**IMPORTANT**: The scraper currently contains placeholder code. To implement actual patent scraping:

1. **Identify Taiwan Patent Office Data Source**:
   - Official API (if available)
   - Web scraping from https://twpat-simple.tipo.gov.tw/
   - Provided data files

2. **Implement Scraping Methods** (see `patent_scraper_template.py` for examples):
   - `scrape_patents_by_keyword()`: Search by keywords
   - `scrape_patents_by_classification()`: Search by IPC code
   - `scrape_patent_details()`: Get detailed patent information
   - `scrape_patents_by_date_range()`: Search by date range
   - `scrape_patents_by_applicant()`: Search by company/applicant

3. **Update** `TaiwanPatentScraper` in `scraper.py` with actual implementation

4. **Test scraping**:
   ```bash
   python manage.py scrape_docs --sections invention --max-pages 10
   ```

### Adding New Patent Categories
1. Update `TaiwanPatentScraper.SECTIONS` in `rag/services/scraper.py`
2. Run `scrape_docs.py` with new section name
3. Process and index as normal

### Adjusting Chunk Strategy
Modify `RecursiveCharacterTextSplitter` parameters in `document_processor.py:30`. Test impact on retrieval quality by comparing answer quality before/after changes.

### Changing LLM Provider
The system uses Google Gemini (free) by default. To switch:
1. Modify `RAGEngine.__init__()` in `rag_engine.py`
2. Update environment variables for new provider
3. Adjust patent-specific prompt template if needed (`RAGEngine.PROMPT_TEMPLATE` - currently optimized for Taiwan patent queries in Traditional Chinese)

### Testing Patent Query Quality
Use `test_query.py` management command with test patent queries. Check:
- Answer relevance and accuracy for patent searches
- Patent source citation correctness (patent numbers, applicants, etc.)
- Response time (logged in query results)
- IPC classification accuracy

Example test queries:
- "請找出與人工智慧相關的專利"
- "請找出台積電的半導體專利"
- "請找出IPC分類G06F的專利"

### Debugging Tips
- **View RAG engine logs**: Check Django logs for detailed query execution info
- **Inspect ChromaDB contents**: Use `rag_engine.get_stats()` to check indexed document count
- **Test embeddings**: Use `embedding_service.embed_text()` directly in Django shell
- **Check retrieved documents**: Call `rag_engine.retrieve_relevant_docs()` before generating answer
- **Inspect chunk quality**: Review files in `data/processed/` to verify chunking strategy

## Important Notes

- **Free Tier**: Uses Google Gemini API (free) + local embeddings (no API costs)
- **ChromaDB Connection**: System expects ChromaDB at `chromadb:8000` (Docker internal network, exposed at `localhost:8001`). Adjust `CHROMA_HOST` and `CHROMA_PORT` in .env for different setups
- **Scraper Implementation Required**: The patent scraper (`TaiwanPatentScraper`) contains placeholder code. Actual implementation depends on Taiwan Patent Office data source. See `patent_scraper_template.py` for guidance.
- **Scraper Ethics**: Built-in 0.5s delay between requests. Do not reduce without considering server impact. Respect Taiwan Patent Office usage policies.
- **Patent Chunk Metadata**: Each chunk preserves `patent_number`, `title`, `applicant`, `inventor`, `ipc_classification`, `application_date`, and other patent-specific fields for accurate source attribution
- **Collection Name**: ChromaDB collection is named `taiwan_patents` (different from original `python_docs`)
- **Collection Reset**: `build_index --rebuild` deletes existing ChromaDB collection. Omit `--rebuild` for incremental updates
- **Model Selection**: Default embedding model is `all-MiniLM-L6-v2` (384 dimensions, fast). Can be changed to `all-mpnet-base-v2` (768 dimensions, better quality) in `embedding_service.py`
- **LLM Model**: Uses `gemini-2.5-flash` by default (configured in `rag_engine.py`). Optimized for Traditional Chinese patent queries.
- **Language**: System is configured for Traditional Chinese (zh-hant), timezone: Asia/Taipei
- **Patent Data Format**: See `patent_scraper_template.py` for expected patent document structure with all required fields

## Common Issues

### ChromaDB Connection Errors
Check if ChromaDB container is running: `docker-compose ps chromadb`. Verify `CHROMA_HOST` and `CHROMA_PORT` match docker-compose.yml service name and port.

### Missing GOOGLE_API_KEY
Obtain free API key from https://makersuite.google.com/app/apikey and add to `.env` file.

### Empty Query Results / No Patents Found
1. Ensure patent data has been scraped: Check `data/raw/` for `*_docs.json` files
2. Ensure documents are processed: Check `data/processed/` for `*_chunks.json` files
3. Ensure vector index is built: `python manage.py build_index --rebuild`
4. Check ChromaDB stats via `/api/health/` endpoint - should show collection name "taiwan_patents" with document count

### Patent Scraper Not Implemented
The `TaiwanPatentScraper` requires actual implementation based on Taiwan Patent Office data source. Refer to:
- `rag/services/patent_scraper_template.py` for implementation guidance
- Taiwan Patent Office website: https://www.tipo.gov.tw/
- Patent search system: https://twpat-simple.tipo.gov.tw/

### Slow Embedding Generation
First run downloads sentence-transformers model (~90MB). Subsequent runs use cached model. Consider using lighter model like `all-MiniLM-L6-v2` in `embedding_service.py` if speed is critical.

### Chinese Encoding Issues
Ensure all files are saved with UTF-8 encoding. Patent data should use Traditional Chinese (繁體中文).
