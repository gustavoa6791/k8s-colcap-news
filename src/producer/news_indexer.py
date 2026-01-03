"""
Indexador alternativo - Scraping directo de portales de noticias.
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime

from src.common.config import Config


class NewsPortalIndexer:
    """
    Indexa URLs de noticias directamente desde los portales colombianos.
    """

    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.queue_name = 'warc_queue'
        self.processed_urls_key = 'processed_urls'
        self.session = self._create_session()

        # Configuración ampliada de portales - más secciones para más noticias
        self.portals = {
            'larepublica.co': {
                'base_url': 'https://www.larepublica.co',
                'sections': [
                    '/economia', '/finanzas', '/empresas', '/globoeconomia',
                    '/economia/gobierno', '/economia/macroeconomia',
                    '/finanzas/bancos', '/finanzas/mercado-de-valores',
                    '/empresas/energia', '/empresas/transporte',
                    '/archivo/economia', '/archivo/finanzas'
                ],
                'paginated': True,
                'max_pages': 5
            },
            'portafolio.co': {
                'base_url': 'https://www.portafolio.co',
                'sections': [
                    '/economia', '/finanzas', '/empresas', '/negocios',
                    '/economia/gobierno', '/economia/finanzas-publicas',
                    '/negocios/empresas', '/internacional',
                    '/tendencias', '/mis-finanzas'
                ],
                'paginated': True,
                'max_pages': 5
            },
            'eltiempo.com': {
                'base_url': 'https://www.eltiempo.com',
                'sections': [
                    '/economia', '/politica', '/colombia', '/bogota',
                    '/economia/sectores', '/economia/finanzas-personales',
                    '/mundo', '/tecnosfera'
                ],
                'paginated': True,
                'max_pages': 3
            },
            'elespectador.com': {
                'base_url': 'https://www.elespectador.com',
                'sections': [
                    '/economia', '/negocios', '/politica', '/colombia',
                    '/economia/macroeconomia', '/economia/finanzas',
                    '/mundo', '/tecnologia'
                ],
                'paginated': True,
                'max_pages': 3
            }
        }

    def _create_session(self):
        """Crea sesión HTTP con headers apropiados"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'es-CO,es;q=0.9'
        })
        return session

    def _extract_article_urls(self, html, base_url, domain):
        """Extrae URLs de artículos de una página"""
        soup = BeautifulSoup(html, 'html.parser')
        urls = set()

        for link in soup.find_all('a', href=True):
            href = link['href']

            # Convertir a URL absoluta
            if href.startswith('/'):
                url = base_url + href
            elif href.startswith('http'):
                url = href
            else:
                continue

            # Filtrar solo URLs del dominio
            if domain not in url:
                continue

            # Filtrar URLs de artículos 
            if any(x in url.lower() for x in ['/tag/', '/autor/', '/buscar', '/login',
                                               '/registro', '.xml', '.css', '.js',
                                               '/rss', '/feed', '/contacto']):
                continue

            # Debe ser una URL de noticia 
            if re.search(r'/[\w-]+-\d+', url) or re.search(r'/\d{4}/\d{2}/\d{2}/', url):
                urls.add(url)

        return urls

    def index_portal(self, domain):
        """Indexa todas las secciones de un portal con paginación"""
        if domain not in self.portals:
            return 0, 0

        portal = self.portals[domain]
        base_url = portal['base_url']
        max_pages = portal.get('max_pages', 3)
        total_new = 0
        total_dups = 0

        for section in portal['sections']:
            # Indexar múltiples páginas de cada sección
            for page in range(1, max_pages + 1):
                if page == 1:
                    url = base_url + section
                else:
                    # Diferentes formatos de paginación según el portal
                    if 'larepublica' in domain or 'portafolio' in domain:
                        url = f"{base_url}{section}?page={page}"
                    elif 'eltiempo' in domain:
                        url = f"{base_url}{section}/page/{page}"
                    else:
                        url = f"{base_url}{section}?page={page}"

                try:
                    response = self.session.get(url, timeout=30)
                    if response.status_code != 200:
                        break  # No más páginas

                    article_urls = self._extract_article_urls(response.text, base_url, domain)

                    if not article_urls:
                        break  # No más artículos

                    page_new = 0
                    for article_url in article_urls:
                        # Verificar si ya fue procesada
                        if self.redis_client.sismember(self.processed_urls_key, article_url):
                            total_dups += 1
                            continue

                        # Encolar tarea
                        task_data = json.dumps({
                            'filename': '',  # No aplica para scraping directo
                            'offset': 0,
                            'length': 0,
                            'url': article_url,
                            'timestamp': datetime.now().strftime('%Y%m%d%H%M%S'),
                            'domain': domain
                        })

                        self.redis_client.lpush(self.queue_name, task_data)
                        self.redis_client.sadd(self.processed_urls_key, article_url)
                        total_new += 1
                        page_new += 1

                    # Si no hay nuevas en esta página, no seguir paginando
                    if page_new == 0:
                        break

                    time.sleep(3)  # Pausa entre páginas (evitar rate limit)

                except Exception as e:
                    break  # Error, pasar a siguiente sección

            time.sleep(2)  # Pausa entre secciones

        return total_new, total_dups

    def search_all_portals(self):
        """Busca en todos los portales configurados"""
        print(f"\n{'='*60}")
        print("    INDEXACIÓN DIRECTA DE PORTALES")
        print(f"{'='*60}")

        total = 0
        duplicates = 0

        for domain in self.portals.keys():
            print(f"\n[*] {domain}...", end=" ", flush=True)
            count, dups = self.index_portal(domain)
            total += count
            duplicates += dups

            if count > 0 or dups > 0:
                print(f"Nuevas: {count} | Duplicadas: {dups}")
            else:
                print("Sin resultados")

            time.sleep(3)  # Pausa entre portales

        print(f"\n[OK] Total: {total} nuevas | {duplicates} duplicadas")
        return total

    def get_queue_size(self):
        return self.redis_client.llen(self.queue_name)

    def get_processed_count(self):
        return self.redis_client.scard(self.processed_urls_key)
