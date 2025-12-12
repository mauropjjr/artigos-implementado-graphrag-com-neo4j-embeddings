# O Caos em Ordem – Engenharia de Ingestão com OCR e Transcrição de Áudio

![Arquitetura](https://img.shields.io/badge/Arquitetura-Data%20Lake-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-green)
![Airflow](https://img.shields.io/badge/Airflow-2.9.0-red)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)

Este projeto é a **continuação natural** do artigo [Construindo Data Lake para IA Generativa](https://github.com/mauropjjr/artigos-contruindo-data-like-para-ia-generativa), onde agora implementamos a **camada de ingestão inteligente** que transforma dados não estruturados (PDFs, imagens, áudio) em texto processável para Agentes de IA.

## 🎯 O Desafio Técnico

O Agente de IA é "cego" e "surdo". Ele só entende texto. O trabalho do Engenheiro de Dados nesta fase é criar um **pipeline de transformação robusto** que:

1. **Deteta** um novo ficheiro na zona de aterragem (`lake-bronze`)
2. **Identifica** o tipo: É um PDF imagem? É um ficheiro `.mp3`?
3. **Aplica** a ferramenta correta:
   - **Tesseract OCR** para imagens e PDFs digitalizados
   - **OpenAI Whisper** para transcrição de áudio
4. **Guarda** o resultado limpo na zona processada (`lake-silver`)

## 🏗️ Arquitetura da Solução

```
┌─────────────────────────────────────────────────────────────┐
│                     ENTRADA (Bronze)                         │
│  📄 PDFs Digitalizados │ 🎤 Áudio de Reuniões │ 📷 Imagens  │
└────────────────────────┬────────────────────────────────────┘
                         │
                    ┌────▼────┐
                    │ Airflow │ ◄── Orquestração a cada 30 min
                    └────┬────┘
                         │
            ┌────────────┴────────────┐
            │                         │
       ┌────▼────┐              ┌────▼────┐
       │Tesseract│              │ Whisper │
       │   OCR   │              │  (IA)   │
       └────┬────┘              └────┬────┘
            │                         │
            └────────────┬────────────┘
                         │
                    ┌────▼────┐
                    │  Silver │ ◄── Texto Limpo e Estruturado
                    └─────────┘
                         │
                    ┌────▼────┐
                    │  Gold   │ ◄── (Próximo Artigo: Vetorização)
                    └─────────┘
```

## 🚀 Stack Tecnológica

| Componente | Tecnologia | Função |
|------------|-----------|--------|
| **Orquestração** | Apache Airflow 2.9.0 | Agendamento e monitorização de pipelines |
| **Armazenamento** | MinIO (S3-compatible) | Data Lake com camadas Bronze/Silver/Gold |
| **OCR** | Tesseract + PyTesseract | Extração de texto de imagens e PDFs |
| **Transcrição** | OpenAI Whisper | Conversão de áudio em texto (suporta PT-BR) |
| **Infraestrutura** | Docker Compose | Containerização e isolamento de dependências |
| **Processamento PDF** | pdf2image + Poppler | Conversão de PDF em imagens para OCR |

## 📋 Pré-requisitos

- **Docker** e **Docker Compose** instalados
- **8GB de RAM** (mínimo recomendado para o Whisper)
- **10GB de espaço em disco** livre

## ⚙️ Instalação e Configuração

### 1. Clone o Repositório

```bash
git clone https://github.com/mauropjjr/artigos-ingestao-comocr-transcricao-audio.git
cd artigos-ingestao-comocr-transcricao-audio
```

### 2. Configure as Variáveis de Ambiente

O ficheiro `.env` já está configurado com valores padrão seguros para desenvolvimento:

```bash
AIRFLOW_UID=50000
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow
```

### 3. Construa e Inicie os Serviços

```bash
# Construir a imagem customizada do Airflow com dependências de OCR/Whisper
docker compose build

# Iniciar todos os serviços (Airflow, MinIO, PostgreSQL)
docker compose up -d
```

**Tempo estimado**: 5-10 minutos na primeira execução (download de modelos do Whisper).

### 4. Verifique os Serviços

Aceda às interfaces web:

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **Airflow UI** | http://localhost:8080 | `airflow` / `airflow` |
| **MinIO Console** | http://localhost:9001 | `admin` / `password123` |

### 5. Ativar a DAG no Airflow

1. Aceda ao Airflow UI (http://localhost:8080)
2. Faça login com as credenciais padrão
3. Localize a DAG `1_ingestao_nao_estruturada`
4. Clique no botão de **toggle** para ativá-la
5. A DAG irá executar automaticamente a cada 30 minutos

## 🧪 Teste o Pipeline

### Cenário: Escritório de Contabilidade

Vamos simular um caso real onde precisamos processar:
- 📄 Uma nota fiscal digitalizada (imagem de qualidade média)
- 🎤 Uma gravação de reunião com cliente

### 1. Preparar Ficheiros de Teste

Coloque os ficheiros no bucket **lake-bronze** via MinIO Console:

1. Aceda a http://localhost:9001
2. Login: `admin` / `password123`
3. Navegue até o bucket `lake-bronze`
4. Faça upload de:
   - `nota_fiscal_1998.pdf` (PDF digitalizado)
   - `reuniao_cliente_silva.mp3` (áudio de reunião)

### 2. Aguardar Processamento

O Airflow irá:
1. Detectar os novos ficheiros
2. **PDF**: Converter para imagem → Aplicar OCR → Extrair texto
3. **MP3**: Carregar modelo Whisper → Transcrever áudio → Gerar texto
4. Salvar resultados em `lake-silver/` como:
   - `nota_fiscal_1998_pdf.txt`
   - `reuniao_cliente_silva_mp3.txt`

### 3. Verificar Resultados

No MinIO Console, navegue até `lake-silver` e descarregue os ficheiros `.txt` gerados.

**Exemplo de saída OCR** (`nota_fiscal_1998_pdf.txt`):
```
--- Pagina 1 ---
NOTA FISCAL
Série: 001  Número: 12345
Data: 15/03/1998

Razão Social: EMPRESA XYZ LTDA
CNPJ: 12.345.678/0001-99

DESCRIÇÃO          VALOR
Consultoria Fiscal  R$ 1.500,00
ICMS (18%)          R$ 270,00
TOTAL               R$ 1.770,00
```

**Exemplo de saída Whisper** (`reuniao_cliente_silva_mp3.txt`):
```
O cliente Silva está preocupado com a tributação do ICMS sobre
as operações interestaduais realizadas no segundo trimestre de
2024. Ele mencionou que houve uma mudança na alíquota...
```

## 🔍 Estrutura do Projeto

```
.
├── dags/
│   ├── ingestion_pipeline.py        # DAG principal do Airflow
│   └── scripts/
│       └── ingestion_brain.py       # Lógica de OCR e Transcrição
├── logs/                             # Logs do Airflow
├── plugins/                          # Plugins customizados (vazio)
├── docker-compose.yml                # Orquestração de containers
├── Dockerfile                        # Imagem customizada do Airflow
├── .env                              # Variáveis de ambiente
└── README.md                         # Este ficheiro
```

## 🧠 Como Funciona o Código

### Pipeline de Decisão (`ingestion_brain.py`)

```python
def process_file(bucket_name, file_key):
    # 1. Download do ficheiro
    local_path = f"/tmp/{file_key.split('/')[-1]}"
    s3_client.download_file(bucket_name, file_key, local_path)
    
    file_ext = local_path.split('.')[-1].lower()
    
    # 2. Roteamento inteligente
    if file_ext in ['pdf', 'png', 'jpg', 'jpeg']:
        extracted_text = _run_ocr(local_path)      # Tesseract
    elif file_ext in ['mp3', 'wav', 'mp4', 'm4a']:
        extracted_text = _run_transcription(local_path)  # Whisper
    
    # 3. Persistência no Silver
    s3_client.put_object(
        Bucket='lake-silver',
        Key=output_key,
        Body=extracted_text.encode('utf-8')
    )
```

### OCR Multi-página

```python
def _run_ocr(file_path):
    if file_path.endswith('.pdf'):
        images = convert_from_path(file_path)  # Poppler
        full_text = ""
        for i, img in enumerate(images):
            text = pytesseract.image_to_string(img, lang='por')
            full_text += f"\n--- Pagina {i+1} ---\n{text}"
        return full_text
```

### Transcrição com IA

```python
def _run_transcription(file_path):
    model = whisper.load_model("base")  # 74M parâmetros
    result = model.transcribe(file_path, language='pt')
    return result["text"]
```

## 🎛️ Configurações Avançadas

### Melhorar Qualidade de Transcrição

No `ingestion_brain.py`, altere o modelo Whisper:

```python
# Padrão (rápido, 74M parâmetros)
model = whisper.load_model("base")

# Alta qualidade (requer GPU, 1550M parâmetros)
model = whisper.load_model("large")
```

### Suportar Mais Idiomas no OCR

No `Dockerfile`, adicione pacotes de idiomas:

```dockerfile
RUN apt-get install -y \
    tesseract-ocr-eng \
    tesseract-ocr-spa \
    tesseract-ocr-fra
```

E no código:
```python
text = pytesseract.image_to_string(img, lang='por+eng')  # PT + EN
```

### Ajustar Frequência de Execução

No `ingestion_pipeline.py`:

```python
with DAG(
    ...
    schedule_interval='*/5 * * * *',  # A cada 5 minutos
    # ou
    schedule_interval='@hourly',       # A cada hora
    # ou
    schedule_interval='0 2 * * *',     # Diariamente às 2h AM
) as dag:
```

## 🐛 Troubleshooting

### Erro: "Tesseract not found"

**Causa**: O container não instalou o Tesseract corretamente.

**Solução**:
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Erro: "Out of memory" durante transcrição

**Causa**: Áudio muito longo ou modelo `large` sem GPU.

**Solução**:
1. Use o modelo `tiny` ou `base`
2. Aumente a memória do Docker (Settings → Resources → Memory → 8GB)

### Ficheiros não são processados

**Verificações**:
1. A DAG está ativa no Airflow?
2. Os ficheiros estão realmente em `lake-bronze`?
3. Verifique os logs: Airflow UI → DAGs → `1_ingestao_nao_estruturada` → Graph → Logs

### MinIO não inicia

**Causa**: Portas 9000/9001 em uso.

**Solução**:
```bash
# Verificar processos na porta
netstat -ano | findstr :9000

# Alterar portas no docker-compose.yml
ports:
  - "9002:9000"  # API
  - "9003:9001"  # Console
```

## 📊 Monitorização

### Métricas do Airflow

Aceda a **Admin → Monitoring** no Airflow UI para ver:
- Taxa de sucesso/falha das DAGs
- Tempo médio de execução
- Uso de recursos (CPU/Memória)

### Logs Detalhados

```bash
# Ver logs do scheduler
docker compose logs -f airflow-scheduler

# Ver logs de uma tarefa específica
docker compose exec airflow-webserver \
  airflow tasks logs 1_ingestao_nao_estruturada process_bronze_files 2024-01-15
```

## 🔐 Segurança em Produção

⚠️ **IMPORTANTE**: As credenciais padrão são apenas para desenvolvimento!

### Checklist para Produção:

- [ ] Alterar credenciais do MinIO (`MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`)
- [ ] Alterar senha do Airflow (`_AIRFLOW_WWW_USER_PASSWORD`)
- [ ] Usar variáveis de ambiente para credenciais (não hardcoded)
- [ ] Habilitar HTTPS no MinIO e Airflow
- [ ] Implementar controlo de acesso baseado em roles (RBAC)
- [ ] Encriptar dados sensíveis no Data Lake
- [ ] Configurar backups regulares do PostgreSQL e MinIO

## 🚀 Próximos Passos

Este projeto estabelece a **camada de ingestão**, mas o texto bruto ainda não é pesquisável semanticamente. No **próximo artigo** da série, iremos:

1. **Vetorizar** o texto extraído usando modelos de embedding (OpenAI Ada, Sentence Transformers)
2. **Indexar** no Pinecone/Qdrant para busca semântica
3. **Implementar** RAG (Retrieval-Augmented Generation) para consultas em linguagem natural
4. **Criar** um Agente de IA que responde perguntas como:
   - "Quais clientes têm pendências fiscais de ICMS?"
   - "Resumo das reuniões de Janeiro sobre ISS"

## 📚 Referências

- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [OpenAI Whisper](https://github.com/openai/whisper)
- [MinIO Python SDK](https://min.io/docs/minio/linux/developers/python/minio-py.html)
- [Artigo Anterior: Data Lake para IA](https://github.com/mauropjjr/artigos-contruindo-data-like-para-ia-generativa)


## 📝 Licença

Este projeto está sob a licença MIT. Veja o ficheiro [LICENSE](LICENSE) para mais detalhes.

## 👨‍💻 Autor

**Mauro Pichiliani Jr.**
- GitHub: [@mauropjjr](https://github.com/mauropjjr)
- LinkedIn: [Mauro Junior.](https://linkedin.com/in/mauropjjr)

---

⭐ Se este projeto foi útil, considere dar uma estrela no GitHub!
