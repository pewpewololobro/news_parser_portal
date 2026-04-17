from .base import HTMLParser
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import time

class SfrParser(HTMLParser):
    """Парсер для сайта sfr.gov.ru/branches/khakasia/"""
    
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
        
        # Ищем все article с классом swiper-slide re-news-main__item
        articles = soup.find_all('article', class_='swiper-slide re-news-main__item')
        
        if not articles:
            # Пробуем другие варианты
            articles = soup.select('.swiper-slide.re-news-main__item, .re-news-main__item, .news-item')
        
        print(f"  Найдено article: {len(articles)}")
        
        for article in articles[:30]:
            # Извлекаем заголовок
            title_elem = article.find(['h1', 'h2', 'h3', 'h4']) or article.find('a', class_=re.compile(r'title', re.I))
            if not title_elem:
                title_elem = article.find('a', href=True)
            
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            
            # Извлекаем ссылку
            link_elem = title_elem if title_elem.name == 'a' else title_elem.find('a', href=True)
            if not link_elem:
                continue
            
            link = link_elem.get('href')
            if not link:
                continue
            
            if not link.startswith('http'):
                if link.startswith('/'):
                    link = 'https://sfr.gov.ru' + link
                else:
                    link = urljoin('https://sfr.gov.ru', link)
            
            # Извлекаем дату
            pub_date = self.extract_date(article)
            
            print(f"  Найдена новость: {title[:50]}...")
            print(f"    Дата: {pub_date}")
            print(f"    Ссылка: {link}")
            
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
        # Ищем тег time
        time_elem = article.find('time')
        if time_elem:
            date = time_elem.get('datetime', '') or time_elem.get_text(strip=True)
            if date:
                return date
        
        # Ищем элементы с классами даты
        date_selectors = ['.date', '.time', '.news-date', '.post-date', '.published', '.data']
        for selector in date_selectors:
            date_elem = article.select_one(selector)
            if date_elem:
                text = date_elem.get_text(strip=True)
                match = re.search(r'(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})', text)
                if match:
                    return match.group(1)
        
        # Ищем дату в тексте
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
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Удаляем лишние элементы
            for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                element.decompose()
            
            # Ищем основной контент на странице новости
            content = None
            
            # Пробуем разные селекторы для контента на сайте sfr.gov.ru
            content_selectors = [
                '.news-detail__text',
                '.article-text',
                '.news-text',
                '.post-content',
                '.entry-content',
                '.content',
                '.main-content',
                '.text-content',
                '.full-text',
                'article',
                '.detail-text',
                '.news-content'
            ]
            
            for selector in content_selectors:
                content = soup.select_one(selector)
                if content:
                    text_length = len(content.get_text(strip=True))
                    if text_length > 200:
                        print(f"      Найден контент по селектору: {selector} ({text_length} символов)")
                        break
                    content = None
            
            # Если не нашли, ищем все параграфы
            if not content:
                paragraphs = soup.find_all('p')
                if paragraphs:
                    text_paragraphs = []
                    for p in paragraphs:
                        p_text = p.get_text(strip=True)
                        if len(p_text) > 50:
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
                        if len(p_text) > 50:
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
                return '\n'.join(lines)[:2000]
            
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
            
            # Сохраняем для отладки
            with open('debug_sfr.html', 'w', encoding='utf-8') as f:
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
                
                print(f"\n  [{idx+1}/{len(items)}] {title[:60]}...")
                print(f"    Ссылка: {link}")
                
                # Получаем полный текст со страницы новости
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