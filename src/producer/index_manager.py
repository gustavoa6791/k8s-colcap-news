"""
Gestor de índices de Common Crawl.
Descarga la lista de índices.
"""
import os
import csv
import json
import requests


class IndexManager:
    """Lista de índices disponibles de Common Crawl."""

    COLLINFO_URL = "https://index.commoncrawl.org/collinfo.json"
    INDEXES_FILE = "data/cc_indexes.csv"

    def __init__(self):
        self.indexes = []

    def get_indexes(self):
        """
        Obtiene los índices: usa archivo local si existe, sino descarga.
        Retorna lista de índices ordenados del más reciente al más antiguo.
        """
        # Si existe el archivo local, usarlo
        if os.path.exists(self.INDEXES_FILE):
            if self._load_from_csv():
                print(f"[INDEX] Usando {len(self.indexes)} índices desde archivo local")
                return self.indexes

        # Si no existe, intentar descargar
        print("[INDEX] Archivo local no encontrado, descargando...")
        if self._download():
            return self.indexes

        # Fallback: lista por defecto
        print("[INDEX] Usando lista de índices por defecto")
        self.indexes = self._get_default_indexes()
        return self.indexes

    def _download(self):
        """Descarga la lista de índices desde Common Crawl."""
        try:
            response = requests.get(self.COLLINFO_URL, timeout=60)
            if response.status_code != 200:
                print(f"[INDEX] Error HTTP: {response.status_code}")
                return False

            data = response.json()
            if not data:
                return False

            # Procesar índices
            self.indexes = []
            for item in data:
                index_id = item.get('id', '')
                if index_id.startswith('CC-MAIN-'):
                    self.indexes.append({
                        'id': index_id,
                        'name': item.get('name', ''),
                        'cdx_api': item.get('cdx-api', ''),
                    })

            self._save_to_csv()
            print(f"[INDEX] Descargados y guardados {len(self.indexes)} índices")
            return True

        except Exception as e:
            print(f"[INDEX] Error descargando: {e}")
            return False

    def _save_to_csv(self):
        """Guardar índices en archivo CSV."""
        os.makedirs(os.path.dirname(self.INDEXES_FILE), exist_ok=True)
        with open(self.INDEXES_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'name', 'cdx_api'])
            writer.writeheader()
            writer.writerows(self.indexes)

    def _load_from_csv(self):
        """Cargar índices desde archivo CSV."""
        try:
            self.indexes = []
            with open(self.INDEXES_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.indexes.append(row)
            return len(self.indexes) > 0
        except Exception:
            return False

    def _get_default_indexes(self):
        """Lista de índices por defecto (fallback)."""
        return [
            {'id': 'CC-MAIN-2024-51', 'name': 'December 2024'},
            {'id': 'CC-MAIN-2024-46', 'name': 'November 2024'},
            {'id': 'CC-MAIN-2024-42', 'name': 'October 2024'},
            {'id': 'CC-MAIN-2024-38', 'name': 'September 2024'},
            {'id': 'CC-MAIN-2024-33', 'name': 'August 2024'},
            {'id': 'CC-MAIN-2024-30', 'name': 'July 2024'},
            {'id': 'CC-MAIN-2024-26', 'name': 'June 2024'},
            {'id': 'CC-MAIN-2024-22', 'name': 'May 2024'},
            {'id': 'CC-MAIN-2024-18', 'name': 'April 2024'},
            {'id': 'CC-MAIN-2024-10', 'name': 'March 2024'},
            {'id': 'CC-MAIN-2023-50', 'name': 'December 2023'},
            {'id': 'CC-MAIN-2023-40', 'name': 'October 2023'},
            {'id': 'CC-MAIN-2023-23', 'name': 'June 2023'},
            {'id': 'CC-MAIN-2023-14', 'name': 'April 2023'},
            {'id': 'CC-MAIN-2023-06', 'name': 'February 2023'},
        ]
