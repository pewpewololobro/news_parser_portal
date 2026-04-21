from .base import HTMLParser
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

class AbakanParser(HTMLParser):
    """Парсер для сайта абакан.рф (xn--80aaac0ct.xn--p1ai)"""
    
    def __init__(self, channel, url=None):
        super().__init__(channel, url)
        # Отключаем проверку SSL для этого сайта
        self.session.verify = False
    
    def extract_news_items(self, soup):
        items = []
        
        # Находим все теги article
        articles = soup.find_all('article')
        print(f"  Найдено article: {len(articles)}")
        
        for article in articles[:30]:
            # Извлекаем ссылку (она всегда есть в article)
            link_elem = article.find('a', href=True)
            if not link_elem:
                continue
            
            link = link_elem.get('href')
            if not link.startswith('http'):
                link = urljoin('https://xn--80aaac0ct.xn--p1ai', link)
            
            # Извлекаем заголовок - обычно в h2 или h3 внутри ссылки
            title = self.extract_title(article, link_elem)
            if not title or len(title) < 10:
                continue
            
            # Извлекаем дату - ищем в article
            pub_date = self.extract_date(article)
            
            # Извлекаем описание - первый параграф в article
            description = self.extract_description(article)
            
            items.append({
                'title': title,
                'link': link,
                'date': pub_date,
                'description': description
            })
        
        # Удаляем дубликаты по ссылке
        unique_items = {}
        for item in items:
            if item['link'] not in unique_items:
                unique_items[item['link']] = item
        
        print(f"  Уникальных новостей: {len(unique_items)}")
        return list(unique_items.values())
    
    def extract_title(self, article, link_elem):
        """Извлекает заголовок новости"""
        # Сначала пробуем найти заголовок в h2 или h3
        heading = article.find(['h2', 'h3'])
        if heading:
            title = heading.get_text(strip=True)
            if title:
                return self.clean_title(title)
        
        # Если нет, берем текст из ссылки
        title = link_elem.get_text(strip=True)
        return self.clean_title(title)
    
    def extract_date(self, article):
        """Извлекает дату публикации"""
        # Ищем тег time
        time_elem = article.find('time')
        if time_elem:
            # Пробуем получить datetime атрибут
            date = time_elem.get('datetime', '')
            if date:
                return date
            # Или текст
            return time_elem.get_text(strip=True)
        
        # Ищем элементы с классами даты
        date_selectors = ['.date', '.time', '.news-date', '.post-date', '.article-date', '.data']
        for selector in date_selectors:
            date_elem = article.select_one(selector)
            if date_elem:
                return date_elem.get_text(strip=True)
        
        return ''
    
    def extract_description(self, article):
        """Извлекает описание/анонс новости"""
        # Ищем первый параграф в article
        first_p = article.find('p')
        if first_p:
            text = first_p.get_text(strip=True)
            if len(text) > 30:
                return text[:500]
        
        # Ищем элементы с описанием
        desc_selectors = ['.desc', '.description', '.anons', '.preview', '.excerpt', '.summary']
        for selector in desc_selectors:
            desc_elem = article.select_one(selector)
            if desc_elem:
                text = desc_elem.get_text(strip=True)
                if len(text) > 30:
                    return text[:500]
        
        return ''
    
    def clean_title(self, title):
        """Очищает заголовок от лишних символов"""
        # Удаляем лишние пробелы
        title = re.sub(r'\s+', ' ', title)
        # Удаляем цифры в начале (если есть)
        title = re.sub(r'^\d+\s*[.)-]?\s*', '', title)
        return title.strip()
    
    def extract_article_text(self, url, html=None):
        """Извлекает полный текст новости со страницы"""
        try:
            if html is None:
                html = self.fetch_page_content(url)
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Удаляем скрипты и стили
            for element in soup.find_all(['script', 'style', 'noscript', 'iframe', 'nav', 'header', 'footer']):
                element.decompose()
            
            # Ищем основной контент
            content = None
            
            # Пробуем найти контент внутри article на странице новости
            article_tag = soup.find('article')
            if article_tag:
                content = article_tag
            else:
                # Пробуем другие селекторы
                content_selectors = [
                    '.article-content', '.news-content', '.post-content',
                    '.entry-content', '.text-content', '.article-body',
                    '.content', '.main-content'
                ]
                for selector in content_selectors:
                    content = soup.select_one(selector)
                    if content and len(content.get_text(strip=True)) > 200:
                        break
            
            if content:
                # Собираем текст из параграфов
                paragraphs = content.find_all('p')
                if paragraphs:
                    text_paragraphs = []
                    for p in paragraphs:
                        p_text = p.get_text(strip=True)
                        # Фильтруем слишком короткие параграфы и подписи
                        if len(p_text) > 40:
                            text_paragraphs.append(p_text)
                    text = '\n\n'.join(text_paragraphs)
                else:
                    text = content.get_text()
                
                # Очищаем текст
                lines = [line.strip() for line in text.splitlines() if line.strip() and len(line.strip()) > 30]
                text = '\n'.join(lines)
                return text[:10000]
            
            return ''
            
        except Exception as e:
            print(f"  Ошибка извлечения текста: {e}")
            return ''