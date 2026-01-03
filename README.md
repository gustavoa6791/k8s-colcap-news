# Proyecto: Infraestructuras Paralelas y Distribuidas

Sistema distribuido para procesamiento de datos de Common Crawl con análisis de sentimiento de noticias colombianas y correlación con el índice bursátil COLCAP.

## Descripción

Este proyecto analiza artículos de noticias de los principales medios colombianos (El Tiempo, El Espectador, Portafolio, La República), realiza análisis de sentimiento en español y correlaciona los resultados con las variaciones del índice COLCAP.

## Arquitectura

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Producer  │────▶│    Redis    │◀────│   Workers   │
│  (1 Job)    │     │(Queue+Data) │     │  (N pods)   │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │  Dashboard  │
                    │   (Dash)    │
                    └─────────────┘
```

**Componentes:**
- **Producer**: Descarga datos COLCAP e indexa URLs de Common Crawl
- **Workers**: Procesan artículos, analizan sentimiento y correlacionan con COLCAP
- **Dashboard**: Visualización de resultados en tiempo real
- **Redis**: Cola de mensajes y almacenamiento de datos

## Requisitos Previos

- Docker Desktop
- Minikube
- kubectl
- Python 3.11+
- Cuenta en Docker Hub

---

## Guía de Uso Paso a Paso

### Paso 1: Clonar e Instalar Dependencias

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
source venv/bin/activate  # Linux/Mac
# o: venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### Paso 2: Iniciar Minikube

```bash
# Iniciar cluster de Kubernetes local
minikube start --driver=docker --memory=4096 --cpus=4

# Verificar que Minikube está corriendo
minikube status
```

### Paso 3: Construir y Subir la Imagen Docker

```bash
# Iniciar sesión en Docker Hub
docker login

# Construir la imagen (reemplazar 'tu-usuario' con tu usuario de Docker Hub)
docker build -t tu-usuario/proyecto-ipd:v1 .

# Subir la imagen a Docker Hub
docker push tu-usuario/proyecto-ipd:v1
```

### Paso 4: Configurar el Despliegue

Editar el archivo `config/kubernetes/k8s-deployment.yaml` y reemplazar todas las referencias de imagen con tu usuario:

```yaml
image: tu-usuario/proyecto-ipd:v1
```

> **Nota:** Hay 4 lugares donde debes cambiar la imagen (Redis usa imagen oficial, no necesita cambio).

### Paso 5: Desplegar en Kubernetes

```bash
# Aplicar toda la configuración de Kubernetes
kubectl apply -f config/kubernetes/k8s-deployment.yaml

# Verificar que los pods se están creando
kubectl get pods -w
```

### Paso 6: Monitorear el Procesamiento

```bash
# Ver logs del Producer (indexación de URLs)
kubectl logs -l app=cc-producer -f

# Ver logs de los Workers (procesamiento de artículos)
kubectl logs -l app=cc-worker --tail=50 -f

# Ver cuántas tareas quedan en la cola
kubectl exec -it $(kubectl get pod -l app=redis -o jsonpath='{.items[0].metadata.name}') -- redis-cli LLEN warc_queue
```

### Paso 7: Acceder al Dashboard de Resultados

```bash
# Abrir el dashboard en el navegador
minikube service dashboard-service
```

---

## Comandos Útiles

### Monitoreo

```bash
# Ver todos los pods
kubectl get pods

# Ver logs en tiempo real del producer
kubectl logs -l app=cc-producer -f

# Ver logs en tiempo real de workers
kubectl logs -l app=cc-worker -f --max-log-requests=10

# Ver logs del dashboard
kubectl logs -l app=dashboard -f

# Ver estado de la cola Redis
kubectl exec -it $(kubectl get pod -l app=redis -o jsonpath='{.items[0].metadata.name}') -- redis-cli LLEN warc_queue

# Ver resultados procesados
kubectl exec -it $(kubectl get pod -l app=redis -o jsonpath='{.items[0].metadata.name}') -- redis-cli HLEN processed_results
```

### Escalamiento

```bash
# Escalar workers (más procesamiento paralelo)
kubectl scale deployment cc-worker --replicas=8

# Ver estado del autoescalado
kubectl get hpa
```
