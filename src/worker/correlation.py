"""
Correlación con datos COLCAP.
"""
import pandas as pd
import redis

from src.common.config import Config


class COLCAPCorrelator:
    def __init__(self, data_path=None, redis_client=None):
        self.data_path = data_path or Config.COLCAP_DATA_PATH
        self.df = None
        self.months_dates = []  # Lista de listas: fechas agrupadas por mes
        self.NEWS_PER_MONTH = 100  # Noticias por mes antes de pasar al siguiente
        self.redis_client = redis_client
        self._load_data()

    def _load_data(self):
        """Datos históricos del COLCAP"""
        try:
            self.df = pd.read_csv(self.data_path)
            self.df['Fecha'] = pd.to_datetime(self.df['Fecha'])
            self.df.set_index('Fecha', inplace=True)

            # Agrupar fechas por mes (últimos 8 meses)
            all_dates = sorted(self.df.index.tolist())
            self.months_dates = self._group_by_month(all_dates, num_months=8)

            print(f"[COLCAP] Datos cargados: {len(self.df)} registros")
            print(f"[COLCAP] Meses disponibles: {len(self.months_dates)}")
        except FileNotFoundError:
            print(f"[COLCAP] ADVERTENCIA: No se encontró {self.data_path}")
            self.df = pd.DataFrame()
        except Exception as e:
            print(f"[COLCAP] Error cargando CSV: {e}")
            self.df = pd.DataFrame()

    def _group_by_month(self, dates, num_months=12):
        """Agrupa fechas por mes"""
        if not dates:
            return []

        # Agrupar por año-mes
        months = {}
        for d in dates:
            key = (d.year, d.month)
            if key not in months:
                months[key] = []
            months[key].append(d)

        # Ordenar meses del más reciente al más antiguo
        sorted_keys = sorted(months.keys(), reverse=True)[:num_months]

        # Retornar lista de fechas por mes
        return [months[k] for k in sorted_keys]

    def get_value(self, date):
        """
        Valor COLCAP para una fecha.
        """
        if self.df.empty:
            return None

        try:
            fecha_lookup = pd.Timestamp(date)
            if fecha_lookup in self.df.index:
                return float(self.df.loc[fecha_lookup]['Ultimo'])
            return None
        except:
            return None

    def _get_global_counter(self):
        """Obtiene contador atómico desde Redis"""
        if self.redis_client:
            try:
                count = self.redis_client.incr('colcap_news_counter')
                return count - 1  # Devolver valor antes del incremento
            except:
                pass
        return 0

    def correlate(self, warc_date):
        """
        Distribución noticias
        """
        try:
            if not self.months_dates:
                # Fallback: usar fecha original si no hay datos
                fecha_noticia = pd.to_datetime(warc_date).date()
                valor_colcap = self.get_value(fecha_noticia)
                return (str(fecha_noticia), valor_colcap)

            # Obtener contador global 
            global_count = self._get_global_counter()

            # Calcular mes y posición dentro del mes
            total_news_per_cycle = self.NEWS_PER_MONTH * len(self.months_dates)
            position_in_cycle = global_count % total_news_per_cycle

            current_month = position_in_cycle // self.NEWS_PER_MONTH
            news_in_month = position_in_cycle % self.NEWS_PER_MONTH

            # Obtener fecha del mes actual
            month_dates = self.months_dates[current_month]
            # Distribuir dentro del mes 
            day_index = news_in_month % len(month_dates)
            fecha_asignada = month_dates[day_index]

            valor_colcap = self.get_value(fecha_asignada.date())
            return (str(fecha_asignada.date()), valor_colcap)
        except:
            return (None, None)

    def is_empty(self):
        """Verifica si hay datos cargados"""
        return self.df.empty
