"""
Producer - Indexación con Fallback
"""
import time
import json

from src.common.config import Config
from src.common.connections import RedisConnection
from .data_ingestion import FinancialDataIngestion
from .indexer import CommonCrawlIndexer
from .index_manager import IndexManager
from .news_indexer import NewsPortalIndexer

# Configuración de batch controlado
QUEUE_LOW_THRESHOLD = 50  # Traer más cuando la cola baje de este valor
WAIT_CHECK_INTERVAL = 5   # Segundos entre verificaciones de cola


def log_to_redis(redis_client, message, level='INFO'):
    """Log Redis para el dashboard"""
    try:
        log_entry = json.dumps({
            'ts': int(time.time()),
            'level': level,
            'msg': message
        })
        redis_client.lpush('producer_logs', log_entry)
        redis_client.ltrim('producer_logs', 0, 199)
    except:
        pass


def wait_for_queue_drain(redis_client, indexer, threshold=QUEUE_LOW_THRESHOLD):
    """Espera que baje del umbral"""
    while True:
        queue_size = indexer.get_queue_size()
        if queue_size <= threshold:
            return True

        print(f"[WAIT] Cola: {queue_size} > {threshold}, esperando {WAIT_CHECK_INTERVAL}s...")
        log_to_redis(redis_client, f"Esperando cola ({queue_size} pendientes)")
        time.sleep(WAIT_CHECK_INTERVAL)


def main():
    print("=" * 60)
    print("    PRODUCER - Common Crawl Indexer")
    print("=" * 60)

    # Configuración
    print(f"\n[CONFIG] Dominios: {', '.join(Config.TARGET_DOMAINS)}")
    print(f"[CONFIG] Pausa entre índices: {Config.DELAY_BETWEEN_INDEXES}s")
    print(f"[CONFIG] Pausa entre dominios: {Config.DELAY_BETWEEN_DOMAINS}s")

    # Cargar índices (1 sola vez si no existe archivo)
    print("\n" + "-" * 60)
    index_manager = IndexManager()
    indexes = index_manager.get_indexes()

    if not indexes:
        print("[ERROR] No hay índices disponibles")
        return

    print(f"[OK] {len(indexes)} índices disponibles")

    # Datos financieros
    print("\n" + "-" * 60)
    ingestion = FinancialDataIngestion()
    ingestion.download()
    ingestion.verify()

    # Conexión Redis
    print("\n" + "-" * 60)
    redis_conn = RedisConnection()
    redis_client = redis_conn.connect()

    if not redis_client:
        print("[ERROR] Sin conexión a Redis")
        return

    # Iniciar indexación
    print("\n" + "=" * 60)
    print("    INICIANDO INDEXACIÓN")
    print("=" * 60)

    cc_indexer = CommonCrawlIndexer(redis_client)
    news_indexer = NewsPortalIndexer(redis_client)
    position = cc_indexer.get_position()

    print(f"\n[INFO] Posición actual: {position}/{len(indexes)}")
    print(f"[INFO] Cola: {cc_indexer.get_queue_size()} tareas")
    print(f"[INFO] URLs procesadas: {cc_indexer.get_processed_count()}")

    log_to_redis(redis_client, f"Producer iniciado. Posición: {position}/{len(indexes)}")

    total_session = 0
    cc_failures = 0
    use_news_portals = False

    print(f"\n[MODE] Batch controlado: espera cola < {QUEUE_LOW_THRESHOLD} antes de traer más")

    # Loop infinito - procesa todos los índices
    while True:
        try:
            # BATCH CONTROLADO: Esperar a que la cola baje antes de traer más
            queue_size = cc_indexer.get_queue_size()
            if queue_size > QUEUE_LOW_THRESHOLD:
                print(f"\n[BATCH] Cola tiene {queue_size} tareas, esperando que baje de {QUEUE_LOW_THRESHOLD}...")
                log_to_redis(redis_client, f"Esperando workers (cola: {queue_size})")
                wait_for_queue_drain(redis_client, cc_indexer)
                print(f"[BATCH] Cola lista, trayendo más URLs...")

            # Si Common Crawl falla mucho, usar portales directamente
            if use_news_portals or cc_failures >= 3:
                if not use_news_portals:
                    print("\n[FALLBACK] Common Crawl no disponible, usando portales de noticias")
                    log_to_redis(redis_client, "Cambiando a scraping directo de portales", "WARN")
                    use_news_portals = True

                found = news_indexer.search_all_portals()
                total_session += found

                if found > 0:
                    log_to_redis(redis_client, f"Portales: {found} URLs encoladas")

                # Esperar antes de volver a escanear (menos tiempo para flujo constante)
                wait_time = 30 if found > 0 else 60
                print(f"\n[PAUSA] Esperando {wait_time}s antes de re-escanear portales...")
                time.sleep(wait_time)
                continue

            # Reiniciar
            if position >= len(indexes):
                msg = "Todos los índices procesados, reiniciando..."
                print(f"\n[INFO] {msg}")
                log_to_redis(redis_client, msg)
                position = 0
                cc_indexer.set_position(0)
                time.sleep(60)

            idx = indexes[position]

            status_msg = f"[{position + 1}/{len(indexes)}] Cola: {cc_indexer.get_queue_size()} | Sesión: {total_session}"
            print(f"\n{status_msg}")

            log_to_redis(redis_client, f"Procesando índice {idx['id']} ({position + 1}/{len(indexes)})")

            found = cc_indexer.search_index(idx['id'])

            if found == 0:
                cc_failures += 1
                print(f"[WARN] Índice sin resultados ({cc_failures}/3 fallas)")
            else:
                cc_failures = 0  # Reset en éxito
                total_session += found
                log_to_redis(redis_client, f"Índice {idx['id']}: {found} URLs encoladas")

            position += 1
            cc_indexer.set_position(position)

            # Pausa entre índices 
            if position < len(indexes):
                print(f"\n[PAUSA] {Config.DELAY_BETWEEN_INDEXES}s...")
                time.sleep(Config.DELAY_BETWEEN_INDEXES)

        except KeyboardInterrupt:
            print(f"\n\n[STOP] Detenido en posición {position}")
            log_to_redis(redis_client, f"Producer detenido manualmente. Posición: {position}", "WARN")
            break
        except Exception as e:
            error_msg = f"Error: {str(e)[:100]}"
            print(f"\n[ERROR] {e}")
            log_to_redis(redis_client, error_msg, "ERROR")
            print("[RETRY] Reintentando en 30s...")
            time.sleep(30)

    print("\n" + "=" * 60)
    print(f"[RESUMEN] Encoladas esta sesión: {total_session}")
    print(f"[RESUMEN] Cola final: {cc_indexer.get_queue_size()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
