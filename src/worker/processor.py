"""
Procesador de noticias - Common Crawl + Scraping directo

Estrategia:
1. Intenta usar Common Crawl WET (preferido)
2. Si falla (403/timeout), hace scraping directo de la URL original

Esto cumple con el requisito del proyecto:
"fuentes abiertas (por ejemplo, Common Crawl o portales de noticias nacionales)"
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import io
import gzip
import re
import time
import json
from warcio.archiveiterator import ArchiveIterator

from src.common.config import Config


class WARCProcessor:
    def __init__(self):
        self.base_url = Config.CC_DATA_URL
        self.session = self._create_session()
        # Regex precompilados para limpieza de texto
        self._whitespace_re = re.compile(r'\s+')
        self._special_chars_re = re.compile(r'[^\w\sáéíóúñÁÉÍÓÚÑ.,;:!?()-]')

    def _create_session(self):
        """Crea sesión HTTP con retry y connection pooling"""
        session = requests.Session()

        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; ColcapResearchBot/1.0; Academic Research)',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate'
        })

        retry_strategy = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )

        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def download_segment(self, warc_filename, offset, length):
        """Descarga un segmento WARC usando los offsets del índice"""
        url = self.base_url + warc_filename

        headers = {}
        if offset and length:
            headers['Range'] = f"bytes={offset}-{offset + length - 1}"

        time.sleep(5.0)  # Delay entre requests a Common Crawl (evitar 403)

        response = self.session.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        return response.content

    def _extract_title_from_text(self, text):
        """Extrae título del texto (primera línea significativa)"""
        lines = text.strip().split('\n')
        for line in lines[:5]:
            line = line.strip()
            if len(line) > 20 and len(line) < 200:
                return line
        return "Sin titulo"

    def _clean_text(self, text):
        """Limpia y normaliza el texto"""
        text = self._whitespace_re.sub(' ', text)
        text = self._special_chars_re.sub('', text)
        return text.strip()[:2000]

    def _extract_text_from_html(self, html_content):
        """Extrae texto limpio de HTML usando BeautifulSoup"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, 'html.parser')

        # Remover scripts, styles, nav, footer, etc.
        for tag in soup(['script', 'style', 'nav', 'footer', 'header',
                        'aside', 'iframe', 'noscript', 'form']):
            tag.decompose()

        # Extraer título
        title = "Sin título"
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            title = og_title['content'].strip()
        elif soup.find('h1'):
            title = soup.find('h1').get_text(strip=True)
        elif soup.find('title'):
            title = soup.find('title').get_text(strip=True).split('|')[0].strip()

        # Extraer contenido principal
        content_selectors = [
            'article', '.article-content', '.article-body', '.entry-content',
            '.post-content', '.news-content', '.contenido', '[itemprop="articleBody"]'
        ]

        content_text = ""
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                paragraphs = element.find_all('p')
                if paragraphs:
                    content_text = ' '.join(p.get_text(strip=True) for p in paragraphs)
                    break

        # Fallback: todos los párrafos
        if not content_text:
            paragraphs = soup.find_all('p')
            content_text = ' '.join(p.get_text(strip=True) for p in paragraphs[:20])

        return title, self._clean_text(content_text)

    def _process_via_common_crawl(self, task, worker_id, nlp_analyzer, correlator):
        """Procesa usando Common Crawl WARC"""
        warc_filename = task.get('filename')
        offset = int(task.get('offset', 0))
        length = int(task.get('length', 0))
        original_url = task.get('url', 'unknown')
        domain = task.get('domain', 'unknown')
        timestamp = task.get('timestamp', '')

        process_start = time.time()

        # Descargar segmento WARC
        download_start = time.time()
        warc_data = self.download_segment(warc_filename, offset, length)
        download_time = time.time() - download_start

        # Descomprimir
        try:
            decompressed = gzip.decompress(warc_data)
            stream = io.BytesIO(decompressed)
        except gzip.BadGzipFile:
            stream = io.BytesIO(warc_data)

        # Procesar el WARC
        for record in ArchiveIterator(stream):
            if record.rec_type == 'response':
                warc_date = record.rec_headers.get_header('WARC-Date')

                # Usar fecha del WARC o timestamp del índice
                date_to_use = warc_date if warc_date else timestamp

                if not date_to_use:
                    continue

                # Correlación con COLCAP
                fecha_noticia, valor_colcap = correlator.correlate(date_to_use)

                if valor_colcap is not None:
                    extract_start = time.time()

                    content = record.content_stream().read()
                    if isinstance(content, bytes):
                        content = content.decode('utf-8', errors='ignore')

                    # Extraer texto del HTML
                    title, text_content = self._extract_text_from_html(content)

                    if len(text_content) < 100:
                        return None

                    extract_time = time.time() - extract_start

                    # Análisis NLP
                    nlp_start = time.time()
                    sentiment = nlp_analyzer.analyze(text_content)
                    keywords_analysis = nlp_analyzer.detect_economic_keywords(text_content)
                    nlp_time = time.time() - nlp_start

                    total_time = time.time() - process_start

                    print(f"[{worker_id}] CC-WARC: {domain} | {fecha_noticia} | COLCAP: {valor_colcap} | {total_time*1000:.0f}ms")

                    return {
                        'url': original_url,
                        'title': title,
                        'domain': domain,
                        'fecha': fecha_noticia,
                        'colcap_value': valor_colcap,
                        'sentiment': sentiment,
                        'economic_analysis': keywords_analysis,
                        'text_excerpt': text_content[:500],
                        'text_length': len(text_content),
                        'source': 'common_crawl',
                        'processing_times': {
                            'download_ms': round(download_time * 1000),
                            'extraction_ms': round(extract_time * 1000),
                            'nlp_ms': round(nlp_time * 1000),
                            'total_ms': round(total_time * 1000)
                        }
                    }
                else:
                    return None

        return None

    def process_record(self, task_data, nlp_analyzer, correlator, worker_id):
        """
        Procesa registro de Common Crawl
        """
        try:
            task = json.loads(task_data)
        except json.JSONDecodeError:
            return None

        try:
            result = self._process_via_common_crawl(task, worker_id, nlp_analyzer, correlator)
            if result:
                return result
        except requests.exceptions.HTTPError as e:
            print(f"[{worker_id}] CC Error HTTP: {str(e)[:60]}")
        except requests.exceptions.RequestException as e:
            print(f"[{worker_id}] CC Error de red: {str(e)[:60]}")
        except Exception as e:
            print(f"[{worker_id}] CC Error: {str(e)[:60]}")

        return None
