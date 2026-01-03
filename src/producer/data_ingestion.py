"""
Ingesta de datos financieros.
"""
import os
import requests
import pandas as pd
from io import StringIO

from src.common.config import Config


class FinancialDataIngestion:
    def __init__(self, data_path=None):
        self.data_path = data_path or Config.COLCAP_DATA_PATH

    def download(self):
        """Datos financieros históricos para correlación. """
        print("\n" + "=" * 60)
        print("    ETAPA 1: INGESTA DE DATOS FINANCIEROS")
        print("=" * 60)

        # Verificar si ya existe el archivo
        if os.path.exists(self.data_path):
            try:
                df = pd.read_csv(self.data_path)
                print(f"[OK] Archivo {self.data_path} ya existe con {len(df)} registros")
                return True
            except:
                print(f"[!] Archivo existente corrupto, descargando nuevo...")

        # Yahoo Finance (COLCAP)
        print("[*] Intentando descargar datos COLCAP desde Yahoo Finance...")
        try:
            url = "https://query1.finance.yahoo.com/v7/finance/download/%5ECOLCAP"
            params = {
                'period1': '1704067200',  # 2024-01-01
                'period2': '1735689600',  # 2024-12-31
                'interval': '1d',
                'events': 'history'
            }
            headers = {'User-Agent': 'Mozilla/5.0'}

            response = requests.get(url, params=params, headers=headers, timeout=30)

            if response.status_code == 200:
                df = pd.read_csv(StringIO(response.text))
                df = df.rename(columns={'Date': 'Fecha', 'Close': 'Ultimo'})
                df = df[['Fecha', 'Ultimo']]
                df.to_csv(self.data_path, index=False)
                print(f"[OK] Datos COLCAP descargados: {len(df)} registros")
                print(f"    Rango: {df['Fecha'].min()} a {df['Fecha'].max()}")
                return True

        except Exception as e:
            print(f"[-] Error descargando de Yahoo Finance: {e}")

        return False


    def verify(self):
        """Verifica  datos financieros """
        try:
            df = pd.read_csv(self.data_path)
            required_columns = ['Fecha', 'Ultimo']

            for col in required_columns:
                if col not in df.columns:
                    print(f"[-] Columna requerida faltante: {col}")
                    return False

            print(f"[OK] Datos financieros verificados: {len(df)} registros")
            return True

        except Exception as e:
            print(f"[-] Error verificando datos: {e}")
            return False
