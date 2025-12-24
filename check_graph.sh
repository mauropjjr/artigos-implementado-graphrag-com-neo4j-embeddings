#!/bin/bash
# Script para verificar dados no Neo4j via container Airflow

echo "Verificando dados no Neo4j..."
docker exec -it artigos-ingestao-comocr-transcricao-audio-airflow-webserver-1 \
    python /opt/airflow/dags/scripts/../scripts/check_neo4j.py
