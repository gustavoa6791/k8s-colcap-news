"""
Módulo de indexación de Common Crawl.
"""
import requests
import json
import time

from src.common.config import Config
from src.common.utils import is_valid_news_url


class CommonCrawlIndexer:
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.queue_name = 'warc_queue'
        self.processed_urls_key = 'processed_urls'
        self.position_key = 'producer_position'

    def search_index(self, index_id):
        """
        Dominios en un índice específico.
        """
        print(f"\n{'='*60}")
        print(f"    ÍNDICE: {index_id}")
        print(f"{'='*60}")

        total = 0
        duplicates = 0

        for domain in Config.TARGET_DOMAINS:
            domain = domain.strip()
            if not domain:
                continue

            print(f"\n[*] {domain}...", end=" ", flush=True)
            count, dups = self._search_domain(domain, index_id)
            total += count
            duplicates += dups

            if count > 0 or dups > 0:
                print(f"Encolados: {count} | Duplicados: {dups}")
            else:
                print(f"Sin resultados")

            time.sleep(Config.DELAY_BETWEEN_DOMAINS)

        print(f"\n[OK] Total {index_id}: {total} nuevas | {duplicates} duplicados")
        return total

    def _search_domain(self, domain, index_id):
        """Dominio en un índice de Common Crawl."""
        url = f"{Config.CC_INDEX_BASE_URL}/{index_id}-index?url={domain}/*&output=json"

        try:
            response = requests.get(url, timeout=120)

            if response.status_code == 200 and response.text.strip():
                count = 0
                duplicates = 0

                for line in response.text.splitlines():
                    try:
                        record = json.loads(line)
                        url_original = record.get('url')

                        if not url_original or not is_valid_news_url(
                            url_original, Config.EXCLUDED_PATTERNS, Config.NEWS_SECTIONS
                        ):
                            continue

                        if self.redis_client.sismember(self.processed_urls_key, url_original):
                            duplicates += 1
                            continue

                        task_data = json.dumps({
                            'filename': record.get('filename'),
                            'offset': record.get('offset'),
                            'length': record.get('length'),
                            'url': url_original,
                            'timestamp': record.get('timestamp'),
                            'domain': domain
                        })

                        self.redis_client.lpush(self.queue_name, task_data)
                        self.redis_client.sadd(self.processed_urls_key, url_original)
                        count += 1

                    except json.JSONDecodeError:
                        continue

                return count, duplicates

            elif response.status_code == 404:
                return 0, 0
            else:
                print(f"Error HTTP: {response.status_code}", end=" ")
                return 0, 0

        except requests.exceptions.Timeout:
            print("Timeout", end=" ")
            return 0, 0
        except Exception as e:
            print(f"Error: {e}", end=" ")
            return 0, 0

    def get_queue_size(self):
        return self.redis_client.llen(self.queue_name)

    def get_processed_count(self):
        return self.redis_client.scard(self.processed_urls_key)

    def get_position(self):
        pos = self.redis_client.get(self.position_key)
        return int(pos) if pos else 0

    def set_position(self, position):
        self.redis_client.set(self.position_key, position)
