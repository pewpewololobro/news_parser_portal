from .base import HTMLParser
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import time

class OnfParser(HTMLParser):
    """Парсер для сайта onf.ru/news"""
    
    def __init__(self, channel, url=None):
        super().__init__(channel, url)
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
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
        
        # Ищем div с id="content" и классом news-catalog
        news_catalog = soup.find('div', id='content', class_='news-catalog')
        
        if not news_catalog:
            news_catalog = soup.find('div', class_='news-catalog')
        
        if not news_catalog:
            print("  Не найден div.news-catalog")
            return []
        
        news_items = news_catalog.find_all('div', class_='news-catalog-item')
        print(f"  Найдено news-catalog-item: {len(news_items)}")
        
        for item in news_items[:30]:
            # Ищем ссылку
            link_elem = item.find('a', href=True)
            if not link_elem:
                continue
            
            link = link_elem.get('href')
            if not link:
                continue
            
            if not link.startswith('http'):
                link = urljoin('https://onf.ru', link)
            
            # Ищем div с классом text
            text_div = item.find('div', class_='text')
            
            # Извлекаем заголовок
            title = ''
            if text_div:
                title_div = text_div.find('div', class_='title')
                if title_div:
                    title = title_div.get_text(strip=True)
            
            if not title:
                title_elem = item.find(['h2', 'h3', 'h4']) or item.find('a', class_=re.compile(r'title', re.I))
                title = title_elem.get_text(strip=True) if title_elem else ''
            
            if not title or len(title) < 10:
                continue
            
            # Извлекаем дату
            pub_date = ''
            if text_div:
                date_div = text_div.find('div', class_='date')
                if date_div:
                    pub_date = date_div.get_text(strip=True)
            
            print(f"  Найдена новость: {title[:50]}...")
            
            items.append({
                'title': title,
                'link': link,
                'date': pub_date,
                'description': ''
            })
        
        unique_items = {}
        for item in items:
            if item['link'] not in unique_items:
                unique_items[item['link']] = item
        
        print(f"  Уникальных новостей: {len(unique_items)}")
        return list(unique_items.values())
    
    def extract_article_text(self, url, html=None):
        """Извлекает полный текст новости со страницы"""
        try:
            if html is None:
                time.sleep(0.5)
                html = self.fetch_page_content(url)
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Удаляем скрипты и стили
            for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                element.decompose()
            
            # Ищем основной контент
            content = None
            
            # Пробуем разные селекторы для контента
            content_selectors = [
                '.news-content',
                '.article-content',
                '.post-content',
                '.entry-content',
                '.content',
                '.main-content',
                '.text-content',
                '.full-text',
                'article',
                '.news-text'
            ]
            
            for selector in content_selectors:
                content = soup.select_one(selector)
                if content and len(content.get_text(strip=True)) > 200:
                    print(f"      Найден контент по селектору: {selector}")
                    break
                content = None
            
            # Если не нашли, ищем все параграфы
            if not content:
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
            
            print(f"      Не удалось найти контент на странице")
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
            
            soup = BeautifulSoup(html, 'html.parser')
            items = self.extract_news_items(soup)
            
            if not items:
                print("  НЕ НАЙДЕНО НОВОСТЕЙ!")
                return 0
            
            added_count = 0
            for idx, item in enumerate(items[:30]):
                title = item.get('title', '')
                link = item.get('link', '')
                pub_date = item.get('date', '')  # Дата со страницы
                
                print(f"\n  [{idx+1}/{len(items)}] {title[:60]}...")
                print(f"    Ссылка: {link}")
                print(f"    Исходная дата: '{pub_date}'")  # Отладка
                
                # Получаем полный текст
                try:
                    full_text = self.extract_article_text(link)
                    description = full_text[:1000] if full_text else ''
                except Exception as e:
                    print(f"    Ошибка получения текста: {e}")
                    description = ''
                
                # Проверяем существование
                from core.models import Item
                if Item.objects.filter(link=link).exists():
                    print(f"    ✗ Пропущено (уже есть в базе)")
                    continue
                
                # Сохраняем новость с ДАТОЙ
                print(f"    Передаем дату в save_item: '{pub_date}'")
                result = self.save_item(title, link, pub_date, description, description)
                
                if result:
                    added_count += 1
                    print(f"    ✓ Добавлено в базу")
                else:
                    print(f"    ✗ Ошибка при сохранении")
            
            print(f"\n  Всего добавлено: {added_count}")
            return added_count
        except Exception as e:
            raise Exception(f"Парсинг не удался: {str(e)}")