from .base import HTMLParser
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

class GenericHTMLParser(HTMLParser):
    """Универсальный HTML парсер"""
    
    def extract_news_items(self, soup):
        items = []
        
        # Ищем все возможные блоки с новостями
        possible_selectors = [
            'article', '.news-item', '.news', '.post', '.item', 
            '.material', '.story', '.article', '.news-list__item'
        ]
        
        news_blocks = []
        for selector in possible_selectors:
            news_blocks = soup.select(selector)
            if news_blocks:
                break
        
        if not news_blocks:
            # Ищем ссылки на новости
            all_links = soup.find_all('a', href=re.compile(r'news|article|post|story|item', re.I))
            for link in all_links[:50]:
                parent = link.find_parent(['div', 'li', 'section', 'article'])
                if parent:
                    news_blocks.append(parent)
        
        for block in news_blocks[:50]:
            # Заголовок
            title_elem = block.find(['h1', 'h2', 'h3', 'h4']) or block.find('a', href=True)
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)
            if not title or len(title) < 15:
                continue
            
            # Ссылка
            link_elem = block.find('a', href=True)
            if not link_elem:
                continue
            link = urljoin(self.url, link_elem['href'])
            
            # Дата
            date_elem = block.find('time', datetime=True) or block.find(class_=re.compile(r'date|time', re.I))
            pub_date = date_elem.get_text(strip=True) if date_elem else ''
            
            # Описание
            desc_elem = block.find('p') or block.find(class_=re.compile(r'desc|anons|preview', re.I))
            description = desc_elem.get_text(strip=True)[:500] if desc_elem else ''
            
            items.append({
                'title': title,
                'link': link,
                'date': pub_date,
                'description': description
            })
        
        # Удаляем дубликаты
        unique_items = {}
        for item in items:
            if item['link'] not in unique_items:
                unique_items[item['link']] = item
        
        return list(unique_items.values())