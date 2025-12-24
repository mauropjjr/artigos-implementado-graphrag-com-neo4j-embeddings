from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os

default_args = {
    'owner': 'data-engineer',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(minutes=30),  # Timeout de 30 minutos por tarefa
}

def list_and_process_files():
    # Imports pesados dentro da função para evitar timeout no DagBag
    import boto3
    sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
    from ingestion_brain import process_file
    
    s3 = boto3.client(
        's3',
        endpoint_url='http://minio:9000',
        aws_access_key_id='admin',
        aws_secret_access_key='password123'
    )
    
    # Listar ficheiros no Bronze
    response = s3.list_objects_v2(Bucket='lake-bronze')
    
    if 'Contents' not in response:
        print("Nenhum ficheiro encontrado.")
        return

    # Verificar ficheiros já processados no Silver
    try:
        silver_response = s3.list_objects_v2(Bucket='lake-silver')
        processed_files = set()
        if 'Contents' in silver_response:
            for obj in silver_response['Contents']:
                # Remove .txt e reconstrói o nome original
                original_name = obj['Key'].replace('.txt', '').replace('_', '.')
                processed_files.add(original_name)
    except Exception as e:
        print(f"Aviso: Não foi possível verificar ficheiros processados: {str(e)}")
        processed_files = set()

    files_to_process = []
    for obj in response['Contents']:
        file_key = obj['Key']
        # Skip ficheiros já processados
        output_key = file_key.replace('.', '_') + ".txt"
        if output_key not in [obj['Key'] for obj in silver_response.get('Contents', [])]:
            files_to_process.append(file_key)
        else:
            print(f"Ficheiro {file_key} já processado. A saltar...")
    
    print(f"Total de ficheiros a processar: {len(files_to_process)}")
    
    for file_key in files_to_process:
        try:
            result = process_file('lake-bronze', file_key)
            print(f"Ficheiro {file_key} processado com sucesso. {result}")
        except Exception as e:
            print(f"Erro ao processar {file_key}: {str(e)}")
            import traceback
            traceback.print_exc()

def load_to_knowledge_graph():
    """Carrega documentos do Silver para o Neo4j (Knowledge Graph)."""
    import boto3
    sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
    from knowledge_loader import process_document_to_graph, create_vector_index
    from langchain_community.graphs import Neo4jGraph
    
    # Criar índice vetorial se não existir
    print("Verificando índice vetorial no Neo4j...")
    create_vector_index()
    
    s3 = boto3.client(
        's3',
        endpoint_url='http://minio:9000',
        aws_access_key_id='admin',
        aws_secret_access_key='password123'
    )
    
    # Conectar ao Neo4j para verificar documentos já indexados
    graph = Neo4jGraph(
        url="bolt://neo4j:7687",
        username="neo4j",
        password="password123"
    )
    
    # Listar ficheiros no Silver
    response = s3.list_objects_v2(Bucket='lake-silver')
    
    if 'Contents' not in response:
        print("Nenhum ficheiro encontrado no lake-silver.")
        return
    
    # Verificar quais documentos já foram indexados
    indexed_docs_query = """
    MATCH (d:Document)
    RETURN d.name as name
    """
    indexed_docs = set([record['name'] for record in graph.query(indexed_docs_query)])
    
    files_to_index = []
    for obj in response['Contents']:
        file_key = obj['Key']
        if file_key not in indexed_docs:
            files_to_index.append(file_key)
        else:
            print(f"Documento {file_key} já indexado no grafo. A saltar...")
    
    print(f"Total de documentos a indexar: {len(files_to_index)}")
    
    # Processar cada ficheiro
    for file_key in files_to_index:
        try:
            process_document_to_graph('lake-silver', file_key)
            print(f"Documento {file_key} indexado com sucesso no Knowledge Graph.")
        except Exception as e:
            print(f"Erro ao indexar {file_key}: {str(e)}")
            import traceback
            traceback.print_exc()

with DAG(
    '1_ingestao_nao_estruturada',
    default_args=default_args,
    description='Pipeline de OCR e Transcrição',
    schedule_interval='*/30 * * * *', # Corre a cada 30 min
    start_date=datetime(2025, 1, 1),
    catchup=False,
) as dag:

    ingest_task = PythonOperator(
        task_id='process_bronze_files',
        python_callable=list_and_process_files,
    )
    
    knowledge_graph_task = PythonOperator(
        task_id='load_to_knowledge_graph',
        python_callable=load_to_knowledge_graph,
    )
    
    # Definir dependência: primeiro processa os ficheiros Bronze -> Silver,
    # depois carrega para o Knowledge Graph
    ingest_task >> knowledge_graph_task
