#!/usr/bin/env python3
"""Script para carregar documentos do Silver para o Neo4j Knowledge Graph"""

import boto3
import os
import sys
from langchain_community.graphs import Neo4jGraph
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase
import spacy
import json
from datetime import datetime

# Carregar modelo spaCy para português
nlp = spacy.load("pt_core_news_sm")

# Modelo de embeddings
embedder = SentenceTransformer('all-MiniLM-L6-v2')

def create_vector_index():
    """Cria índice vetorial no Neo4j se não existir"""
    driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "password123"))
    
    with driver.session() as session:
        # Verificar se o índice já existe
        result = session.run("SHOW INDEXES WHERE name = 'document_chunks'")
        if not result.single():
            # Criar índice vetorial
            session.run("""
            CREATE VECTOR INDEX document_chunks IF NOT EXISTS
            FOR (c:Chunk) ON (c.embedding)
            OPTIONS {indexConfig: {
                `vector.dimensions`: 384,
                `vector.similarity_function`: 'cosine'
            }}
            """)
            print("Índice vetorial 'document_chunks' criado.")
        else:
            print("Índice vetorial 'document_chunks' já existe.")
    
    driver.close()

def extract_entities(text):
    """Extrai entidades nomeadas usando spaCy"""
    doc = nlp(text)
    entities = []
    
    for ent in doc.ents:
        entities.append({
            'text': ent.text,
            'label': ent.label_,
            'start': ent.start_char,
            'end': ent.end_char
        })
    
    return entities

def split_text_into_chunks(text, chunk_size=1000, chunk_overlap=200):
    """Divide o texto em chunks usando LangChain"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    chunks = text_splitter.split_text(text)
    return chunks

def process_document_to_graph(bucket_name, file_key):
    """Processa um documento do Silver e carrega para o Neo4j"""
    
    # Cliente S3
    s3 = boto3.client(
        's3',
        endpoint_url='http://minio:9000',
        aws_access_key_id='admin',
        aws_secret_access_key='password123'
    )
    
    # Conectar ao Neo4j
    graph = Neo4jGraph(
        url="bolt://neo4j:7687",
        username="neo4j",
        password="password123"
    )
    
    # Download do documento
    local_path = f"/tmp/{file_key}"
    s3.download_file(bucket_name, file_key, local_path)
    
    with open(local_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Limpar arquivo temporário
    os.remove(local_path)
    
    # 1. Criar nó do Documento
    doc_query = """
    MERGE (d:Document {name: $name})
    SET d.source = $source,
        d.created_at = $created_at,
        d.content_length = $content_length
    """
    
    graph.query(doc_query, {
        'name': file_key,
        'source': bucket_name,
        'created_at': datetime.now().isoformat(),
        'content_length': len(text)
    })
    
    # 2. Dividir texto em chunks
    chunks = split_text_into_chunks(text)
    
    # 3. Processar cada chunk
    for i, chunk in enumerate(chunks):
        # Gerar embedding
        embedding = embedder.encode(chunk).tolist()
        
        # Extrair entidades
        entities = extract_entities(chunk)
        
        # Criar nó do Chunk
        chunk_query = """
        MATCH (d:Document {name: $doc_name})
        CREATE (c:Chunk {
            id: $chunk_id,
            content: $content,
            embedding: $embedding,
            position: $position
        })
        CREATE (d)-[:HAS_CHUNK]->(c)
        """
        
        graph.query(chunk_query, {
            'doc_name': file_key,
            'chunk_id': f"{file_key}_chunk_{i}",
            'content': chunk,
            'embedding': embedding,
            'position': i
        })
        
        # 4. Criar nós de entidades e relacionamentos
        for entity in entities:
            # Criar nó da entidade
            entity_query = """
            MERGE (e:Entity {text: $text, label: $label})
            """
            graph.query(entity_query, {
                'text': entity['text'],
                'label': entity['label']
            })
            
            # Relacionar chunk com entidade
            relation_query = """
            MATCH (c:Chunk {id: $chunk_id})
            MATCH (e:Entity {text: $text, label: $label})
            MERGE (c)-[:MENTIONS]->(e)
            """
            graph.query(relation_query, {
                'chunk_id': f"{file_key}_chunk_{i}",
                'text': entity['text'],
                'label': entity['label']
            })
    
    print(f"Documento {file_key} processado: {len(chunks)} chunks, {sum(len(extract_entities(chunk)) for chunk in chunks)} entidades extraídas.")

if __name__ == "__main__":
    # Para testes locais
    if len(sys.argv) > 1:
        bucket = sys.argv[1]
        file_key = sys.argv[2]
        process_document_to_graph(bucket, file_key)
    else:
        print("Uso: python knowledge_loader.py <bucket> <file_key>")