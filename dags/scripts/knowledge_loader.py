import os
import spacy
from langchain_community.graphs import Neo4jGraph
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import boto3

# 1. Configurações
NEO4J_URI = "bolt://neo4j:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password123"

# Modelo de Embeddings focado em Português
EMBEDDING_MODEL = HuggingFaceEmbeddings(model_name="neuralmind/bert-base-portuguese-cased")

# NLP para extrair entidades (Pessoas, Organizações)
nlp = spacy.load("pt_core_news_sm")

# Conexão com S3/MinIO
s3 = boto3.client('s3', endpoint_url='http://minio:9000', 
                  aws_access_key_id='admin', aws_secret_access_key='password123')

# Conexão com Neo4j (via LangChain wrapper para facilitar)
graph = Neo4jGraph(url=NEO4J_URI, username=NEO4J_USER, password=NEO4J_PASSWORD)

def create_vector_index():
    """Cria o índice vetorial no Neo4j se não existir"""
    graph.query("""
    CREATE VECTOR INDEX text_embeddings IF NOT EXISTS
    FOR (c:Chunk) ON (c.embedding)
    OPTIONS {indexConfig: {
      `vector.dimensions`: 768,
      `vector.similarity_function`: 'cosine'
    }}
    """)

def process_document_to_graph(bucket, file_key):
    print(f"Indexando: {file_key}")
    
    # Baixar texto do Lake Silver
    obj = s3.get_object(Bucket=bucket, Key=file_key)
    text_content = obj['Body'].read().decode('utf-8')
    
    # 2. Chunking (Quebrar o texto)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""]
    )
    docs = text_splitter.create_documents([text_content])
    
    # 3. Processar cada pedaço
    for i, doc in enumerate(docs):
        chunk_text = doc.page_content
        
        # A. Gerar Embedding (Vetor)
        vector = EMBEDDING_MODEL.embed_query(chunk_text)
        
        # B. Extrair Entidades (Grafo) - Simplificado
        # Aqui extraímos nomes próprios (PER) e organizações (ORG)
        spacy_doc = nlp(chunk_text)
        entities = [(ent.text, ent.label_) for ent in spacy_doc.ents if ent.label_ in ['PER', 'ORG', 'MISC']]
        
        # C. Cypher Query: Cria o Chunk + Vetor E conecta às entidades
        cypher_query = """
        MERGE (d:Document {name: $doc_name})
        CREATE (c:Chunk {text: $text, chunk_id: $chunk_id})
        SET c.embedding = $vector
        MERGE (d)-[:HAS_CHUNK]->(c)
        
        WITH c
        UNWIND $entities as ent
        MERGE (e:Entity {name: ent[0], type: ent[1]})
        MERGE (c)-[:MENTIONS]->(e)
        """
        
        graph.query(cypher_query, params={
            "doc_name": file_key,
            "text": chunk_text,
            "chunk_id": i,
            "vector": vector,
            "entities": entities
        })
        
    print(f"Documento {file_key} ingerido no Grafo Híbrido.")

# Exemplo de execução (seria chamado pelo Airflow)
if __name__ == "__main__":
    create_vector_index()
    # Simulação: pegando um arquivo que já existe no lake
    # process_document_to_graph('lake-silver', 'processo_exemplo.txt')