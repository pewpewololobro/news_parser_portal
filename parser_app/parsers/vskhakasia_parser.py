from .base import HTMLParser
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import time

class VskhakasiaParser(HTMLParser):
    """Парсер для сайта vskhakasia.ru/press-centr/news"""
    
    def extract_news_items(self, soup):
        items = []
        
        # Находим все теги article
        articles = soup.find_all('article')
        
        if not articles:
            # Альтернативные селекторы
            articles = soup.select('.news-item, .post, .item, .material, .story')
        
        print(f"  Найдено блоков новостей: {len(articles)}")
        
        for article in articles[:30]:
            # Извлекаем заголовок
            title_elem = article.find(['h2', 'h3', 'h4']) or article.find('a', class_=re.compile(r'title|link', re.I))
            if not title_elem:
                title_elem = article.find('a', href=True)
            
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)
            if not title or len(title) < 10:
                continue
            
            # Извлекаем ссылку
            link_elem = title_elem if title_elem.name == 'a' else title_elem.find('a', href=True)
            if not link_elem:
                continue
            link = urljoin(self.url, link_elem['href'])
            
            # Извлекаем дату
            pub_date = self.extract_date_from_article(article)
            if not pub_date:
                pub_date = self.find_date_in_context(link_elem)
            
            items.append({
                'title': title,
                'link': link,
                'date': pub_date,
                'description': ''  # Будет заполнено при сохранении
            })
        
        # Удаляем дубликаты
        unique_items = {}
        for item in items:
            if item['link'] not in unique_items:
                unique_items[item['link']] = item
        
        print(f"  Уникальных новостей: {len(unique_items)}")
        return list(unique_items.values())
    
    def extract_date_from_article(self, article):
        """Извлекает дату из блока article"""
        # Ищем тег time
        time_elem = article.find('time')
        if time_elem:
            date = time_elem.get('datetime', '') or time_elem.get_text(strip=True)
            if date:
                return date
        
        # Ищем элементы с классами даты
        date_selectors = ['.date', '.time', '.news-date', '.post-date', '.article-date', '.published']
        for selector in date_selectors:
            date_elem = article.select_one(selector)
            if date_elem:
                text = date_elem.get_text(strip=True)
                match = re.search(r'(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})', text)
                if match:
                    return match.group(1)
        
        return ''
    
    def find_date_in_context(self, elem):
        """Ищет дату в родительских элементах"""
        date_patterns = [
            r'(\d{2}\.\d{2}\.\d{4})',
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{2}/\d{2}/\d{4})',
            r'(\d{1,2}\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4})',
        ]
        current = elem
        for _ in range(5):
            if current:
                text = current.get_text()
                for pattern in date_patterns:
                    match = re.search(pattern, text, re.I)
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
            
            # Ищем основной контент статьи
            content = None
            
            # Пробуем разные селекторы
            content_selectors = [
                '.news-text',
                '.article-text', 
                '.post-content',
                '.entry-content',
                'article',
                '.content',
                '.main-content',
                '.text-content',
                '.full-text'
            ]
            
            for selector in content_selectors:
                content = soup.select_one(selector)
                if content and len(content.get_text(strip=True)) > 200:
                    break
            
            if not content:
                # Пробуем найти основной блок с текстом
                main_tag = soup.find('main')
                if not main_tag:
                    main_tag = soup.find('article')
                if not main_tag:
                    main_tag = soup.find('div', class_=re.compile(r'content|text|body', re.I))
                if main_tag:
                    content = main_tag
            
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
                        # Берем первые 2-3 параграфа
                        if len(text_paragraphs) > 3:
                            text = '\n\n'.join(text_paragraphs[:3])
                        else:
                            text = '\n\n'.join(text_paragraphs)
                        return text[:2000]
                
                # Если нет параграфов
                text = content.get_text()
                lines = [line.strip() for line in text.splitlines() if line.strip() and len(line.strip()) > 30]
                text = '\n'.join(lines)
                return text[:2000]
            
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
            
            added_count = 0
            for item in items[:30]:
                title = item.get('title', '')
                link = item.get('link', '')
                pub_date = item.get('date', '')
                
                print(f"  Обрабатываем: {title[:50]}...")
                try:
                    full_text = self.extract_article_text(link)
                    description = full_text[:1000] if full_text else ''
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