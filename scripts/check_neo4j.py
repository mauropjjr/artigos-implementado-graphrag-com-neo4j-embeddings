#!/usr/bin/env python3
"""Script para verificar dados no Neo4j"""

from langchain_community.graphs import Neo4jGraph

def check_neo4j_data():
    """Verifica dados gravados no Neo4j"""
    
    # Conectar ao Neo4j
    graph = Neo4jGraph(
        url="bolt://neo4j:7687",
        username="neo4j",
        password="password123"
    )
    
    print("=" * 80)
    print("VERIFICAÇÃO DO NEO4J - KNOWLEDGE GRAPH")
    print("=" * 80)
    
    # 1. Contar tipos de nós
    print("\n📊 CONTAGEM DE NÓS POR TIPO:")
    print("-" * 80)
    count_query = """
    CALL db.labels() YIELD label
    CALL {
        MATCH (n) WHERE label IN labels(n)
        RETURN count(n) as cnt
    }
    RETURN label as NodeType, cnt as Count
    ORDER BY Count DESC
    """
    try:
        results = graph.query(count_query)
        for record in results:
            node_type = record['NodeType']
            count = record['Count']
            print(f"  {node_type:20} : {count:5} nós")
    except Exception as e:
        print(f"  ⚠️  Erro ao contar nós: {str(e)}")
    
    # 2. Listar documentos
    print("\n📄 DOCUMENTOS INDEXADOS:")
    print("-" * 80)
    docs_query = """
    MATCH (d:Document)
    RETURN d.name as name, d.source as source, d.created_at as created
    ORDER BY d.created_at DESC
    LIMIT 20
    """
    docs = graph.query(docs_query)
    if docs:
        for i, doc in enumerate(docs, 1):
            print(f"  {i}. {doc['name']}")
            print(f"     Source: {doc.get('source', 'N/A')}")
            print(f"     Created: {doc.get('created', 'N/A')}")
            print()
    else:
        print("  ❌ Nenhum documento encontrado")
    
    # 3. Estatísticas de chunks
    print("\n🧩 ESTATÍSTICAS DE CHUNKS:")
    print("-" * 80)
    chunks_query = """
    MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)
    RETURN d.name as document, count(c) as num_chunks
    ORDER BY num_chunks DESC
    LIMIT 10
    """
    chunks = graph.query(chunks_query)
    if chunks:
        for record in chunks:
            print(f"  {record['document']:50} : {record['num_chunks']:3} chunks")
    else:
        print("  ❌ Nenhum chunk encontrado")
    
    # 4. Verificar índice vetorial
    print("\n🔍 ÍNDICES VETORIAIS:")
    print("-" * 80)
    index_query = """
    SHOW INDEXES
    """
    try:
        indexes = graph.query(index_query)
        vector_indexes = [idx for idx in indexes if idx.get('type') == 'VECTOR']
        if vector_indexes:
            for idx in vector_indexes:
                print(f"  ✅ {idx['name']}")
                print(f"     Type: {idx.get('type', 'N/A')}")
                print(f"     Entity Type: {idx.get('entityType', 'N/A')}")
        else:
            print("  ⚠️  Nenhum índice vetorial encontrado")
    except Exception as e:
        print(f"  ⚠️  Erro ao verificar índices: {str(e)}")
    
    # 5. Exemplo de chunk
    print("\n📝 EXEMPLO DE CHUNK (primeiro chunk encontrado):")
    print("-" * 80)
    sample_query = """
    MATCH (c:Chunk)
    RETURN c.text as text, c.chunk_id as id
    LIMIT 1
    """
    samples = graph.query(sample_query)
    if samples:
        chunk = samples[0]
        text = chunk['text'][:200] + "..." if len(chunk['text']) > 200 else chunk['text']
        print(f"  ID: {chunk['id']}")
        print(f"  Text: {text}")
    else:
        print("  ❌ Nenhum chunk encontrado")
    
    # 6. Relacionamentos
    print("\n🔗 TIPOS DE RELACIONAMENTOS:")
    print("-" * 80)
    rel_query = """
    CALL db.relationshipTypes() YIELD relationshipType
    CALL {
        MATCH ()-[r]->() WHERE type(r) = relationshipType
        RETURN count(r) as cnt
    }
    RETURN relationshipType as RelType, cnt as Count
    ORDER BY Count DESC
    """
    try:
        rels = graph.query(rel_query)
        if rels:
            for rel in rels:
                print(f"  {rel['RelType']:20} : {rel['Count']:5} relacionamentos")
        else:
            print("  ❌ Nenhum relacionamento encontrado")
    except Exception as e:
        print(f"  ⚠️  Erro ao contar relacionamentos: {str(e)}")
    
    print("\n" + "=" * 80)
    print("✅ Verificação concluída!")
    print("=" * 80)

if __name__ == "__main__":
    try:
        check_neo4j_data()
    except Exception as e:
        print(f"❌ Erro ao conectar ao Neo4j: {str(e)}")
        import traceback
        traceback.print_exc()
