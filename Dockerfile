FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Poetry
RUN pip install poetry

# 複製依賴文件
COPY pyproject.toml poetry.lock* ./

# 配置 Poetry 不建立虛擬環境（因為已在容器中）
RUN poetry config virtualenvs.create false

# 安裝 Python 依賴
RUN poetry install --no-interaction --no-ansi --no-root --only main

# 複製專案文件
COPY . /app

# 建立資料目錄
RUN mkdir -p /app/data/raw /app/data/processed /app/data/vector_store

# 暴露端口
EXPOSE 8000

# 預設啟動命令
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
