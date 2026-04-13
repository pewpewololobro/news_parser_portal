from .base import HTMLParser
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

class ShansOnlineParser(HTMLParser):
    """Парсер для shansonline.ru"""
    
    def extract_news_items(self, soup):
        items = []
        
        # Пробуем разные селекторы для новостей
        selectors = [
            '.news-item',
            '.news',
            '.article',
            '.story',
            '.item',
            'article',
            '.post',
            '.material'
        ]
        
        news_blocks = []
        for selector in selectors:
            news_blocks = soup.select(selector)
            if news_blocks:
                break
        
        for block in news_blocks[:30]:
            # Ищем ссылку
            link_elem = block.find('a', href=True)
            if not link_elem:
                continue
            
            title = link_elem.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            
            link = urljoin(self.url, link_elem['href'])
            
            # Ищем дату
            date_selectors = ['date', 'time', 'data', 'datetime', 'published', 'date-info']
            pub_date = ''
            for selector in date_selectors:
                date_elem = block.find(class_=re.compile(selector, re.I))
                if date_elem:
                    pub_date = date_elem.get_text(strip=True)
                    break
            
            # Ищем описание
            desc_selectors = ['desc', 'text', 'anons', 'preview', 'excerpt', 'summary']
            description = ''
            for selector in desc_selectors:
                desc_elem = block.find(class_=re.compile(selector, re.I))
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                    break
            
            items.append((title, link, pub_date, description))
        
        return items


class GenericHTMLParser(HTMLParser):
    """Универсальный HTML парсер для сайтов без RSS"""
    
    def extract_news_items(self, soup):
        items = []
        
        # Ищем все ссылки, которые могут быть новостями
        common_patterns = [
            r'news', r'article', r'post', r'story', 
            r'view', r'item', r'material', r'publication',
            r'novost', r'sobytie', r'event'
        ]
        
        all_links = soup.find_all('a', href=True)
        
        for link_elem in all_links[:100]:
            href = link_elem.get('href', '')
            title = link_elem.get_text(strip=True)
            
            # Проверяем, похоже ли на новость
            if not title or len(title) < 20:
                continue
            
            # Проверяем URL на наличие признаков новости
            is_news = any(pattern in href.lower() for pattern in common_patterns)
            is_news = is_news or any(pattern in title.lower() for pattern in common_patterns)
            
            if not is_news:
                continue
            
            link = urljoin(self.url, href)
            
            # Ищем дату рядом со ссылкой
            parent = link_elem.parent
            date_patterns = [r'\d{2}\.\d{2}\.\d{4}', r'\d{4}-\d{2}-\d{2}', r'\d{2}/\d{2}/\d{4}']
            pub_date = ''
            
            for _ in range(3):
                if parent:
                    parent_text = parent.get_text()
                    for pattern in date_patterns:
                        match = re.search(pattern, parent_text)
                        if match:
                            pub_date = match.group()
                            break
                    if pub_date:
                        break
                    parent = parent.parent
                else:
                    break
            
            items.append((title, link, pub_date, ''))
        
        # Удаляем дубликаты по ссылке
        unique_items = {}
        for item in items:
            if item[1] not in unique_items:
                unique_items[item[1]] = item
        
        return list(unique_items.values())


# Обновленный словарь парсеров
PARSER_MAP = {
    'shansonline.ru': ShansOnlineParser,
    'xn--80aaac0ct.xn--p1ai': GenericHTMLParser,  # абакан.рф
    'ctv7.ru': GenericHTMLParser,
    'abakan-news.ru': GenericHTMLParser,
    'vskhakasia.ru': GenericHTMLParser,
    'gazeta19.ru': GenericHTMLParser,
    '19rusinfo.ru': GenericHTMLParser,
    '19rus.ru': GenericHTMLParser,
    'mk-hakasia.ru': GenericHTMLParser,
    'onf.ru': GenericHTMLParser,
    'r-19.ru': GenericHTMLParser,
    'pulse19.ru': GenericHTMLParser,
    'ren.tv': GenericHTMLParser,
    'r19.ru': GenericHTMLParser,
    'abakan.ru': GenericHTMLParser,
    'terra-19tv.ru': GenericHTMLParser,
    'xakac.info': GenericHTMLParser,
    'rg.ru': GenericHTMLParser,
    'tass.ru': GenericHTMLParser,
    'krk.sledcom.ru': GenericHTMLParser,
    'nalog.gov.ru': GenericHTMLParser,
    'sfr.gov.ru': GenericHTMLParser,
    '19.xn--b1aew.xn--p1ai': GenericHTMLParser,  # МВД РХ
}