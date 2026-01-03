import os


class Config:
    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))

    # Worker
    WORKER_ID = os.getenv('HOSTNAME', 'worker-local')
    WORKER_TIMEOUT = int(os.getenv('WORKER_TIMEOUT', 5))

    # Datos
    COLCAP_DATA_PATH = os.getenv('COLCAP_DATA_PATH', 'data/colcap_historico.csv')

    # Producer (delays de Common Crawl)
    DELAY_BETWEEN_INDEXES = int(os.getenv('DELAY_BETWEEN_INDEXES', 15))
    DELAY_BETWEEN_DOMAINS = int(os.getenv('DELAY_BETWEEN_DOMAINS', 5))

    # Dominios objetivo
    _default_domains = "eltiempo.com,elespectador.com,portafolio.co,larepublica.co"
    TARGET_DOMAINS = os.getenv('TARGET_DOMAINS', _default_domains).split(',')

    # Common Crawl
    CC_INDEX_BASE_URL = "https://index.commoncrawl.org"
    CC_DATA_URL = "https://data.commoncrawl.org/"

    # Dashboard
    DASHBOARD_MAX_RESULTS = int(os.getenv('DASHBOARD_MAX_RESULTS', 500))

    # NLP - Palabras clave económicas
    ECONOMIC_KEYWORDS = [
        'economia', 'economía', 'bolsa', 'acciones', 'colcap', 'dolar', 'dólar',
        'peso', 'inflacion', 'inflación', 'banco', 'inversion', 'inversión',
        'mercado', 'finanzas', 'exportaciones', 'importaciones', 'pib', 'gdp',
        'desempleo', 'empleo', 'tasa', 'interes', 'interés', 'petroleo', 'petróleo',
        'cafe', 'café', 'carbon', 'carbón', 'oro', 'divisas', 'bvc', 'wall street'
    ]

    # Filtros de URLs
    EXCLUDED_PATTERNS = [
        'robots.txt', 'sitemap', '.xml', '.css', '.js', '.png', '.jpg',
        '.gif', '.ico', '.woff', '.ttf', '/tag/', '/autor/', '/autor-',
        '/buscar', '/search', '/login', '/registro', '/suscripcion',
        '/privacidad', '/terminos', '/contacto', '/rss', '/feed'
    ]

    NEWS_SECTIONS = [
        '/economia', '/finanzas', '/negocios', '/empresas', '/mercados',
        '/politica', '/noticias', '/actualidad', '/colombia', '/mundo',
        '/deportes', '/cultura', '/tecnologia', '/opinion'
    ]

    # Reintentos
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', 5))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', 5))
