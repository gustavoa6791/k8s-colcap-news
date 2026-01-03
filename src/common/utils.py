from datetime import datetime


def json_serial(obj):
    """Serializador JSON"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, '__str__') and 'ObjectId' in str(type(obj)):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def is_valid_news_url(url, excluded_patterns, news_sections):
    """Verifica URL de articulo valido """
    url_lower = url.lower()

    # Excluir patrones no deseados
    for pattern in excluded_patterns:
        if pattern in url_lower:
            return False

    # Preferir URLs con estructura de noticias
    has_section = any(section in url_lower for section in news_sections)

    # URLs con números al final suelen ser artículos
    has_article_id = any(c.isdigit() for c in url.split('/')[-1]) if '/' in url else False

    return has_section or has_article_id
