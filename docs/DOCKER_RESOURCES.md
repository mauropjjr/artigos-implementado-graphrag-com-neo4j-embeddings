# Configuração de Recursos do Docker Desktop

## Problema
Quando você executa `docker-compose up -d`, toda a stack consome muita memória e pode derrubar o Docker Desktop.

## Consumo de Recursos Estimado

| Serviço | Memória Reservada | Memória Limite |
|---------|-------------------|----------------|
| PostgreSQL | 256MB | 512MB |
| Airflow Webserver | 1GB | 2GB |
| Airflow Scheduler | 1GB | 2GB |
| MinIO | 256MB | 512MB |
| Neo4j | 768MB | 1.5GB |
| **TOTAL** | **~3.3GB** | **~6.5GB** |

## Solução 1: Aumentar Recursos do Docker Desktop (RECOMENDADO)

### Windows:
1. Abra o **Docker Desktop**
2. Clique no ícone de engrenagem (Settings)
3. Vá em **Resources** > **Advanced**
4. Configure:
   - **Memory**: Mínimo **8 GB** (ideal: 12 GB ou mais)
   - **CPUs**: Mínimo **4 CPUs**
   - **Swap**: 2 GB
   - **Disk image size**: 60 GB (se possível)
5. Clique em **Apply & Restart**

## Solução 2: Subir Serviços Gradualmente

Se você não tem 8GB disponíveis para o Docker, suba os serviços em etapas:

```bash
# 1. Primeiro, serviços essenciais
docker-compose up -d postgres minio

# 2. Aguarde 30 segundos, depois Neo4j
docker-compose up -d neo4j

# 3. Aguarde 30 segundos, depois Airflow
docker-compose up -d airflow-webserver airflow-scheduler
```

## Solução 3: Reduzir Memória do Neo4j (Emergencial)

Se ainda tiver problemas, edite o `docker-compose.yml` e reduza a memória do Neo4j:

```yaml
NEO4J_server_memory_heap_initial__size: 256m
NEO4J_server_memory_heap_max__size: 512m
```

E ajuste os limites:
```yaml
deploy:
  resources:
    limits:
      memory: 768M
    reservations:
      memory: 384M
```

## Solução 4: Desabilitar Graph Data Science (GDS)

O plugin GDS do Neo4j consome muita memória. Se não for essencial, remova:

```yaml
NEO4J_PLUGINS: '["apoc"]'  # Remove "graph-data-science"
```

## Monitoramento

Após subir os containers, monitore o uso de recursos:

```bash
# Ver uso de memória de todos os containers
docker stats

# Ver logs de um container específico
docker logs <container_name>
```

## Troubleshooting

### Docker Desktop trava ao subir todos os serviços
- **Causa**: Memória insuficiente alocada no Docker Desktop
- **Solução**: Aumente a memória para 8-12 GB nas configurações

### Container fica reiniciando constantemente
- **Causa**: Container excedeu o limite de memória (OOMKilled)
- **Solução**: Aumente o limite de memória do container específico ou reduza processos

### "request returned 500 Internal Server Error"
- **Causa**: Docker Desktop não está respondendo
- **Solução**: Reinicie o Docker Desktop completamente
