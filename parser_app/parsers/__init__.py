from urllib.parse import urlparse
import re
from .base import RSSParser, HTMLParser
from .site_parsers import PARSER_MAP, GenericHTMLParser

def get_parser(channel):
    """
    Возвращает подходящий парсер для канала
    """
    # Сначала проверяем html_desc, если он пустой или '-', используем link
    url = channel.html_desc
    if not url or url == '-' or url.strip() == '':
        url = channel.link
        if not url:
            raise Exception(f"URL канала '{channel.short_title}' не указан ни в html_desc, ни в link")
    
    # Проверяем наличие RSS ленты
    rss_indicators = ['.rss', '.xml', '/rss', '/feed', 'rss.xml', 'rss.php', 'feed.xml']
    if any(indicator in url.lower() for indicator in rss_indicators):
        try:
            return RSSParser(channel, url)  # Передаем URL в парсер
        except:
            # Если RSS не работает, пробуем HTML
            pass
    
    # Ищем парсер для конкретного домена
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()
    
    # Убираем www и поддомены
    domain = re.sub(r'^www\.', '', domain)
    domain = re.sub(r'^xn--80aaac0ct\.', '', domain)  # Специально для абакан.рф
    
    # Пробуем найти точное совпадение
    for site_domain, parser_class in PARSER_MAP.items():
        if site_domain in domain or domain in site_domain:
            return parser_class(channel, url)  # Передаем URL в парсер
    
    # Если парсер не найден, используем универсальный HTML парсер
    return GenericHTMLParser(channel, url)  # Передаем URL в парсер