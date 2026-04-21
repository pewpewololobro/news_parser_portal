from .base import RSSParser, HTMLParser
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import time
import feedparser

class ShansonlineParser(RSSParser):
    """Специальный парсер для shansonline.ru с правильными заголовками"""
    
    def __init__(self, channel, url=None):
        super().__init__(channel, url)
        # Специальные заголовки для shansonline.ru
        self.session.headers.update({
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        })
    
    def fetch_rss_content(self, url):
        """Загружает RSS ленту с правильными заголовками"""
        try:
            # Пробуем разные User-Agent
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (compatible; FeedFetcher/1.0; +http://www.google.com/feedfetcher.html)',
                'Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)',
            ]
            
            for ua in user_agents:
                self.session.headers['User-Agent'] = ua
                try:
                    response = self.session.get(url, timeout=30)
                    if response.status_code == 200:
                        break
                except:
                    continue
            
            response.raise_for_status()
            
            # Проверяем, что вернулся XML, а не HTML
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' in content_type and 'xml' not in content_type:
                # Если вернулся HTML, пробуем найти RSS ссылку в HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                rss_link = soup.find('link', type='application/rss+xml')
                if rss_link and rss_link.get('href'):
                    print(f"  Найдена RSS ссылка в HTML: {rss_link['href']}")
                    return self.fetch_rss_content(rss_link['href'])
                raise Exception("Вернулся HTML, а не RSS")
            
            return response.content
            
        except Exception as e:
            raise Exception(f"Не удалось загрузить RSS ленту: {str(e)}")
    
    def parse(self):
        """Парсинг RSS ленты"""
        try:
            if not self.url:
                raise Exception("URL не указан")
            
            print(f"  Загружаем RSS: {self.url}")
            
            # Загружаем содержимое RSS
            content = self.fetch_rss_content(self.url)
            
            # Парсим через feedparser
            feed = feedparser.parse(content)
            
            if feed.bozo and feed.bozo_exception:
                print(f"  Предупреждение при парсинге RSS: {feed.bozo_exception}")
            
            if not feed.entries:
                print("  RSS лента пуста")
                return 0
            
            added_count = 0
            for entry in feed.entries[:50]:
                title = entry.get('title', '')
                link = entry.get('link', '')
                pub_date = entry.get('published', entry.get('updated', ''))
                
                # Пробуем получить описание из разных полей
                description = ''
                if hasattr(entry, 'summary'):
                    description = entry.summary
                elif hasattr(entry, 'description'):
                    description = entry.description
                elif hasattr(entry, 'content'):
                    if entry.content:
                        description = entry.content[0].value
                
                # Очищаем описание от HTML тегов
                if description:
                    soup = BeautifulSoup(description, 'html.parser')
                    description = soup.get_text(strip=True)[:500]
                
                # Если описание слишком короткое, пробуем извлечь текст со страницы
                full_text = description
                if link and len(description) < 300:
                    try:
                        full_text = self.extract_article_text(link)
                    except Exception as e:
                        print(f"    Не удалось извлечь текст со страницы: {e}")
                
                if self.save_item(title, link, pub_date, description, full_text):
                    added_count += 1
                    print(f"    ✓ Добавлено: {title[:50]}...")
                else:
                    print(f"    ✗ Пропущено: {title[:50]}...")
            
            return added_count
            
        except Exception as e:
            raise Exception(f"RSS parsing failed: {str(e)}")


class ShansonlineHTMLParser(HTMLParser):
    """HTML парсер для shansonline.ru на случай, если RSS не работает"""
    
    def extract_news_items(self, soup):
        items = []
        
        # Ищем новости на странице
        news_selectors = [
            '.news-item',
            '.news',
            'article',
            '.post',
            '.material',
            '.item',
            '.story'
        ]
        
        news_items = []
        for selector in news_selectors:
            news_items = soup.select(selector)
            if news_items:
                print(f"  Найдено новостей: {len(news_items)}")
                break
        
        for item in news_items[:30]:
            # Заголовок
            title_elem = item.find(['h1', 'h2', 'h3', 'h4']) or item.find('a')
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)
            if not title or len(title) < 10:
                continue
            
            # Ссылка
            link_elem = title_elem if title_elem.name == 'a' else title_elem.find('a', href=True)
            if not link_elem:
                continue
            
            link = link_elem.get('href')
            if not link.startswith('http'):
                link = urljoin('https://shansonline.ru', link)
            
            # Дата
            pub_date = self.extract_date(item)
            
            # Описание
            description = self.extract_description(item)
            
            items.append({
                'title': title,
                'link': link,
                'date': pub_date,
                'description': description
            })
        
        return items
    
    def extract_date(self, item):
        """Извлекает дату"""
        time_elem = item.find('time')
        if time_elem:
            return time_elem.get('datetime', '') or time_elem.get_text(strip=True)
        
        date_selectors = ['.date', '.time', '.news-date', '.post-date']
        for selector in date_selectors:
            date_elem = item.select_one(selector)
            if date_elem:
                return date_elem.get_text(strip=True)
        
        return ''
    
    def extract_description(self, item):
        """Извлекает описание"""
        p_elem = item.find('p')
        if p_elem:
            text = p_elem.get_text(strip=True)
            if len(text) > 40:
                return text[:500]
        return ''
    
    def parse(self):
        try:
            if not self.url:
                raise Exception("URL канала не указан")
            
            print(f"  Загружаем HTML: {self.url}")
            html = self.fetch_page_content(self.url)
            soup = BeautifulSoup(html, 'html.parser')
            items = self.extract_news_items(soup)
            
            added_count = 0
            for item in items[:30]:
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