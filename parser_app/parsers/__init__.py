from urllib.parse import urlparse
import re
from .base import RSSParser, HTMLParser
from .site_parsers import GenericHTMLParser
from .abakan_parser import AbakanParser
from .adi19_parser import Adi19Parser
from .abakan_news_parser import AbakanNewsParser
from .vskhakasia_parser import VskhakasiaParser
from .rusinfo_parser import RusinfoParser
from .mk_parser import MkParser
from .rus19_parser import Rus19Parser
from .onf_parser import OnfParser
from .r19_parser import R19Parser
from .r19_journal_parser import R19JournalParser
from .abakan_ru_parser import AbakanRuParser
from .shansonline_parser import ShansonlineParser, ShansonlineHTMLParser    
from .sledcom_parser import SledcomParser
from .nalog_parser import NalogParser
from .sfr_parser import SfrParser

# Словарь парсеров для конкретных доменов
PARSER_MAP = {
    'xn--80aaac0ct.xn--p1ai': AbakanParser,
    'абакан.рф': AbakanParser,
    'adi19.ru': Adi19Parser,
    'xn----8sbafpsdo3dff2b1j.xn--p1ai': AbakanNewsParser,
    'vskhakasia.ru': VskhakasiaParser, 
    '19rusinfo.ru': RusinfoParser,
    'mk-hakasia.ru': MkParser, 
    'www.mk-hakasia.ru': MkParser,  
    '19rus.ru': Rus19Parser,
    'www.19rus.ru': Rus19Parser,
    'onf.ru': OnfParser,
    'www.onf.ru': OnfParser,
    'r-19.ru': R19Parser,
    'www.r-19.ru': R19Parser,
    'r19.ru/journal/news': R19JournalParser,
    'r19.ru': R19JournalParser,
    'abakan.ru': AbakanRuParser,
    'www.abakan.ru': AbakanRuParser,
    'shansonline.ru': ShansonlineParser, 
    'sledcom.ru': SledcomParser,
    'krk.sledcom.ru': SledcomParser,
    'nalog.gov.ru': NalogParser,
    'www.nalog.gov.ru': NalogParser,
    'sfr.gov.ru': SfrParser,
    'www.sfr.gov.ru': SfrParser,
}

def get_parser(channel):
    """
    Возвращает подходящий парсер для канала
    """
    # Определяем URL для парсинга
    url = None
    
    # Проверяем html_desc
    html_desc = channel.html_desc
    if html_desc and html_desc != '-' and html_desc.strip():
        if html_desc.startswith(('http://', 'https://')):
            url = html_desc
        elif '.' in html_desc and ' ' not in html_desc:
            url = 'https://' + html_desc
    
    # Если нет, пробуем link
    if not url:
        link = channel.link
        if link and link.startswith(('http://', 'https://')):
            url = link
        elif link and '.' in link and ' ' not in link:
            url = 'https://' + link
    
    if not url:
        raise Exception(f"URL канала не определен: html_desc='{channel.html_desc}', link='{channel.link}'")
    
    print(f"  URL: {url}")
    
    # Определяем домен для специальной обработки
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()
    domain = re.sub(r'^www\.', '', domain)
    
    # Специальная обработка для следкома (ДО проверки RSS)
    if 'sledcom.ru' in domain:
        print(f"  Используем специальный парсер: SledcomParser")
        return SledcomParser(channel, url)
    
    # Проверяем RSS для остальных сайтов
    rss_indicators = ['.rss', '.xml', '/rss', '/feed', 'rss.xml']
    if any(indicator in url.lower() for indicator in rss_indicators):
        try:
            return RSSParser(channel, url)
        except:
            pass
    
    # Ищем парсер в словаре
    for site_domain, parser_class in PARSER_MAP.items():
        if site_domain in domain or domain in site_domain:
            print(f"  Используем парсер: {parser_class.__name__}")
            return parser_class(channel, url)
    
    print(f"  Используем универсальный парсер: GenericHTMLParser")
    return GenericHTMLParser(channel, url)