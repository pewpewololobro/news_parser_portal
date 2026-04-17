from .base import HTMLParser
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import time

class R19JournalParser(HTMLParser):
    """Парсер для сайта r19.ru/journal/news"""
    
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
    
    def clean_title(self, title):
        """Очищает заголовок от даты, месяца и количества просмотров"""
        if not title:
            return title
        
        print(f"      Очистка: '{title}'")
        
        # 1. Удаляем всё, что в начале до первой буквы (цифры, пробелы, точки)
        # Находим позицию первой русской или английской буквы
        match = re.search(r'[А-Яа-яA-Za-z]', title)
        if match:
            start_pos = match.start()
            if start_pos > 0:
                title = title[start_pos:]
        
        # 2. Удаляем названия месяцев в начале (с маленькой или большой буквы)
        months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 
                'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
                'январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
                'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь']
        
        for month in months:
            if title.lower().startswith(month):
                title = title[len(month):]
                break
            if title.lower().startswith(month.capitalize()):
                title = title[len(month.capitalize()):]
                break
        
        # 3. Удаляем любые оставшиеся цифры в начале
        title = re.sub(r'^\d+', '', title)
        
        # 4. Удаляем количество просмотров в конце
        title = re.sub(r'\s+\d+$', '', title)
        
        # 5. Удаляем лишние пробелы и тире в начале
        title = re.sub(r'^\s*[-–—]\s*', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        
        print(f"      Результат: '{title}'")
        return title if title else original
    
    def extract_news_items(self, soup):
        items = []
        
        # Ищем div с классом journal-main-list
        main_list = soup.find('div', class_='journal-main-list')
        
        if not main_list:
            main_list = soup.select_one('.journal-main-list, .main-list, .journal-list')
        
        if not main_list:
            print("  Не найден div.journal-main-list")
            return []
        
        # Ищем все ссылки на новости
        all_links = main_list.find_all('a', href=True)
        
        news_links = []
        for link in all_links:
            href = link.get('href', '')
            # Ссылки на новости обычно содержат /journal/news/ или /news/
            if '/journal/news/' in href or '/news/' in href:
                link_text = link.get_text(strip=True)
                # Пропускаем ссылки "Читать далее" и пустые
                if link_text and 'далее' not in link_text.lower() and len(link_text) > 3:
                    news_links.append(link)
        
        if news_links:
            print(f"  Найдено ссылок на новости: {len(news_links)}")
            
            for link in news_links[:30]:
                title = link.get_text(strip=True)
                title = self.clean_title(title)
                print("Коля тут тест:",title)
                
                if not title or len(title) < 3:
                    continue
                
                link_url = link.get('href')
                if not link_url.startswith('http'):
                    link_url = urljoin('https://r19.ru', link_url)
                
                # Ищем дату рядом со ссылкой
                pub_date = self.extract_date_from_parent(link)
                
                items.append({
                    'title': title,
                    'link': link_url,
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
    
    def extract_date_from_parent(self, link_elem):
        """Извлекает дату из родительских элементов ссылки"""
        current = link_elem
        for _ in range(5):
            if current:
                text = current.get_text()
                
                # Формат "14 апреля"
                match = re.search(r'(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)', text)
                if match:
                    day, month_ru = match.groups()
                    from datetime import datetime
                    year = datetime.now().year
                    months = {
                        'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
                        'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
                        'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
                    }
                    month = months.get(month_ru, 1)
                    return f"{int(day):02d}.{month:02d}.{year}"
                
                # Формат "14.04.2026"
                match = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
                if match:
                    return match.group(1)
                
                current = current.parent
            else:
                break
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
                '.journal-content',
                '.article-content',
                '.news-content',
                '.post-content',
                '.entry-content',
                '.content',
                '.main-content',
                '.text-content',
                '.full-text',
                'article',
                '.journal-text',
                '.news-text',
                '.detail-text',
                '.article-text',
                '.material-content',
                '.page-content',
                '.view-content',
                '.field-name-body',
                '.body-content'
            ]
            
            for selector in content_selectors:
                content = soup.select_one(selector)
                if content:
                    text_length = len(content.get_text(strip=True))
                    if text_length > 200:
                        print(f"      Найден контент по селектору: {selector} ({text_length} символов)")
                        break
                    content = None
            
            # Если не нашли, ищем div с классом, содержащим 'content'
            if not content:
                for div in soup.find_all('div', class_=True):
                    classes = ' '.join(div.get('class', []))
                    if 'content' in classes.lower() and len(div.get_text(strip=True)) > 500:
                        content = div
                        print(f"      Найден контент в div с классом: {classes}")
                        break
            
            # Если все еще не нашли, ищем все параграфы подряд
            if not content:
                main_tag = soup.find('main') or soup.find('article')
                if main_tag:
                    content = main_tag
                    print(f"      Найден контент в main/article")
            
            if content:
                # Собираем параграфы
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
                        print(f"      Собрано {len(text_paragraphs)} параграфов")
                        return text[:2000]
                
                # Если нет параграфов, берем весь текст
                text = content.get_text()
                lines = [line.strip() for line in text.splitlines() if line.strip() and len(line.strip()) > 30]
                if lines:
                    print(f"      Собрано {len(lines)} строк текста")
                    return '\n'.join(lines)[:2000]
            
            print(f"      НЕ НАЙДЕН контент на странице {url}")
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