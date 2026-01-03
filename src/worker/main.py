"""
Worker - Procesamiento Paralelo con ThreadPool
"""
import time
import redis
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.common.config import Config
from src.common.connections import RedisConnection, S3Connection
from .processor import WARCProcessor
from .nlp import SentimentAnalyzer
from .correlation import COLCAPCorrelator
from .metrics import WorkerMetrics

# Configuración de paralelismo
BATCH_SIZE = 4  # Tareas a procesar en paralelo por worker
MAX_THREADS = 4  # Hilos por worker


def process_single_task(args):
    """Procesa una tarea individual (para ThreadPool)"""
    task_data, warc_processor, nlp_analyzer, correlator, worker_id = args
    try:
        return warc_processor.process_record(task_data, nlp_analyzer, correlator, worker_id)
    except Exception as e:
        print(f"[{worker_id}] Error en hilo: {e}")
        return None


def main():
    worker_id = Config.WORKER_ID

    print("=" * 60)
    print(f"    WORKER {worker_id} (Optimizado)")
    print(f"    Batch: {BATCH_SIZE} | Threads: {MAX_THREADS}")
    print("=" * 60)

    # Conectar a Redis primero
    redis_conn = RedisConnection()
    redis_client = redis_conn.connect()
    if not redis_client:
        print(f"[{worker_id}] Abortando: No hay conexión a Redis")
        return

    # Inicializar componentes
    correlator = COLCAPCorrelator(redis_client=redis_client)
    nlp_analyzer = SentimentAnalyzer()
    warc_processor = WARCProcessor()

    # Conectar a S3
    s3_conn = S3Connection()
    s3_conn.connect()

    # Inicializar métricas
    metrics = WorkerMetrics(redis_client, worker_id)
    metrics.init_global_metrics()

    # Contadores
    tasks_processed = 0
    correlations_found = 0
    errors_count = 0
    start_time = time.time()

    # Registrar worker al iniciar
    metrics.update_worker_stats(0, 0, 0)

    print(f"[{worker_id}] Esperando tareas en la cola 'warc_queue'...")

    # ThreadPool para procesamiento paralelo
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        while True:
            try:
                # Obtener batch de tareas
                tasks = []
                for _ in range(BATCH_SIZE):
                    result = redis_client.lpop('warc_queue')
                    if result:
                        tasks.append(result.decode('utf-8') if isinstance(result, bytes) else result)
                    else:
                        break

                if not tasks:
                    # Cola vacía, esperar con blpop 
                    result = redis_client.blpop('warc_queue', timeout=2)  # 2 segundos para heartbeat rápido
                    if result:
                        _, task_data = result
                        tasks = [task_data.decode('utf-8') if isinstance(task_data, bytes) else task_data]
                    else:
                        # Timeout 
                        elapsed_time = time.time() - start_time
                        tasks_per_minute = (tasks_processed / elapsed_time * 60) if elapsed_time > 0 else 0
                        metrics.update_worker_stats(tasks_per_minute, errors_count, tasks_processed)
                        continue

                # Procesar batch en paralelo
                futures = []
                for task_data in tasks:
                    args = (task_data, warc_processor, nlp_analyzer, correlator, worker_id)
                    futures.append(executor.submit(process_single_task, args))

                # Recolectar resultados 
                for future in as_completed(futures):
                    tasks_processed += 1
                    metrics.increment_global_counter('total_processed')

                    # Heartbeat en cada tarea para mantener worker visible
                    elapsed_time = time.time() - start_time
                    tasks_per_minute = (tasks_processed / elapsed_time * 60) if elapsed_time > 0 else 0
                    metrics.update_worker_stats(tasks_per_minute, errors_count, tasks_processed)

                    try:
                        correlation_result = future.result()

                        if correlation_result:
                            correlations_found += 1

                            if metrics.save_correlation(correlation_result):
                                pass  # Guardado exitoso

                            if metrics.save_to_dashboard(correlation_result.copy()):
                                pass  # Enviado a dashboard
                        else:
                            metrics.increment_global_counter('total_skipped')

                    except Exception as e:
                        errors_count += 1
                        metrics.increment_global_counter('total_errors')
                        print(f"[{worker_id}] Error procesando resultado: {e}")

                # Actualizar stats después de cada batch
                elapsed_time = time.time() - start_time
                tasks_per_second = tasks_processed / elapsed_time if elapsed_time > 0 else 0
                tasks_per_minute = tasks_per_second * 60

                # Actualizar worker_stats en cada batch para mantener visibilidad
                metrics.update_worker_stats(tasks_per_minute, errors_count, tasks_processed)

                # Progreso cada 10 tareas
                if tasks_processed % 10 == 0:
                    queue_size = redis_client.llen('warc_queue')

                    print(f"[{worker_id}] {tasks_processed} proc | {correlations_found} corr | {queue_size} pend | {tasks_per_second:.2f} t/s")

                    metrics.save_metrics({
                        'tasks_processed': tasks_processed,
                        'correlations_found': correlations_found,
                        'queue_size': queue_size,
                        'elapsed_seconds': elapsed_time,
                        'tasks_per_second': tasks_per_second
                    })

            except redis.ConnectionError:
                print(f"[{worker_id}] Conexión a Redis perdida. Reconectando...")
                redis_client = redis_conn.connect()
                if not redis_client:
                    break

            except KeyboardInterrupt:
                print(f"\n[{worker_id}] Detenido por el usuario")
                break

            except Exception as e:
                print(f"[{worker_id}] Error inesperado: {e}")
                errors_count += 1
                metrics.increment_global_counter('total_errors')
                time.sleep(2)

    # Métricas finales
    elapsed_time = time.time() - start_time
    metrics.save_metrics({
        'status': 'finalizado',
        'tasks_processed': tasks_processed,
        'correlations_found': correlations_found,
        'total_seconds': elapsed_time
    })

    print(f"[{worker_id}] Finalizado. Total: {tasks_processed}, Correlaciones: {correlations_found}")


if __name__ == "__main__":
    main()
