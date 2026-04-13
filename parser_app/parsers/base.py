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

class BaseParser:
    """Базовый класс для всех парсеров"""
    
    def __init__(self, channel, url=None):
        self.channel = channel
        # Используем переданный URL или берем из html_desc/link
        if url:
            self.url = url
        else:
            self.url = channel.html_desc
            if not self.url or self.url == '-':
                self.url = channel.link
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        # Отключаем проверку SSL для проблемных сайтов (осторожно!)
        self.session.verify = False
        # Игнорируем предупреждения SSL
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def parse(self):
        """Основной метод парсинга - должен быть переопределен"""
        raise NotImplementedError
    
    def save_item(self, title, link, pub_date, description):
        """Сохраняет новость, если её ещё нет"""
        if not title or not link:
            return False
        
        # Проверяем существование новости
        if Item.objects.filter(link=link).exists():
            return False
        
        # Парсим дату
        parsed_date = None
        if pub_date:
            parsed_date = self.parse_date(pub_date)
        
        # Если дата не распарсилась, используем текущую
        if not parsed_date:
            parsed_date = dj_timezone.now()
        
        # Создаем новость
        try:
            Item.objects.create(
                title=title[:500],
                link=link,
                pubDate=parsed_date,
                description=description[:5000] if description else '',
                channel=self.channel
            )
            return True
        except Exception as e:
            print(f"Ошибка сохранения новости: {e}")
            return False
    
    def parse_date(self, date_string):
        """Пытается распарсить дату из разных форматов"""
        if not date_string:
            return None
        
        # Список возможных форматов дат
        date_formats = [
            '%a, %d %b %Y %H:%M:%S %z',
            '%a, %d %b %Y %H:%M:%S %Z',
            '%a, %d %b %Y %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%d.%m.%Y %H:%M',
            '%d.%m.%Y',
            '%Y-%m-%d',
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_string.strip(), fmt)
                # Добавляем часовой пояс если его нет
                if dt.tzinfo is None:
                    dt = pytz.timezone('Asia/Krasnoyarsk').localize(dt)
                return dt
            except:
                continue
        
        return None


class RSSParser(BaseParser):
    """Парсер для RSS/Atom лент"""
    
    def parse(self):
        try:
            # Проверяем URL
            if not self.url:
                raise Exception("URL не указан")
            
            # Настройка feedparser для проблемных сайтов
            feedparser.USER_AGENT = self.session.headers['User-Agent']
            
            # Пробуем скачать через requests сначала (для SSL проблем)
            try:
                response = self.session.get(self.url, timeout=30)
                response.raise_for_status()
                content = response.content
                feed = feedparser.parse(content)
            except Exception as e:
                # Если не получилось через requests, пробуем напрямую feedparser
                feed = feedparser.parse(self.url)
            
            if feed.bozo and feed.bozo_exception:
                # Проверяем, не является ли это HTML страницей вместо RSS
                if 'not an XML media type' in str(feed.bozo_exception) or 'syntax error' in str(feed.bozo_exception):
                    # Пробуем как HTML
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
                
                if self.save_item(title, link, pub_date, description):
                    added_count += 1
            
            return added_count
        except Exception as e:
            raise Exception(f"RSS parsing failed: {str(e)}")


class HTMLParser(BaseParser):
    """Базовый HTML парсер - переопределяется для каждого сайта"""
    
    def __init__(self, channel, url=None):
        super().__init__(channel, url)
        # Игнорируем предупреждения BeautifulSoup
        import warnings
        from bs4 import XMLParsedAsHTMLWarning
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
    
    def extract_news_items(self, soup):
        """Должен вернуть список кортежей (title, link, date, description)"""
        raise NotImplementedError
    
    def parse(self):
        try:
            # Проверяем, что URL не пустой
            if not self.url:
                raise Exception("URL канала не указан")
            
            print(f"  Загружаем HTML: {self.url}")
            response = self.session.get(self.url, timeout=30)
            response.raise_for_status()
            
            # Определяем кодировку
            if response.encoding == 'ISO-8859-1':
                response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            items = self.extract_news_items(soup)
            
            added_count = 0
            for title, link, pub_date, description in items[:50]:
                if self.save_item(title, link, pub_date, description):
                    added_count += 1
            
            return added_count
        except Exception as e:
            raise Exception(f"HTML parsing failed: {str(e)}")