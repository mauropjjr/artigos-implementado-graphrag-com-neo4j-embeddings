FROM apache/airflow:2.9.0

USER root

# 1. Instalar dependências de sistema (OCR e Processamento de Áudio)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-por \
    ffmpeg \
    libsm6 \
    libxext6 \
    poppler-utils \
    && apt-get autoremove -yqq --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# 2. Instalar bibliotecas Python para IA e Dados
RUN pip install --no-cache-dir \
    apache-airflow-providers-amazon \
    pytesseract \
    pdf2image \
    openai-whisper \
    torchaudio \
    torch \
    numpy \
    pandas \
    boto3 \
    spacy \
    langchain \
    langchain-community \
    langchain-huggingface \
    langchain-text-splitters \
    langchain-core \
    neo4j \
    sentence-transformers

# 3. Baixar modelo spaCy para Português
RUN python -m spacy download pt_core_news_sm
