"""
Módulo de datos del Dashboard.
Conexión a Redis y funciones de obtención de datos.
"""
import redis
import json
import pandas as pd

from src.common.config import Config

# Configuración
REDIS_HOST = Config.REDIS_HOST
REDIS_PORT = Config.REDIS_PORT
COLCAP_PATH = Config.COLCAP_DATA_PATH
_colcap_data = None


def get_redis():
    """Conexión a Redis"""
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        r.ping()
        return r
    except:
        return None


def load_colcap():
    """Carga de datos de COLCAP"""
    global _colcap_data
    if _colcap_data is None:
        try:
            df = pd.read_csv(COLCAP_PATH)
            df['Fecha'] = pd.to_datetime(df['Fecha'])
            _colcap_data = df
        except:
            _colcap_data = pd.DataFrame()
    return _colcap_data


def get_results():
    """Resultados del dashboard"""
    r = get_redis()
    if not r:
        return []
    try:
        data = r.lrange('resultados_dashboard', 0, -1)
        return [json.loads(x) for x in data if x]
    except:
        return []


def get_workers():
    """Información de workers activos"""
    r = get_redis()
    if not r:
        return []
    try:
        keys = r.keys('worker_stats:*')
        out = []
        for k in keys:
            d = r.hgetall(k)
            if d:
                d['worker_id'] = k.split(':')[-1]
                out.append(d)
        return out
    except:
        return []


def get_metrics():
    """Métricas globales"""
    r = get_redis()
    if not r:
        return {'processed': 0, 'errors': 0, 'queue': 0, 'skipped': 0}
    try:
        return {
            'processed': int(r.get('total_processed') or 0),
            'errors': int(r.get('total_errors') or 0),
            'skipped': int(r.get('total_skipped') or 0),
            'queue': r.llen('warc_queue')
        }
    except:
        return {'processed': 0, 'errors': 0, 'queue': 0, 'skipped': 0}


def record_throughput_snapshot():
    """
    Snapshot del throughput actual.
    """
    import time
    r = get_redis()
    if not r:
        return

    try:
        # Métricas actuales
        workers = get_workers()
        num_workers = len(workers)
        total_rate = sum(float(w.get('rate', 0)) for w in workers)
        total_processed = int(r.get('total_processed') or 0)

        # Crear snapshot
        timestamp = int(time.time())
        snapshot = json.dumps({
            'ts': timestamp,
            'workers': num_workers,
            'rate': round(total_rate, 2),
            'processed': total_processed
        })

        # Guardar en lista 
        r.lpush('throughput_history', snapshot)
        r.ltrim('throughput_history', 0, 399)  # Ultimos 400 registros

        # Cambio de workers

        last_workers = r.get('last_worker_count')
        if num_workers > 0 and num_workers % 2 == 0:  # Solo pares
            if last_workers is None or int(last_workers) != num_workers:
                # Rate promedio reciente para número de workers
                recent_rates = []
                history_data = r.lrange('throughput_history', 0, 50)
                for item in history_data:
                    snap = json.loads(item)
                    if snap.get('workers') == num_workers and snap.get('rate', 0) > 0:
                        recent_rates.append(snap['rate'])

                # Rate actual
                effective_rate = total_rate if total_rate > 0 else (
                    sum(recent_rates) / len(recent_rates) if recent_rates else 0
                )

                # Cambio de configuración
                change_entry = json.dumps({
                    'ts': timestamp,
                    'workers': num_workers,
                    'rate': round(effective_rate, 2)
                })
                r.lpush('scalability_changes', change_entry)
                r.set('last_worker_count', num_workers)

    except:
        pass


def get_throughput_history(seconds=60):
    """
    Historial de throughput
    """
    import time
    r = get_redis()
    if not r:
        return []

    try:
        # Obtener todos los snapshots
        data = r.lrange('throughput_history', 0, -1)
        if not data:
            return []

        # Filtrar por ventana de tiempo en segundos
        cutoff = int(time.time()) - seconds
        history = []

        for item in data:
            snapshot = json.loads(item)
            if snapshot['ts'] >= cutoff:
                history.append(snapshot)

        # Ordenar por timestamp
        history.sort(key=lambda x: x['ts'])
        return history

    except:
        return []


def get_producer_logs(limit=50):
    """Ultimos logs del producer"""
    r = get_redis()
    if not r:
        return []
    try:
        data = r.lrange('producer_logs', 0, limit - 1)
        logs = []
        for item in data:
            log = json.loads(item)
            logs.append(log)
        return logs
    except:
        return []


def get_scalability_metrics(minutes=None):
    """
    Calcula métricas de escalabilidad basadas en últimos cambios de configuración.
    Speedup = Throughput(N) / Throughput(1)
    Eficiencia = Speedup / N
    """
    r = get_redis()
    if not r:
        return {'changes': [], 'baseline_rate': 0}

    try:
        # Cambios de configuración
        data = r.lrange('scalability_changes', 0, -1)  # Todos los cambios
        if not data:
            return {'changes': [], 'baseline_rate': 0}

        # Parsear y ordenar por timestamp
        changes = []
        for item in data:
            change = json.loads(item)
            # Solo incluir si tiene rate > 0 
            if change.get('rate', 0) > 0:
                changes.append(change)

        changes.sort(key=lambda x: x['ts'])

        if not changes:
            return {'changes': [], 'baseline_rate': 0}

        # Registro con menor número de workers que tenga rate
        min_workers_change = min(changes, key=lambda x: x['workers'])
        baseline_rate = min_workers_change['rate'] / min_workers_change['workers'] if min_workers_change['workers'] > 0 else 1

        # Calcular speedup y eficiencia para cada cambio
        result_changes = []
        for change in changes:
            n_workers = change['workers']
            rate = change['rate']
            ts = change['ts']

            speedup = rate / baseline_rate if baseline_rate > 0 else n_workers
            efficiency = (speedup / n_workers) * 100 if n_workers > 0 else 0

            result_changes.append({
                'ts': ts,
                'workers': n_workers,
                'rate': round(rate, 2),
                'speedup': round(speedup, 2),
                'efficiency': round(efficiency, 1),
                'ideal_speedup': n_workers
            })

        return {
            'changes': result_changes,
            'baseline_rate': round(baseline_rate, 2)
        }

    except:
        return {'changes': [], 'baseline_rate': 0}


def clear_scalability_history():
    """Limpia el historial de throughput para reiniciar métricas de escalabilidad"""
    r = get_redis()
    if not r:
        return False
    try:
        r.delete('throughput_history')
        r.delete('scalability_changes')
        r.delete('last_worker_count')
        return True
    except:
        return False
