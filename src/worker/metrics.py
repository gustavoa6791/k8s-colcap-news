"""
Módulo de métricas y estadísticas del worker.
"""
from datetime import datetime
import json

from src.common.utils import json_serial

class WorkerMetrics:
    def __init__(self, redis_client, worker_id):
        self.redis_client = redis_client
        self.worker_id = worker_id

    def init_global_metrics(self):
        """Métricas globales"""
        if self.redis_client is None:
            return

        try:
            if not self.redis_client.exists('processing_start_time'):
                self.redis_client.set('processing_start_time', datetime.utcnow().isoformat())
            if not self.redis_client.exists('total_processed'):
                self.redis_client.set('total_processed', 0)
            if not self.redis_client.exists('total_errors'):
                self.redis_client.set('total_errors', 0)
            if not self.redis_client.exists('total_skipped'):
                self.redis_client.set('total_skipped', 0)
        except:
            pass

    def increment_global_counter(self, counter_name, amount=1):
        """Contador global"""
        if self.redis_client is None:
            return

        try:
            self.redis_client.incrby(counter_name, amount)
        except:
            pass

    def update_worker_stats(self, tasks_per_minute, errors=0, tasks_processed=0):
        """Estadísticas de worker"""
        if self.redis_client is None:
            return

        try:
            key = f'worker_stats:{self.worker_id}'

            if tasks_processed > 0:
                processed = tasks_processed
            else:
                history_key = f'worker_history:{self.worker_id}'
                processed = int(self.redis_client.get(history_key) or 0)

            self.redis_client.hset(key, 'rate', round(tasks_per_minute, 2))
            self.redis_client.hset(key, 'last_active', datetime.utcnow().isoformat())
            self.redis_client.hset(key, 'errors', errors)
            self.redis_client.hset(key, 'processed', processed)
            self.redis_client.expire(key, 15)

            self.redis_client.set('last_processed_time', datetime.utcnow().isoformat())
        except Exception as e:
            print(f"[{self.worker_id}] Error actualizando stats: {e}")

    def save_to_dashboard(self, result_data):
        """Resultado para visualización en dashboard"""
        if self.redis_client is None:
            return False

        try:
            result_data['processed_at'] = datetime.utcnow().isoformat()
            result_data['worker_id'] = self.worker_id
            self.redis_client.lpush('resultados_dashboard', json.dumps(result_data, default=json_serial))
            history_key = f'worker_history:{self.worker_id}'
            self.redis_client.incr(history_key)

            return True
        except Exception as e:
            print(f"[{self.worker_id}] Error enviando a dashboard: {e}")
            return False

    def save_correlation(self, correlation_data):
        """Correlación en Redis"""
        if self.redis_client is None:
            return False

        try:
            correlation_data['worker_id'] = self.worker_id
            correlation_data['timestamp_procesado'] = datetime.utcnow().isoformat()

            # Guardar en lista de correlaciones
            self.redis_client.lpush('correlaciones_history', json.dumps(correlation_data, default=json_serial))
            self.redis_client.ltrim('correlaciones_history', 0, 999)  # Mantener últimas 1000

            return True
        except Exception as e:
            print(f"[{self.worker_id}] Error guardando correlación: {e}")
            return False

    def save_metrics(self, metrics_data):
        """Métricas de procesamiento"""
        if self.redis_client is None:
            return False

        try:
            metrics_data['worker_id'] = self.worker_id
            metrics_data['timestamp'] = datetime.utcnow().isoformat()

            # Lista de métricas
            self.redis_client.lpush('metrics_history', json.dumps(metrics_data, default=json_serial))
            self.redis_client.ltrim('metrics_history', 0, 499)  # Mantener últimas 500

            return True
        except Exception as e:
            print(f"[{self.worker_id}] Error guardando métricas: {e}")
            return False
