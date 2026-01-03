
FROM python:3.11-slim

# Metadatos
LABEL maintainer="Universidad del Valle"
LABEL description="Sistema distribuido para procesamiento de Common Crawl"
LABEL version="1.0.0"

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Directorio de trabajo
WORKDIR /app

# Dependencias del sistema (gcc para compilar, libxml2 para lxml)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Estructura del proyecto
COPY src/ ./src/
COPY data/ ./data/
COPY main.py .

# Puerto dashboard Dash
EXPOSE 8050

# Comandos
# Worker: python main.py worker
# Producer: python main.py producer
# Dashboard: python main.py dashboard
CMD ["python", "main.py", "--help"]
