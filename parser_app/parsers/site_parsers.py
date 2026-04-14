from .base import HTMLParser
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

class ShansOnlineParser(HTMLParser):
    """Парсер для shansonline.ru"""
    
    def extract_news_items(self, soup):
        items = []
        
        news_blocks = soup.select('.news-item, .news, .article, .story, article, .post')
        
        for block in news_blocks[:30]:
            link_elem = block.find('a', href=True)
            if not link_elem:
                continue
            
            title = link_elem.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            
            link = urljoin(self.url, link_elem['href'])
            
            date_elem = block.find(class_=re.compile(r'date|time|datetime', re.I))
            pub_date = date_elem.get_text(strip=True) if date_elem else ''
            
            desc_elem = block.find(class_=re.compile(r'desc|anons|preview|excerpt', re.I))
            description = desc_elem.get_text(strip=True) if desc_elem else ''
            
            items.append({
                'title': title,
                'link': link,
                'date': pub_date,
                'description': description
            })
        
        return items


class GenericHTMLParser(HTMLParser):
    """Улучшенный универсальный HTML парсер"""
    
    def extract_news_items(self, soup):
        items = []
        
        news_patterns = [
            r'news', r'article', r'post', r'story', r'view', r'item', 
            r'material', r'publication', r'novost', r'sobytie', r'event',
            r'n[\d]+', r'p[\d]+'
        ]
        
        possible_containers = soup.find_all(['article', 'div', 'li', 'section'], 
                                           class_=re.compile(r'(news|article|post|item|story)', re.I))
        
        if not possible_containers:
            possible_containers = soup.find_all('a', href=True)
        
        for container in possible_containers[:100]:
            if container.name == 'a':
                link_elem = container
                parent = container.parent
            else:
                link_elem = container.find('a', href=True)
                parent = container
            
            if not link_elem:
                continue
            
            href = link_elem.get('href', '')
            title = link_elem.get_text(strip=True)
            
            if not title or len(title) < 20 or len(title) > 200:
                continue
            
            is_news = any(re.search(pattern, href.lower()) for pattern in news_patterns)
            is_news = is_news or any(re.search(pattern, title.lower()) for pattern in news_patterns)
            
            if not is_news:
                continue
            
            link = urljoin(self.url, href)
            pub_date = self.find_date_in_context(parent or link_elem)
            description = self.find_description(container)
            
            items.append({
                'title': title,
                'link': link,
                'date': pub_date,
                'description': description
            })
        
        unique_items = {}
        for item in items:
            if item['link'] not in unique_items:
                unique_items[item['link']] = item
        
        return list(unique_items.values())
    
    def find_date_in_context(self, element):
        """Ищет дату в окружающих элементах"""
        date_patterns = [
            r'(\d{2}\.\d{2}\.\d{4})',
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{2}/\d{2}/\d{4})',
            r'(\d{1,2}\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4})',
            r'(\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{4})',
        ]
        
        for _ in range(5):
            if element:
                element_text = element.get_text()
                for pattern in date_patterns:
                    match = re.search(pattern, element_text, re.I)
                    if match:
                        return match.group(1)
                element = element.parent
            else:
                break
        
        return ''
    
    def find_description(self, container):
        """Ищет описание новости"""
        desc_selectors = [
            'p', '.desc', '.description', '.anons', '.preview', 
            '.excerpt', '.summary', '.lead', '.intro'
        ]
        
        for selector in desc_selectors:
            desc_elem = container.find(selector)
            if desc_elem:
                text = desc_elem.get_text(strip=True)
                if len(text) > 50:
                    return text[:500]
        
        first_p = container.find('p')
        if first_p:
            text = first_p.get_text(strip=True)
            if len(text) > 50:
                return text[:500]
        
        return ''


class RenTvParser(HTMLParser):
    """Специальный парсер для ren.tv с обходом защиты"""
    
    def __init__(self, channel, url=None):
        super().__init__(channel, url)
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Referer': 'https://ren.tv/',
        })
        
        try:
            self.session.get('https://ren.tv/', timeout=30)
        except:
            pass
    
    def fetch_page_content(self, url):
        """Переопределяем метод загрузки с обработкой редиректов и кук"""
        try:
            import time
            import random
            time.sleep(random.uniform(1, 3))
            
            response = self.session.get(url, timeout=30, allow_redirects=True)
            
            if response.status_code == 403:
                self.session.headers['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
                response = self.session.get(url, timeout=30)
                
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text
            
        except Exception as e:
            raise Exception(f"Не удалось загрузить страницу ren.tv: {str(e)}")
    
    def extract_news_items(self, soup):
        """Извлекает новости из списка на странице тега"""
        items = []
        
        news_blocks = soup.select('.news-item, .material, .post, article, .item, .story')
        
        if not news_blocks:
            all_links = soup.find_all('a', href=re.compile(r'/news/|/article/|/story/'))
            for link in all_links:
                parent = link.find_parent(['div', 'article', 'section'])
                if parent:
                    news_blocks.append(parent)
        
        for block in news_blocks[:30]:
            title_elem = block.find(['h1', 'h2', 'h3', 'h4'], 
                                   class_=re.compile(r'title|heading', re.I))
            if not title_elem:
                title_elem = block.find('a', class_=re.compile(r'title', re.I))
            if not title_elem:
                title_elem = block.find('a', href=re.compile(r'/news/|/article/'))
            
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)
            if not title or len(title) < 10:
                continue
            
            if title_elem.name == 'a':
                link = urljoin(self.url, title_elem.get('href', ''))
            else:
                link_elem = title_elem.find('a') or block.find('a', href=True)
                if not link_elem:
                    continue
                link = urljoin(self.url, link_elem.get('href', ''))
            
            date_elem = block.find('time', datetime=True) or block.find(class_=re.compile(r'date|time', re.I))
            pub_date = date_elem.get_text(strip=True) if date_elem else ''
            
            desc_elem = block.find(class_=re.compile(r'desc|anons|preview|excerpt', re.I)) or block.find('p')
            description = desc_elem.get_text(strip=True)[:500] if desc_elem else ''
            
            items.append({
                'title': title,
                'link': link,
                'date': pub_date,
                'description': description
            })
        
        return items
    
    def extract_article_text(self, url, html=None):
        """Извлекает текст статьи с защищенной страницы"""
        try:
            if html is None:
                html = self.fetch_page_content(url)
            
            soup = BeautifulSoup(html, 'html.parser')
            
            for element in soup.find_all(['script', 'style', 'noscript', 'iframe']):
                element.decompose()
            
            content = None
            content_selectors = [
                '.article-content', '.news-content', '.post-content',
                '.entry-content', '.text-content', '.article-body',
                '.material-content', '.story-content',
                '[itemprop="articleBody"]', '.full-story', '.main-text'
            ]
            
            for selector in content_selectors:
                content = soup.select_one(selector)
                if content and len(content.get_text(strip=True)) > 200:
                    break
            
            if content:
                for hidden in content.find_all(['script', 'style', 'button', 'form']):
                    hidden.decompose()
                text = content.get_text()
            else:
                paragraphs = soup.find_all('p')
                valid_paragraphs = []
                for p in paragraphs:
                    p_text = p.get_text(strip=True)
                    if (len(p_text) > 50 and 
                        'YaAdFoxActivate' not in p_text and 
                        'window.Ya' not in p_text and
                        'adfox' not in p_text.lower()):
                        valid_paragraphs.append(p_text)
                
                if valid_paragraphs:
                    text = '\n'.join(valid_paragraphs)
                else:
                    return ''
            
            lines = []
            for line in text.splitlines():
                line = line.strip()
                if (line and len(line) > 20 and 
                    'YaAdFoxActivate' not in line and 
                    'window.Ya' not in line and
                    'adfox' not in line.lower()):
                    lines.append(line)
            
            return '\n'.join(lines)[:10000]
            
        except Exception as e:
            print(f"Ошибка извлечения текста с ren.tv: {e}")
            return ''


# Обновленный словарь парсеров
PARSER_MAP = {
    'ren.tv': RenTvParser,
    'shansonline.ru': ShansOnlineParser,
    'xn--80aaac0ct.xn--p1ai': GenericHTMLParser,
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
    'r19.ru': GenericHTMLParser,
    'abakan.ru': GenericHTMLParser,
    'terra-19tv.ru': GenericHTMLParser,
    'xakac.info': GenericHTMLParser,
    'rg.ru': GenericHTMLParser,
    'tass.ru': GenericHTMLParser,
    'krk.sledcom.ru': GenericHTMLParser,
    'nalog.gov.ru': GenericHTMLParser,
    'sfr.gov.ru': GenericHTMLParser,
    '19.xn--b1aew.xn--p1ai': GenericHTMLParser,
}