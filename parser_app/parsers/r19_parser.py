from .base import HTMLParser
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import time

class R19Parser(HTMLParser):
    """Парсер для сайта r-19.ru/news"""
    
    def __init__(self, channel, url=None):
        super().__init__(channel, url)
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Google Chrome";v="120", "Not_A Brand";v="8", "Chromium";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def fetch_page_content(self, url):
        """Загружает страницу"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except Exception as e:
            raise Exception(f"Не удалось загрузить страницу {url}: {str(e)}")
    
    def extract_news_items(self, soup):
        items = []
        
        # Ищем div с классом block_news_list
        news_list = soup.find('div', class_='block_news_list')
        
        if not news_list:
            # Пробуем другие варианты
            news_list = soup.select_one('.block_news_list, .news-list, .news_list')
        
        if not news_list:
            print("  Не найден div.block_news_list")
            return []
        
        # Внутри ищем все div с классом block_news_list_b
        news_items = news_list.find_all('div', class_='block_news_list_b')
        
        if not news_items:
            # Пробуем другие селекторы внутри
            news_items = news_list.select('.block_news_list_b, .news-item, .item')
        
        print(f"  Найдено block_news_list_b: {len(news_items)}")
        
        for item in news_items[:30]:
            # Извлекаем ссылку (первая ссылка в блоке)
            link_elem = item.find('a', href=True)
            if not link_elem:
                continue
            
            link = link_elem.get('href')
            if not link:
                continue
            
            if not link.startswith('http'):
                link = urljoin('https://r-19.ru', link)
            
            # Извлекаем заголовок
            title = link_elem.get_text(strip=True)
            if not title or len(title) < 10:
                # Пробуем найти заголовок в других элементах
                title_elem = item.find(['h2', 'h3', 'h4']) or item.find(class_=re.compile(r'title', re.I))
                if title_elem:
                    title = title_elem.get_text(strip=True)
            
            if not title or len(title) < 10:
                continue
            
            # Извлекаем дату (если есть)
            pub_date = self.extract_date(item)
            
            # Извлекаем описание (анонс)
            description = self.extract_description(item)
            
            print(f"  Найдена новость: {title[:50]}...")
            
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
        
        print(f"  Уникальных новостей: {len(unique_items)}")
        return list(unique_items.values())
    
    def extract_date(self, item):
        """Извлекает дату из блока новости"""
        # Тег time
        time_elem = item.find('time')
        if time_elem:
            date = time_elem.get('datetime', '') or time_elem.get_text(strip=True)
            if date:
                return date
        
        # Элементы с классами даты
        date_selectors = ['.date', '.time', '.news-date', '.post-date', '.published', '.data']
        for selector in date_selectors:
            date_elem = item.select_one(selector)
            if date_elem:
                text = date_elem.get_text(strip=True)
                match = re.search(r'(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})', text)
                if match:
                    return match.group(1)
        
        # Ищем дату в тексте
        text = item.get_text()
        date_patterns = [
            r'(\d{2}\.\d{2}\.\d{4})',
            r'(\d{4}-\d{2}-\d{2})',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return ''
    
    def extract_description(self, item):
        """Извлекает описание/анонс новости"""
        # Ищем параграф
        p_elem = item.find('p')
        if p_elem:
            text = p_elem.get_text(strip=True)
            if len(text) > 40:
                return text[:500]
        
        # Ищем элементы с описанием
        desc_selectors = ['.description', '.anons', '.preview', '.excerpt', '.summary', '.text']
        for selector in desc_selectors:
            desc_elem = item.select_one(selector)
            if desc_elem:
                text = desc_elem.get_text(strip=True)
                if len(text) > 40:
                    return text[:500]
        
        return ''
    
    def extract_article_text(self, url, html=None):
        """Извлекает полный текст новости для описания"""
        try:
            if html is None:
                time.sleep(0.5)
                html = self.fetch_page_content(url)
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Удаляем лишние элементы
            for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                element.decompose()
            
            # Ищем основной контент
            content = None
            
            # Пробуем разные селекторы
            content_selectors = [
                '.news-text',
                '.article-text',
                '.post-content',
                '.entry-content',
                '.content',
                '.main-content',
                '.text-content',
                '.full-text',
                'article'
            ]
            
            for selector in content_selectors:
                content = soup.select_one(selector)
                if content and len(content.get_text(strip=True)) > 200:
                    print(f"      Найден контент по селектору: {selector}")
                    break
                content = None
            
            if not content:
                # Ищем все параграфы
                paragraphs = soup.find_all('p')
                if paragraphs:
                    text_paragraphs = []
                    for p in paragraphs:
                        p_text = p.get_text(strip=True)
                        if len(p_text) > 40:
                            text_paragraphs.append(p_text)
                    
                    if text_paragraphs:
                        print(f"      Найдено {len(text_paragraphs)} параграфов")
                        text = '\n\n'.join(text_paragraphs[:5])
                        return text[:2000]
            
            if content:
                # Собираем параграфы
                paragraphs = content.find_all('p')
                if paragraphs:
                    text_paragraphs = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40]
                    if text_paragraphs:
                        if len(text_paragraphs) > 3:
                            text = '\n\n'.join(text_paragraphs[:3])
                        else:
                            text = '\n\n'.join(text_paragraphs)
                        return text[:2000]
                
                text = content.get_text()
                lines = [line.strip() for line in text.splitlines() if line.strip() and len(line.strip()) > 30]
                return '\n'.join(lines)[:2000]
            
            return ''
            
        except Exception as e:
            print(f"      Ошибка извлечения текста: {e}")
            return ''
    
    def parse(self):
        try:
            if not self.url:
                raise Exception("URL канала не указан")
            
            print(f"  Загружаем: {self.url}")
            html = self.fetch_page_content(self.url)
            
            # Сохраняем для отладки
            with open('debug_r19.html', 'w', encoding='utf-8') as f:
                f.write(html)
            
            soup = BeautifulSoup(html, 'html.parser')
            items = self.extract_news_items(soup)
            
            if not items:
                print("  НЕ НАЙДЕНО НОВОСТЕЙ!")
                return 0
            
            added_count = 0
            for idx, item in enumerate(items[:30]):
                title = item.get('title', '')
                link = item.get('link', '')
                pub_date = item.get('date', '')
                description = item.get('description', '')
                
                print(f"\n  [{idx+1}/{len(items)}] {title[:60]}...")
                print(f"    Ссылка: {link}")
                print(f"    Дата: {pub_date}")
                
                # Если нет описания, получаем со страницы новости
                if not description:
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
                
                from core.models import Item
                if Item.objects.filter(link=link).exists():
                    print(f"    ✗ Пропущено (уже есть в базе)")
                    continue
                
                if self.save_item(title, link, pub_date, description, description):
                    added_count += 1
                    print(f"    ✓ Добавлено в базу")
                else:
                    print(f"    ✗ Ошибка при сохранении")
            
            print(f"\n  Всего добавлено: {added_count}")
            return added_count
        except Exception as e:
            raise Exception(f"Парсинг не удался: {str(e)}")