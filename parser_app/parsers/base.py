import hashlib
import requests
from bs4 import BeautifulSoup
import feedparser
from datetime import datetime
from django.utils import timezone as dj_timezone
from core.models import Item, Channel
import pytz
import re
import ssl
from urllib.parse import urlparse
import random

class BaseParser:
    """Базовый класс для всех парсеров"""
    
    def __init__(self, channel, url=None):
        self.channel = channel
        if url:
            self.url = url
        else:
            self.url = channel.html_desc
            if not self.url or self.url == '-':
                self.url = channel.link
        
        self.session = requests.Session()
        
        # Ротация User-Agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
        ]
        
        self.session.headers.update({
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        self.session.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def parse(self):
        raise NotImplementedError
    
    def fetch_page_content(self, url):
        """Загружает страницу и возвращает HTML"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Определяем кодировку
            if response.encoding == 'ISO-8859-1':
                soup = BeautifulSoup(response.content[:10000], 'html.parser')
                meta_charset = soup.find('meta', charset=True)
                if meta_charset:
                    response.encoding = meta_charset['charset']
                else:
                    meta = soup.find('meta', attrs={'http-equiv': 'Content-Type'})
                    if meta and 'charset=' in meta.get('content', ''):
                        charset = meta['content'].split('charset=')[-1]
                        response.encoding = charset
                    else:
                        response.encoding = 'utf-8'
            
            return response.text
        except Exception as e:
            raise Exception(f"Не удалось загрузить страницу {url}: {str(e)}")
    
    def extract_article_text(self, url, html=None):
        """Извлекает основной текст статьи с помощью readability"""
        try:
            if html is None:
                html = self.fetch_page_content(url)
            
            # Используем readability-lxml для извлечения основного контента
            from readability import Document
            doc = Document(html)
            article_text = doc.summary()
            
            soup = BeautifulSoup(article_text, 'html.parser')
            
            # Удаляем ненужные элементы
            for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'iframe']):
                element.decompose()
            
            text = soup.get_text()
            
            # Очищаем текст от лишних пробелов и пустых строк
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = '\n'.join(lines)
            
            # Фильтруем рекламный код
            if 'YaAdFoxActivate' in text or 'window.Ya' in text:
                text = self._extract_text_alternative(soup, html)
            
            # Если текст слишком короткий (< 500 символов), пробуем альтернативные методы
            if len(text) < 500:
                text = self._extract_text_alternative(soup, html)
            
            return text[:10000]
            
        except Exception as e:
            print(f"Ошибка извлечения текста статьи: {e}")
            return ''
    
    def _extract_text_alternative(self, soup, html):
        """Альтернативный метод извлечения текста"""
        # Пробуем найти контент по типичным CSS селекторам
        content_selectors = [
            '.article-content', '.post-content', '.entry-content', 
            '.content', '.main-content', '.story-content', '.news-content',
            'article', '.post-body', '.entry-body', '.text-content',
            '[itemprop="articleBody"]', '.field-name-body', '.node-content',
            '.material-content', '.full-story', '.main-text'
        ]
        
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                for element in content.find_all(['script', 'style']):
                    element.decompose()
                text = content.get_text()
                text = '\n'.join([line.strip() for line in text.splitlines() if line.strip()])
                if len(text) > 200 and 'YaAdFoxActivate' not in text:
                    return text
        
        # Пробуем собрать все параграфы
        paragraphs = soup.find_all('p')
        valid_paragraphs = []
        for p in paragraphs:
            p_text = p.get_text(strip=True)
            if len(p_text) > 50 and 'YaAdFoxActivate' not in p_text and 'window.Ya' not in p_text:
                valid_paragraphs.append(p_text)
        
        if valid_paragraphs:
            return '\n'.join(valid_paragraphs)
        
        return ''
    
    def save_item(self, title, link, pub_date, description, full_text=''):
        """Сохраняет новость с полным текстом"""
        if not title or not link:
            print(f"    save_item: пропущено - нет заголовка или ссылки")
            return False
        
        # Проверяем существование новости
        if Item.objects.filter(link=link).exists():
            print(f"    save_item: новость уже существует")
            return False
        
        print(f"    save_item: получена дата '{pub_date}'")
        
        # Парсим дату
        parsed_date = None
        if pub_date:
            parsed_date = self.parse_date(pub_date)
            if parsed_date:
                print(f"    save_item: дата распаршена в {parsed_date}")
            else:
                print(f"    save_item: НЕ УДАЛОСЬ распарсить дату '{pub_date}'")
        
        # Если дата не распарсилась, используем текущую
        if not parsed_date:
            parsed_date = dj_timezone.now()
            print(f"    save_item: используем ТЕКУЩУЮ дату {parsed_date}")
        
        # Создаем новость
        try:
            item = Item.objects.create(
                title=title[:500],
                link=link,
                pubDate=parsed_date,
                description=full_text[:5000] if full_text else (description[:5000] if description else ''),
                channel=self.channel
            )
            print(f"    save_item: сохранено с датой {item.pubDate}")
            return True
        except Exception as e:
            print(f"    save_item: ошибка сохранения {e}")
            return False
    
    def parse_date(self, date_string):
        """Пытается распарсить дату из разных форматов"""
        if not date_string:
            print(f"      parse_date: пустая дата")
            return None
        
        print(f"      parse_date: пробуем распарсить '{date_string}'")
        
        # Замена русских месяцев на английские
        months_ru_en = {
            'января': 'January', 'февраля': 'February', 'марта': 'March',
            'апреля': 'April', 'мая': 'May', 'июня': 'June',
            'июля': 'July', 'августа': 'August', 'сентября': 'September',
            'октября': 'October', 'ноября': 'November', 'декабря': 'December'
        }
        
        date_eng = date_string
        for ru, en in months_ru_en.items():
            if ru in date_eng.lower():
                date_eng = date_eng.lower().replace(ru, en)
                print(f"      parse_date: заменили {ru} на {en} -> '{date_eng}'")
                break
        
        # Форматы дат
        date_formats = [
            '%d %B %Y',      # 15 April 2026
            '%d.%m.%Y',      # 15.04.2026
            '%Y-%m-%d',      # 2026-04-15
            '%d.%m.%Y %H:%M',
            '%Y-%m-%d %H:%M:%S',
            '%d %b %Y',
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_eng.strip(), fmt)
                if dt.tzinfo is None:
                    dt = pytz.timezone('Asia/Krasnoyarsk').localize(dt)
                print(f"      parse_date: успешно распаршено как '{fmt}' -> {dt}")
                return dt
            except:
                continue
        
        print(f"      parse_date: НЕ УДАЛОСЬ распарсить '{date_string}'")
        return None


class RSSParser(BaseParser):
    """Парсер для RSS/Atom лент"""
    
    def parse(self):
        try:
            if not self.url:
                raise Exception("URL не указан")
            
            feedparser.USER_AGENT = self.session.headers['User-Agent']
            
            try:
                response = self.session.get(self.url, timeout=30)
                response.raise_for_status()
                content = response.content
                feed = feedparser.parse(content)
            except Exception as e:
                feed = feedparser.parse(self.url)
            
            if feed.bozo and feed.bozo_exception:
                if 'not an XML media type' in str(feed.bozo_exception) or 'syntax error' in str(feed.bozo_exception):
                    raise Exception("Not an RSS feed, trying HTML parser")
                raise Exception(f"RSS parsing error: {feed.bozo_exception}")
            
            if not feed.entries:
                return 0
            
            added_count = 0
            for entry in feed.entries[:50]:
                title = entry.get('title', '')
                link = entry.get('link', '')
                pub_date = entry.get('published', entry.get('updated', ''))
                description = entry.get('summary', entry.get('description', ''))
                
                full_text = description
                if link and len(description) < 500:
                    try:
                        full_text = self.extract_article_text(link)
                    except:
                        pass
                
                if self.save_item(title, link, pub_date, description, full_text):
                    added_count += 1
            
            return added_count
        except Exception as e:
            raise Exception(f"RSS parsing failed: {str(e)}")


class HTMLParser(BaseParser):
    """Базовый HTML парсер"""
    
    def __init__(self, channel, url=None):
        super().__init__(channel, url)
        import warnings
        from bs4 import XMLParsedAsHTMLWarning
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
    
    def extract_news_items(self, soup):
        """Должен вернуть список словарей с данными новостей"""
        raise NotImplementedError
    
    def parse(self):
        try:
            if not self.url:
                raise Exception("URL канала не указан")
            
            print(f"  Загружаем HTML: {self.url}")
            html = self.fetch_page_content(self.url)
            soup = BeautifulSoup(html, 'html.parser')
            items = self.extract_news_items(soup)
            
            added_count = 0
            for item in items[:50]:
                title = item.get('title', '')
                link = item.get('link', '')
                pub_date = item.get('date', '')
                description = item.get('description', '')
                
                full_text = description
                if link and len(description) < 500:
                    try:
                        full_text = self.extract_article_text(link)
                    except:
                        pass
                
                if self.save_item(title, link, pub_date, description, full_text):
                    added_count += 1
            
            return added_count
        except Exception as e:
            raise Exception(f"HTML parsing failed: {str(e)}")
    
    