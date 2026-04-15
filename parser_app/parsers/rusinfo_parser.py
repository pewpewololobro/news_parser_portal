from .base import HTMLParser
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import time

class RusinfoParser(HTMLParser):
    """Парсер для сайта 19rusinfo.ru"""
    
    def __init__(self, channel, url=None):
        super().__init__(channel, url)
        
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Referer': 'https://19rusinfo.ru/',
        })
        
        # Получаем cookies
        try:
            self.session.get('https://19rusinfo.ru/', timeout=30)
            time.sleep(1)
        except:
            pass
    
    def fetch_page_content(self, url):
        """Загружает страницу"""
        try:
            time.sleep(1)
            response = self.session.get(url, timeout=30, allow_redirects=True)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except Exception as e:
            raise Exception(f"Не удалось загрузить страницу {url}: {str(e)}")
    
    def extract_news_items(self, soup):
        items = []
        
        # Ищем все article с классом raxo-item-top
        articles = soup.find_all('article', class_='raxo-item-top')
        
        print(f"  Найдено article.raxo-item-top: {len(articles)}")
        
        for article in articles[:30]:
            # Извлекаем заголовок
            title_elem = article.find(['h1', 'h2', 'h3', 'h4'])
            if not title_elem:
                title_elem = article.find('a', href=True)
            
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)
            if not title or len(title) < 15:
                continue
            
            # Извлекаем ссылку
            link_elem = title_elem if title_elem.name == 'a' else title_elem.find('a', href=True)
            if not link_elem:
                continue
            
            link = link_elem.get('href')
            if not link:
                continue
                
            if not link.startswith('http'):
                link = urljoin('https://19rusinfo.ru', link)
            
            # Извлекаем дату
            pub_date = self.extract_date(article)
            
            items.append({
                'title': title,
                'link': link,
                'date': pub_date,
                'description': ''
            })
        
        # Удаляем дубликаты
        unique_items = {}
        for item in items:
            if item['link'] not in unique_items:
                unique_items[item['link']] = item
        
        print(f"  Уникальных новостей: {len(unique_items)}")
        return list(unique_items.values())
    
    def extract_date(self, article):
        """Извлекает дату из article"""
        time_elem = article.find('time')
        if time_elem:
            date = time_elem.get('datetime', '') or time_elem.get_text(strip=True)
            if date:
                return date
        
        text = article.get_text()
        date_patterns = [
            r'(\d{2}\.\d{2}\.\d{4})',
            r'(\d{4}-\d{2}-\d{2})',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return ''
    
    def extract_article_text(self, url, html=None):
        """Извлекает полный текст новости для описания"""
        try:
            if html is None:
                time.sleep(0.5)
                html = self.fetch_page_content(url)
            
            # Проверяем, не вернулась ли главная страница вместо новости
            if 'raxo-item-top' in html and len(html) < 50000:
                print(f"    Предупреждение: возможно, вернулась главная страница")
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Удаляем лишние элементы
            for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                element.decompose()
            
            # Ищем основной контент
            content = None
            
            # Пробуем разные селекторы для контента
            content_selectors = [
                '.news-text',
                '.article-text', 
                '.post-content',
                '.entry-content',
                '.content',
                '.main-content',
                '.text-content',
                '.full-text',
                '.detail-text',
                '.raxo-content',
                '.article-content'
            ]
            
            for selector in content_selectors:
                content = soup.select_one(selector)
                if content:
                    text_length = len(content.get_text(strip=True))
                    if text_length > 200:
                        print(f"    Найден контент по селектору: {selector} ({text_length} символов)")
                        break
                    else:
                        content = None
            
            # Если не нашли, ищем все параграфы подряд
            if not content:
                paragraphs = soup.find_all('p')
                if paragraphs:
                    text_paragraphs = []
                    for p in paragraphs:
                        p_text = p.get_text(strip=True)
                        if len(p_text) > 40:
                            text_paragraphs.append(p_text)
                    
                    if text_paragraphs:
                        content_text = '\n\n'.join(text_paragraphs[:5])
                        print(f"    Найдено параграфов: {len(text_paragraphs)}")
                        return content_text[:2000]
            
            if content:
                # Собираем параграфы из найденного контента
                paragraphs = content.find_all('p')
                if paragraphs:
                    text_paragraphs = []
                    for p in paragraphs:
                        p_text = p.get_text(strip=True)
                        if len(p_text) > 40:
                            text_paragraphs.append(p_text)
                    
                    if text_paragraphs:
                        if len(text_paragraphs) > 3:
                            text = '\n\n'.join(text_paragraphs[:3])
                        else:
                            text = '\n\n'.join(text_paragraphs)
                        return text[:2000]
                
                # Если нет параграфов, берем весь текст
                text = content.get_text()
                lines = [line.strip() for line in text.splitlines() if line.strip() and len(line.strip()) > 30]
                text = '\n'.join(lines)
                return text[:2000]
            
            print(f"    Не удалось найти контент на странице {url}")
            return ''
            
        except Exception as e:
            print(f"  Ошибка извлечения текста: {e}")
            return ''
    
    def parse(self):
        """Основной метод парсинга"""
        try:
            if not self.url:
                raise Exception("URL канала не указан")
            
            print(f"  Загружаем HTML: {self.url}")
            html = self.fetch_page_content(self.url)
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
                print(f"    URL: {link}")
                
                try:
                    full_text = self.extract_article_text(link)
                    description = full_text[:1000] if full_text else ''
                    if description:
                        print(f"    Текст получен: {len(description)} символов")
                    else:
                        print(f"    Текст не получен")
                except Exception as e:
                    print(f"    Ошибка получения текста: {e}")
                    description = ''
                
                if self.save_item(title, link, pub_date, description, description):
                    added_count += 1
                    print(f"    ✓ Добавлено")
                else:
                    print(f"    ✗ Пропущено (дубликат)")
            
            return added_count
        except Exception as e:
            raise Exception(f"HTML parsing failed: {str(e)}")