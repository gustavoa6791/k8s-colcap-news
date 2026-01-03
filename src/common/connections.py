import redis
import boto3
from botocore import UNSIGNED
from botocore.config import Config as BotoConfig
import time

from .config import Config

class RedisConnection:
    def __init__(self, host=None, port=None, db=None):
        self.host = host or Config.REDIS_HOST
        self.port = port or Config.REDIS_PORT
        self.db = db or Config.REDIS_DB
        self.client = None

    def connect(self, max_retries=None, retry_delay=None):
        max_retries = max_retries or Config.MAX_RETRIES
        retry_delay = retry_delay or Config.RETRY_DELAY

        for attempt in range(max_retries):
            try:
                self.client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db
                )
                self.client.ping()
                print(f"[Redis] Conectado a {self.host}:{self.port}")
                return self.client
            except Exception as e:
                print(f"[Redis] Intento {attempt + 1}/{max_retries} - Error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)

        return None

    def get_client(self):
        if self.client is None:
            return self.connect()
        try:
            self.client.ping()
            return self.client
        except:
            return self.connect()


class S3Connection:
    """conexión a S3 (Common Crawl)"""
    def __init__(self, region='us-east-1'):
        self.region = region
        self.client = None

    def connect(self):
        self.client = boto3.client(
            's3',
            region_name=self.region,
            config=BotoConfig(signature_version=UNSIGNED)
        )
        print(f"[S3] Cliente configurado para Common Crawl")
        return self.client

    def get_client(self):
        if self.client is None:
            return self.connect()
        return self.client
