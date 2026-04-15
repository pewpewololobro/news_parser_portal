from .base import HTMLParser
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import time

class Rus19Parser(HTMLParser):
    """Парсер для сайта 19rus.ru"""
    
    def __init__(self, channel, url=None):
        super().__init__(channel, url)
        self.session.verify = False
    
    def extract_news_items(self, soup):
        items = []
        
        # Ищем новости (структура может отличаться)
        news_selectors = [
            '.news-item',
            '.post',
            'article',
            '.material',
            '.story',
            '.news-list__item'
        ]
        
        news_blocks = []
        for selector in news_selectors:
            news_blocks = soup.select(selector)
            if news_blocks:
                print(f"  Найдено новостей: {len(news_blocks)}")
                break
        
        for block in news_blocks[:30]:
            title_elem = block.find(['h2', 'h3', 'h4']) or block.find('a')
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)
            if not title or len(title) < 15:
                continue
            
            link_elem = title_elem if title_elem.name == 'a' else title_elem.find('a', href=True)
            if not link_elem:
                continue
            
            link = link_elem.get('href')
            if not link.startswith('http'):
                link = urljoin('https://www.19rus.ru', link)
            
            items.append({
                'title': title,
                'link': link,
                'date': '',
                'description': ''
            })
        
        return items
    
    def extract_article_text(self, url, html=None):
        try:
            if html is None:
                time.sleep(0.5)
                html = self.fetch_page_content(url)
            
            soup = BeautifulSoup(html, 'html.parser')
            
            for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer']):
                element.decompose()
            
            content = soup.select_one('.news-text, .article-text, .content, article')
            if content:
                paragraphs = content.find_all('p')
                if paragraphs:
                    text = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40])
                    return text[:2000]
                return content.get_text(strip=True)[:2000]
            return ''
        except Exception as e:
            print(f"  Ошибка: {e}")
            return ''