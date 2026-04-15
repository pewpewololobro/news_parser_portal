from .base import HTMLParser
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

class Adi19Parser(HTMLParser):
    """Парсер для сайта Агентство деловой информации (adi19.ru)"""
    
    def extract_news_items(self, soup):
        items = []
        
        # Находим контейнер со списком новостей (обычно основная часть страницы)
        # Это поможет исключить подвал и боковые колонки
        main_content = soup.find('main') or soup.find('div', class_=re.compile(r'content|main', re.I))
        
        if main_content:
            search_area = main_content
        else:
            # Если не нашли основной контент, ищем по всей странице
            search_area = soup
        
        # Ищем все ссылки в области контента
        all_links = search_area.find_all('a', href=True)
        
        # Список слов, по которым исключаем ссылки (служебные)
        exclude_keywords = [
            # Политика и правила
            'политик', 'конфиденциальн', 'cookie', 'файл', 
            'правила', 'условия', 'terms', 'privacy',
            # Навигация
            'следующ', 'предыдущ', 'далее', 'назад', 'вперед',
            'все новости', 'читать', 'подробнее', 'показать',
            # Авторизация и соцсети
            'регистрац', 'войти', 'вход', 'logout', 'выйти',
            'facebook', 'twitter', 'vk', 'telegram', 'instagram', 'youtube',
            'whatsapp', 'viber', 'ok', 'odnoklassniki',
            # Подвал и разработка
            'разработка', 'magneex', 'magneex.com', 'создание', 'студия',
            'дизайн', 'хостинг', 'поддержка', 'контакты',
            # RSS и подписка
            'rss', 'feed', 'подписаться', 'subscribe',
            # Реклама
            'реклам', 'advert', 'advertisement',
        ]
        
        # Паттерны для проверки URL (исключаем служебные страницы)
        exclude_url_patterns = [
            '/policy', '/privacy', '/terms', '/cookie', '/rules',
            '/about', '/contacts', '/feedback', '/advertising',
            '/sitemap', '/search', '/user', '/login', '/register'
        ]
        
        for link in all_links[:100]:
            title = link.get_text(strip=True)
            
            # Пропускаем пустые или слишком короткие ссылки
            if not title or len(title) < 15:
                continue
            
            # Пропускаем слишком длинные (обычно не заголовки)
            if len(title) > 300:
                continue
            
            # Проверяем на служебные ключевые слова
            is_excluded = False
            title_lower = title.lower()
            for keyword in exclude_keywords:
                if keyword.lower() in title_lower:
                    is_excluded = True
                    break
            
            if is_excluded:
                continue
            
            # Проверяем URL ссылки на служебные признаки
            href = link.get('href', '').lower()
            
            # Исключаем по паттернам URL
            if any(pattern in href for pattern in exclude_url_patterns):
                continue
            
            # Проверяем внешние ссылки (обычно не новости)
            if href.startswith(('http://', 'https://')):
                # Если ссылка ведет на другой домен, исключаем
                if 'adi19.ru' not in href:
                    continue
            
            # Проверяем, что ссылка ведет на статью
            if not re.search(r'/news/|/\d{4}/\d{2}/\d{2}/|/story/|/article/', href):
                date_found = self.find_date_in_context(link)
                if not date_found:
                    continue
            
            link_url = urljoin(self.url, link['href'])
            
            # Ищем дату рядом со ссылкой
            pub_date = self.find_date_in_context(link)
            
            # Если дата не найдена, пропускаем
            if not pub_date:
                continue
            
            items.append({
                'title': title,
                'link': link_url,
                'date': pub_date,
                'description': ''
            })
        
        # Удаляем дубликаты по ссылке
        unique_items = {}
        for item in items:
            if item['link'] not in unique_items:
                unique_items[item['link']] = item
        
        print(f"  Найдено уникальных новостей: {len(unique_items)}")
        return list(unique_items.values())
    
    def find_date_in_context(self, link_elem):
        """Ищет дату в родительских элементах ссылки"""
        date_patterns = [
            r'(\d{2}\.\d{2}\.\d{4})',  # 15.04.2026
            r'(\d{4}-\d{2}-\d{2})',      # 2026-04-15
            r'(\d{2}/\d{2}/\d{4})',      # 15/04/2026
            r'(\d{1,2}\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4})',  # 15 апреля 2026
        ]
        
        # Проверяем текущий элемент и до 4 родителей
        current = link_elem
        for _ in range(5):
            if current:
                parent_text = current.get_text()
                for pattern in date_patterns:
                    match = re.search(pattern, parent_text, re.I)
                    if match:
                        return match.group(1)
                current = current.parent
            else:
                break
        
        return ''
    
    def extract_article_text(self, url, html=None):
        """Извлекает полный текст новости со страницы статьи"""
        try:
            if html is None:
                html = self.fetch_page_content(url)
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Удаляем скрипты, стили и навигацию
            for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()
            
            # Ищем основной контент
            content = None
            content_selectors = [
                '.news-text',
                '.article-text',
                '.post-content',
                '.entry-content',
                'article',
                '.content',
                '.main-content'
            ]
            
            for selector in content_selectors:
                content = soup.select_one(selector)
                if content and len(content.get_text(strip=True)) > 200:
                    break
            
            if not content:
                # Если не нашли по селекторам, ищем все параграфы подряд
                main_tag = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|text', re.I))
                if main_tag:
                    content = main_tag
            
            if content:
                # Собираем все параграфы
                paragraphs = content.find_all('p')
                if paragraphs:
                    text_paragraphs = []
                    for p in paragraphs:
                        p_text = p.get_text(strip=True)
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
            print(f"  Ошибка извлечения текста статьи: {e}")
            return ''