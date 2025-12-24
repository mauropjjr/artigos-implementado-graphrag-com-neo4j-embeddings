# Arquitetura do Sistema

## Visão Geral

Este sistema implementa um pipeline de ingestão de dados não estruturados para alimentar sistemas de IA Generativa. A arquitetura segue o padrão **Medallion Architecture** (Bronze → Silver → Gold) comumente usado em Data Lakes modernos.

## Camadas do Data Lake

### 🥉 Bronze (Raw/Landing Zone)
- **Propósito**: Armazenamento bruto de ficheiros recém-chegados
- **Formatos**: PDF, imagens (JPG, PNG), áudio (MP3, WAV, M4A)
- **Características**:
  - Dados imutáveis (append-only)
  - Sem transformações aplicadas
  - Retenção de metadados originais

### 🥈 Silver (Processed/Cleaned Zone)
- **Propósito**: Dados transformados e limpos
- **Formato**: Texto puro (UTF-8)
- **Transformações Aplicadas**:
  - OCR (Tesseract) para documentos visuais
  - Transcrição (Whisper) para áudio
  - Limpeza básica de caracteres especiais
- **Características**:
  - Dados estruturados em texto
  - Indexados por timestamp
  - Prontos para vetorização

### 🥇 Gold (Analytics/Serving Zone)
- **Propósito**: Dados otimizados para consumo e busca inteligente
- **Formatos**: 
  - Vetores de embedding (384 dimensões)
  - Grafo de conhecimento (Neo4j)
  - Metadados estruturados
- **Componentes**:
  - **Embeddings**: Sentence Transformers para busca semântica
  - **Entidades**: Extração NER com spaCy (PERSON, ORG, LOC)
  - **Grafo**: Relacionamentos entre documentos, chunks e entidades
- **Uso**: Busca semântica, RAG, Agentes de IA, análise de relacionamentos

## Componentes Técnicos

### Apache Airflow
```
┌─────────────────────────────────────┐
│          Airflow Scheduler          │
│  - Monitora DAGs                    │
│  - Executa tarefas a cada 30 min    │
│  - Gerencia dependências            │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│       Airflow Webserver (UI)        │
│  - Dashboard de monitorização       │
│  - Logs e troubleshooting           │
│  - Controlo manual de execuções     │
└─────────────────────────────────────┘
```

### Neo4j (Knowledge Graph)
```
┌─────────────────────────────────────┐
│         Neo4j Graph Database        │
│                                     │
│  ┌─────────┐  ┌─────────┐  ┌─────┐│
│  │Document │  │ Chunk   │  │Entity││
│  │ Nodes   │←→│ Nodes   │←→│Nodes││
│  └─────────┘  └─────────┘  └─────┘│
│                                     │
│  Vector Index: document_chunks      │
│  Relationships: HAS_CHUNK, MENTIONS│
│                                     │
│  Bolt Protocol: :7687               │
│  HTTP Console:  :7474               │
└─────────────────────────────────────┘
```

### Pipeline de Processamento

```
                 ┌──────────────────┐
     Upload      │  lake-bronze/    │
  ─────────────→ │  documento.pdf   │
   (MinIO UI)    └────────┬─────────┘
                          │
                ┌─────────▼──────────┐
                │  Airflow Sensor    │
                │  (detecta novos)   │
                └─────────┬──────────┘
                          │
              ┌───────────▼────────────┐
              │  ingestion_brain.py    │
              │                        │
              │  ┌──────────────────┐  │
              │  │ Identificador de │  │
              │  │ Tipo de Ficheiro │  │
              │  └────────┬─────────┘  │
              │           │            │
              │    ┌──────▼──────┐     │
              │    │  Roteador   │     │
              │    └──┬──────┬───┘     │
              └───────┼──────┼─────────┘
                      │      │
         ┌────────────┘      └────────────┐
         │                                │
    ┌────▼─────┐                   ┌─────▼─────┐
    │Tesseract │                   │  Whisper  │
    │   OCR    │                   │    STT    │
    └────┬─────┘                   └─────┬─────┘
         │                                │
         └────────────┬────────────────────┘
                      │
              ┌───────▼────────┐
              │  lake-silver/  │
              │  documento.txt │
              └───────┬────────┘
                      │
              ┌───────▼────────┐
              │knowledge_loader│
              │     .py        │
              │                │
              │ ┌────────────┐ │
              │ │Text Chunking│ │
              │ │(LangChain)  │ │
              │ └─────┬──────┘ │
              │       │        │
              │ ┌─────▼─────┐  │
              │ │Embeddings  │  │
              │ │(Sentence   │  │
              │ │Transformers│  │
              │ └─────┬─────┘  │
              │       │        │
              │ ┌─────▼─────┐  │
              │ │Entity NER  │  │
              │ │(spaCy)     │  │
              │ └─────┬─────┘  │
              │       │        │
              └───────┼────────┘
                      │
              ┌───────▼────────┐
              │   Neo4j Graph   │
              │ Knowledge Base │
              └────────────────┘
```

## Fluxo de Dados Detalhado

### 1. Detecção de Ficheiros
```python
# ingestion_pipeline.py - list_and_process_files()
response = s3.list_objects_v2(Bucket='lake-bronze')
for obj in response['Contents']:
    process_file('lake-bronze', obj['Key'])
```

### 2. Decisão de Processamento
```python
# ingestion_brain.py - process_file()
file_ext = local_path.split('.')[-1].lower()

if file_ext in ['pdf', 'png', 'jpg']:
    extracted_text = _run_ocr(local_path)
elif file_ext in ['mp3', 'wav', 'm4a']:
    extracted_text = _run_transcription(local_path)
```

### 3. Extração de Texto

#### OCR (Tesseract)
```
PDF → pdf2image → PIL Image → Tesseract → Texto
```

#### Transcrição (Whisper)
```
Áudio → FFmpeg → Mel Spectrogram → Whisper Neural Net → Texto
```

### 4. Persistência
```python
s3_client.put_object(
    Bucket='lake-silver',
    Key=output_key,
    Body=extracted_text.encode('utf-8')
)
```

### 5. Ingestão no Knowledge Graph
```python
# knowledge_loader.py - process_document_to_graph()
chunks = split_text_into_chunks(text)
for chunk in chunks:
    embedding = embedder.encode(chunk)
    entities = extract_entities(chunk)
    # Criar nós no Neo4j
    create_chunk_node(chunk, embedding)
    create_entity_nodes(entities)
    create_relationships(chunk, entities)
```

## Estrutura do Knowledge Graph

### Nós Principais
- **Document**: Representa ficheiros originais
  - Propriedades: `name`, `source`, `created_at`, `content_length`
- **Chunk**: Segmentos de texto com embeddings
  - Propriedades: `id`, `content`, `embedding`, `position`
- **Entity**: Entidades nomeadas extraídas
  - Propriedades: `text`, `label` (PERSON, ORG, LOC, etc.)

### Relacionamentos
- `Document → HAS_CHUNK → Chunk`
- `Chunk → MENTIONS → Entity`

### Índice Vetorial
```cypher
CREATE VECTOR INDEX document_chunks
FOR (c:Chunk) ON (c.embedding)
OPTIONS {indexConfig: {
    `vector.dimensions`: 384,
    `vector.similarity_function`: 'cosine'
}}
```

## Estratégia Híbrida: Vetorial + Grafo

### Busca Semântica (Embeddings)
- **Vantagem**: Busca por similaridade de significado
- **Uso**: Queries como "documentos sobre tributação"
- **Implementação**: Sentence Transformers + Neo4j Vector Index

### Análise de Relacionamentos (Grafo)
- **Vantagem**: Descoberta de conexões entre entidades
- **Uso**: Queries como "quais pessoas estão relacionadas com empresa X"
- **Implementação**: Cypher queries + Graph algorithms

### Casos de Uso Combinados
1. **RAG Contextual**: Busca vetorial + recuperação de contexto via grafo
2. **Análise de Rede**: Mapear relacionamentos entre entidades
3. **Descoberta de Padrões**: Identificar clusters e comunidades

## Escalabilidade

### Horizontal
- **Airflow Workers**: Adicionar múltiplos workers para processamento paralelo
- **MinIO Cluster**: Distribuir armazenamento em múltiplos nós

### Vertical
- **GPU para Whisper**: Usar modelo `large` com CUDA
- **Mais RAM**: Processar ficheiros maiores sem swap

### Otimizações Futuras
1. **Processamento em Stream**: Para ficheiros muito grandes
2. **Cache de Modelos**: Manter Whisper em memória entre execuções
3. **Particionamento**: Dividir processamento por tipo de ficheiro
4. **Dead Letter Queue**: Para ficheiros que falharam processamento

## Segurança

### Camada de Rede
```
Internet → Firewall → Reverse Proxy (Nginx) → Airflow/MinIO
                              ↓
                            TLS/SSL
```

### Controlo de Acesso
- **MinIO**: IAM Policies (S3-compatible)
- **Airflow**: RBAC (Role-Based Access Control)
- **PostgreSQL**: Credenciais encriptadas

### Auditoria
- Logs de acesso ao MinIO
- Logs de execução do Airflow
- Tracking de modificações de ficheiros

## Monitorização

### Métricas-Chave
- **Latência de Processamento**: Tempo entre upload e texto extraído
- **Taxa de Erro**: % de ficheiros que falharam processamento
- **Throughput**: Ficheiros processados por hora
- **Utilização de Recursos**: CPU, RAM, Disco

### Alertas Recomendados
- ⚠️ Fila de ficheiros > 100 (possível bottleneck)
- ⚠️ Taxa de erro > 5%
- ⚠️ Disco MinIO > 80% de utilização
- ⚠️ Airflow scheduler não executa há > 10 min

## Comparação com Alternativas

| Componente | Escolhido | Alternativa | Motivo da Escolha |
|------------|-----------|-------------|-------------------|
| Orquestração | Airflow | Prefect, Dagster | Maturidade, comunidade |
| Armazenamento | MinIO | AWS S3, Azure Blob | Custo, privacidade local |
| OCR | Tesseract | AWS Textract | Open-source, sem custos API |
| Transcrição | Whisper | Google Speech-to-Text | Qualidade PT-BR, offline |
| Base de Dados | PostgreSQL | MySQL, MongoDB | Suporte nativo Airflow |
| Knowledge Graph | Neo4j | Amazon Neptune, JanusGraph | Cypher query language, vector search integrado |
| Embeddings | Sentence Transformers | OpenAI Ada | Open-source, sem custos API, português |
| NER | spaCy | AWS Comprehend | Biblioteca madura, modelo PT-BR |
