from .base import RSSParser, HTMLParser
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import time
import feedparser
import gzip
import zlib

class SledcomParser(RSSParser):
    """Специальный парсер для krk.sledcom.ru с поддержкой сжатых ответов"""
    
    def __init__(self, channel, url=None):
        super().__init__(channel, url)
        self.session.headers.update({
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate',  # Поддержка сжатия
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Referer': 'https://krk.sledcom.ru/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        })
    
    def decompress_response(self, response):
        """Декомпрессия сжатого ответа"""
        content = response.content
        content_encoding = response.headers.get('Content-Encoding', '').lower()
        
        print(f"    Content-Encoding: {content_encoding}")
        
        if content_encoding == 'gzip':
            try:
                content = gzip.decompress(content)
                print(f"    Распакован gzip, длина: {len(content)}")
            except Exception as e:
                print(f"    Ошибка распаковки gzip: {e}")
        elif content_encoding == 'deflate':
            try:
                content = zlib.decompress(content)
                print(f"    Распакован deflate, длина: {len(content)}")
            except:
                try:
                    content = zlib.decompress(content, -zlib.MAX_WBITS)
                    print(f"    Распакован deflate (raw), длина: {len(content)}")
                except Exception as e:
                    print(f"    Ошибка распаковки deflate: {e}")
        
        return content
    
    def fetch_rss_content(self, url):
        """Загружает и декомпрессирует RSS ленту"""
        try:
            response = self.session.get(url, timeout=30, verify=False)
            response.raise_for_status()
            
            # Декомпрессия
            content = self.decompress_response(response)
            
            # Пробуем декодировать в текст
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = content.decode('windows-1251')
                except:
                    text = content.decode('utf-8', errors='ignore')
            
            # Проверяем, что получили XML
            if not text.strip():
                raise Exception("Пустой ответ")
            
            if not text.strip().startswith('<?xml') and not text.strip().startswith('<rss'):
                print(f"    Начало ответа: {text[:100]}")
                raise Exception("Ответ не является RSS XML")
            
            return text
            
        except Exception as e:
            raise Exception(f"Не удалось загрузить RSS: {str(e)}")
    
    def parse(self):
        try:
            if not self.url:
                raise Exception("URL не указан")
            
            print(f"  Загружаем RSS: {self.url}")
            
            # Пробуем разные URL
            urls_to_try = [
                self.url,
                'https://krk.sledcom.ru/news/rss.xml',
                'https://krk.sledcom.ru/rss.xml',
            ]
            
            rss_content = None
            for url_try in urls_to_try:
                try:
                    print(f"    Пробуем: {url_try}")
                    rss_content = self.fetch_rss_content(url_try)
                    if rss_content:
                        print(f"    Успешно загружено, длина: {len(rss_content)}")
                        break
                except Exception as e:
                    print(f"    Ошибка: {e}")
                    continue
            
            if not rss_content:
                print("  RSS не работает, пробуем HTML парсер")
                html_parser = SledcomHTMLParser(self.channel, 'https://krk.sledcom.ru/news/')
                return html_parser.parse()
            
            # Парсим RSS
            feed = feedparser.parse(rss_content)
            
            if feed.bozo:
                print(f"  Предупреждение при парсинге: {feed.bozo_exception}")
            
            if not feed.entries:
                print("  RSS лента пуста, пробуем HTML парсер")
                html_parser = SledcomHTMLParser(self.channel, 'https://krk.sledcom.ru/news/')
                return html_parser.parse()
            
            added_count = 0
            for entry in feed.entries[:50]:
                title = entry.get('title', '')
                link = entry.get('link', '')
                pub_date = entry.get('published', entry.get('updated', ''))
                
                description = ''
                if hasattr(entry, 'summary'):
                    description = entry.summary
                elif hasattr(entry, 'description'):
                    description = entry.description
                
                if description:
                    soup = BeautifulSoup(description, 'html.parser')
                    description = soup.get_text(strip=True)[:500]
                
                full_text = description
                if link and len(description) < 300:
                    try:
                        full_text = self.extract_article_text(link)
                    except Exception as e:
                        print(f"    Не удалось извлечь текст: {e}")
                
                if self.save_item(title, link, pub_date, description, full_text):
                    added_count += 1
                    print(f"    ✓ Добавлено: {title[:50]}...")
            
            return added_count
            
        except Exception as e:
            print(f"  Ошибка, пробуем HTML парсер: {e}")
            html_parser = SledcomHTMLParser(self.channel, 'https://krk.sledcom.ru/news/')
            return html_parser.parse()


class SledcomHTMLParser(HTMLParser):
    """HTML парсер для krk.sledcom.ru/news/"""
    
    def fetch_page_content(self, url):
        """Загружает HTML страницу"""
        try:
            response = self.session.get(url, timeout=30, verify=False)
            response.raise_for_status()
            
            # Декомпрессия
            content = response.content
            content_encoding = response.headers.get('Content-Encoding', '').lower()
            
            if content_encoding == 'gzip':
                content = gzip.decompress(content)
            elif content_encoding == 'deflate':
                try:
                    content = zlib.decompress(content)
                except:
                    content = zlib.decompress(content, -zlib.MAX_WBITS)
            
            # Декодирование
            try:
                text = content.decode('utf-8')
            except:
                try:
                    text = content.decode('windows-1251')
                except:
                    text = content.decode('utf-8', errors='ignore')
            
            return text
            
        except Exception as e:
            raise Exception(f"Не удалось загрузить страницу: {str(e)}")
    
    def extract_news_items(self, soup):
        items = []
        
        # Ищем новости по разным селекторам
        news_selectors = [
            '.news-item',
            '.item-news', 
            '.news',
            'article',
            '.post',
            '.material',
            'a[href*="/news/"]'
        ]
        
        news_items = []
        for selector in news_selectors:
            news_items = soup.select(selector)
            if news_items:
                print(f"  Найдено по селектору '{selector}': {len(news_items)}")
                break
        
        # Если не нашли, ищем ссылки на новости
        if not news_items:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')
                if '/news/' in href:
                    title = link.get_text(strip=True)
                    if title and len(title) > 15:
                        news_items.append(link)
            print(f"  Найдено по ссылкам: {len(news_items)}")
        
        for item in news_items[:30]:
            # Заголовок и ссылка
            if item.name == 'a':
                title = item.get_text(strip=True)
                link = item.get('href')
            else:
                title_elem = item.find(['h1', 'h2', 'h3', 'h4']) or item.find('a')
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                link_elem = title_elem if title_elem.name == 'a' else title_elem.find('a', href=True)
                if not link_elem:
                    continue
                link = link_elem.get('href')
            
            if not title or len(title) < 10:
                continue
            
            if not link:
                continue
                
            if not link.startswith('http'):
                link = urljoin('https://krk.sledcom.ru', link)
            
            # Дата
            pub_date = ''
            date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', str(item))
            if date_match:
                pub_date = date_match.group(1)
            
            items.append({
                'title': title,
                'link': link,
                'date': pub_date,
                'description': ''
            })
        
        return items
    
    def parse(self):
        try:
            print(f"  Загружаем HTML: {self.url}")
            html = self.fetch_page_content(self.url)
            
            # Сохраняем для отладки
            with open('debug_sledcom.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("  HTML сохранен в debug_sledcom.html")
            
            soup = BeautifulSoup(html, 'html.parser')
            items = self.extract_news_items(soup)
            
            if not items:
                print("  НЕ НАЙДЕНО НОВОСТЕЙ!")
                return 0
            
            added_count = 0
            for item in items[:30]:
                title = item.get('title', '')
                link = item.get('link', '')
                pub_date = item.get('date', '')
                
                print(f"  Обрабатываем: {title[:50]}...")
                
                full_text = ''
                try:
                    full_text = self.extract_article_text(link)
                except Exception as e:
                    print(f"    Ошибка получения текста: {e}")
                
                if self.save_item(title, link, pub_date, full_text, full_text):
                    added_count += 1
                    print(f"    ✓ Добавлено")
                else:
                    print(f"    ✗ Пропущено")
            
            return added_count
        except Exception as e:
            raise Exception(f"HTML parsing failed: {str(e)}")