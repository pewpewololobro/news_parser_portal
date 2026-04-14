from urllib.parse import urlparse
import re
from bs4 import BeautifulSoup
from .base import RSSParser, HTMLParser
from .site_parsers import PARSER_MAP, GenericHTMLParser, RenTvParser

def get_parser(channel):
    """
    Возвращает подходящий парсер для канала
    """
    url = channel.html_desc
    if not url or url == '-' or url.strip() == '':
        url = channel.link
        if not url:
            raise Exception(f"URL канала '{channel.short_title}' не указан ни в html_desc, ни в link")
    
    # Проверяем наличие RSS ленты
    rss_indicators = ['.rss', '.xml', '/rss', '/feed', 'rss.xml', 'rss.php', 'feed.xml', '/atom']
    if any(indicator in url.lower() for indicator in rss_indicators):
        try:
            return RSSParser(channel, url)
        except:
            pass
    
    # Определяем CMS по мета-тегам (если возможно)
    try:
        import requests
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        
        generator = soup.find('meta', {'name': 'generator'})
        if generator:
            generator_content = generator.get('content', '').lower()
            if 'wordpress' in generator_content:
                from .site_parsers import WordPressParser
                return WordPressParser(channel, url)
            elif 'drupal' in generator_content:
                from .site_parsers import DrupalParser
                return DrupalParser(channel, url)
    except:
        pass
    
    # Ищем парсер для конкретного домена
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()
    
    domain = re.sub(r'^www\.', '', domain)
    domain = re.sub(r'^xn--80aaac0ct\.', '', domain)
    
    for site_domain, parser_class in PARSER_MAP.items():
        if site_domain in domain or domain in site_domain:
            return parser_class(channel, url)
    
    return GenericHTMLParser(channel, url)