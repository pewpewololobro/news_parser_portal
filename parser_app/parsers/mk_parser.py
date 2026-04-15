from .base import HTMLParser
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import time
from datetime import datetime

class MkParser(HTMLParser):
    """Парсер для сайта mk-hakasia.ru"""
    
    def __init__(self, channel, url=None):
        super().__init__(channel, url)
        
        self.today_dot = datetime.now().strftime('%d.%m.%Y')
        self.today_text_ru = self.get_russian_date()
        print(f"  Сегодня: {self.today_dot} / {self.today_text_ru}")
    
    def get_russian_date(self):
        months = {
            1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
            5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
            9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
        }
        now = datetime.now()
        return f"{now.day} {months[now.month]} {now.year}"
    
    def normalize_date(self, date_string):
        if not date_string:
            return None
        date_string = date_string.lower().strip()
        if re.match(r'\d{2}\.\d{2}\.\d{4}', date_string):
            return date_string
        match = re.match(r'(\d{1,2})\s+([а-я]+)\s+(\d{4})', date_string)
        if match:
            day, month_ru, year = match.groups()
            months_map = {
                'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
                'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
                'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'
            }
            month = months_map.get(month_ru, '01')
            return f"{int(day):02d}.{month}.{year}"
        return None
    
    def is_today(self, date_string):
        if not date_string:
            return False
        normalized = self.normalize_date(date_string)
        return normalized == self.today_dot if normalized else False
    
    def fetch_page_content(self, url):
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except Exception as e:
            raise Exception(f"Не удалось загрузить страницу {url}: {str(e)}")
    
    def extract_news_items(self, soup):
        items = []
        
        day_groups = soup.find_all('section', class_='news-listing__day-group')
        print(f"  Найдено групп новостей: {len(day_groups)}")
        
        for group in day_groups:
            group_date = self.extract_group_date(group)
            print(f"  Группа с датой: {group_date}")
            
            if not self.is_today(group_date):
                print(f"    Пропускаем (не сегодня)")
                continue
            
            print(f"    Обрабатываем группу за сегодня")
            
            # Ищем все li с классом news-listing__item
            news_items = group.find_all('li', class_='news-listing__item')
            print(f"    Найдено li.news-listing__item: {len(news_items)}")
            
            for idx, item in enumerate(news_items[:30]):
                # Ищем заголовок
                title_elem = item.find(['h2', 'h3', 'h4'])
                if not title_elem:
                    title_elem = item.find('a')
                
                if not title_elem:
                    print(f"    Новость {idx+1}: не найден заголовок")
                    continue
                
                title = title_elem.get_text(strip=True)
                if not title or len(title) < 10:
                    print(f"    Новость {idx+1}: заголовок слишком короткий")
                    continue
                
                print(f"    Новость {idx+1}: {title[:60]}...")
                
                # Ищем ссылку - ОСНОВНАЯ ПРОБЛЕМА БЫЛА ЗДЕСЬ
                # Пробуем найти ссылку разными способами
                link = None
                
                # 1. Пробуем найти ссылку внутри заголовка
                if title_elem.name == 'a':
                    link = title_elem.get('href')
                else:
                    link_elem = title_elem.find('a', href=True)
                    if link_elem:
                        link = link_elem.get('href')
                
                # 2. Если не нашли, ищем любую ссылку внутри item
                if not link:
                    any_link = item.find('a', href=True)
                    if any_link:
                        link = any_link.get('href')
                
                # 3. Если все еще нет, ищем по паттерну
                if not link:
                    all_links = item.find_all('a', href=True)
                    for ln in all_links:
                        href = ln.get('href', '')
                        if '/news/' in href or '/2026/' in href:
                            link = href
                            break
                
                if not link:
                    print(f"      НЕ НАЙДЕНА ССЫЛКА")
                    continue
                
                if not link.startswith('http'):
                    link = urljoin('https://www.mk-hakasia.ru', link)
                
                print(f"      Ссылка: {link}")
                
                pub_date = self.extract_date(item)
                if not pub_date:
                    pub_date = group_date
                
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
        
        print(f"  Уникальных новостей за сегодня: {len(unique_items)}")
        return list(unique_items.values())
    
    def extract_group_date(self, group):
        title_elem = group.find(['h2', 'h3', 'h4'], class_=re.compile(r'title|date|head', re.I))
        if not title_elem:
            title_elem = group.find('h2')
        return title_elem.get_text(strip=True) if title_elem else ''
    
    def extract_date(self, item):
        time_elem = item.find('time')
        if time_elem:
            date = time_elem.get('datetime', '') or time_elem.get_text(strip=True)
            if date:
                return date
        return ''
    
    def extract_article_text(self, url, html=None):
        try:
            if html is None:
                time.sleep(0.5)
                html = self.fetch_page_content(url)
            
            soup = BeautifulSoup(html, 'html.parser')
            
            for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                element.decompose()
            
            content = None
            content_selectors = [
                '.article-text', '.news-text', '.post-content', '.entry-content',
                '.article-content', '.content', '.main-content', '.text-content',
                '.full-text', 'article'
            ]
            
            for selector in content_selectors:
                content = soup.select_one(selector)
                if content:
                    text_length = len(content.get_text(strip=True))
                    if text_length > 200:
                        print(f"      Найден контент ({text_length} символов)")
                        break
                    content = None
            
            if not content:
                paragraphs = soup.find_all('p')
                if paragraphs:
                    text_paragraphs = []
                    for p in paragraphs:
                        p_text = p.get_text(strip=True)
                        if len(p_text) > 40:
                            text_paragraphs.append(p_text)
                    if text_paragraphs:
                        text = '\n\n'.join(text_paragraphs[:5])
                        return text[:2000]
            
            if content:
                paragraphs = content.find_all('p')
                if paragraphs:
                    text_paragraphs = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40]
                    if text_paragraphs:
                        text = '\n\n'.join(text_paragraphs[:3])
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
            
            print(f"  Загружаем HTML: {self.url}")
            html = self.fetch_page_content(self.url)
            soup = BeautifulSoup(html, 'html.parser')
            items = self.extract_news_items(soup)
            
            if not items:
                print("  НЕ НАЙДЕНО НОВОСТЕЙ ЗА СЕГОДНЯ!")
                return 0
            
            added_count = 0
            for idx, item in enumerate(items[:30]):
                title = item.get('title', '')
                link = item.get('link', '')
                pub_date = item.get('date', '')
                
                print(f"\n  [{idx+1}/{len(items)}] {title[:60]}...")
                
                try:
                    full_text = self.extract_article_text(link)
                    description = full_text[:1000] if full_text else ''
                except Exception as e:
                    description = ''
                
                from core.models import Item
                if Item.objects.filter(link=link).exists():
                    print(f"    ✗ Уже есть в базе")
                    continue
                
                if self.save_item(title, link, pub_date, description, description):
                    added_count += 1
                    print(f"    ✓ Добавлено")
                else:
                    print(f"    ✗ Ошибка сохранения")
            
            return added_count
        except Exception as e:
            raise Exception(f"HTML parsing failed: {str(e)}")