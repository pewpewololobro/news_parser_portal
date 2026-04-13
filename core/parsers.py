import re
import logging
from datetime import datetime
from urllib.parse import urljoin

import requests
import feedparser
from bs4 import BeautifulSoup
from django.utils import timezone
from django.db import IntegrityError

from .models import Channel, Item

logger = logging.getLogger(__name__)


class NewsParser:
    """Универсальный парсер новостей для RSS и HTML-сайтов"""

    # Правила парсинга для сайтов без RSS
    HTML_RULES = {
        'adi19.ru': {
            'article_selector': 'div.news-item, div.post, article',
            'title_selector': 'a, h2, h3, .title',
            'link_selector': 'a',
            'date_selector': '.date, time',
        },
        '19rusinfo.ru': {
            'article_selector': '.news-item, .article, .post',
            'title_selector': 'a, .title',
            'link_selector': 'a',
            'date_selector': '.date',
        },
        'mk-hakasia.ru': {
            'article_selector': '.news-item, .article, .material-card',
            'title_selector': '.title a, a.title',
            'link_selector': 'a',
            'date_selector': '.date',
        },
        'vskhakasia.ru': {
            'article_selector': '.news-item, .item, .document-list__item',
            'title_selector': 'a, .title',
            'link_selector': 'a',
            'date_selector': '.date, time',
        },
        'ren.tv': {
            'article_selector': '.tags-feed__item, .news-item',
            'title_selector': '.news-item__title a, .tags-feed__item-title a',
            'link_selector': 'a',
            'date_selector': '.news-item__date, .tags-feed__item-date',
        },
        'r19.ru': {
            'article_selector': '.news-item, .article, .news-list__item',
            'title_selector': 'a, .title',
            'link_selector': 'a',
            'date_selector': '.date, time',
        },
        'abakan.ru': {
            'article_selector': '.news-item, .article, .entry',
            'title_selector': 'a, .title',
            'link_selector': 'a',
            'date_selector': '.date, time',
        },
        'default': {
            'article_selector': 'article, .news-item, .post, .entry, .item, .material-card',
            'title_selector': 'h1, h2, h3, .title, .headline, a',
            'link_selector': 'a',
            'date_selector': 'time, .date, .published, .post-date',
        },
    }

    @classmethod
    def get_rules_for_url(cls, url):
        """Возвращает правила парсинга для данного URL"""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace('www.', '')
        for site_domain, rules in cls.HTML_RULES.items():
            if site_domain in domain:
                return rules
        return cls.HTML_RULES['default']

    @classmethod
    def parse_channel(cls, channel):
        """Главный метод: определяет тип канала и запускает нужный парсер"""
        logger.info(f"Начинаю парсинг: {channel.title} ({channel.link})")
        
        if cls._has_rss(channel.link):
            return cls._parse_rss(channel)
        else:
            return cls._parse_html(channel)

    @staticmethod
    def _has_rss(url):
        """Проверяет, есть ли у сайта RSS-лента"""
        try:
            from feedfinder2 import find_feeds
            feeds = find_feeds(url, check_all=True)
            return len(feeds) > 0
        except Exception:
            return False

    @classmethod
    def _parse_rss(cls, channel):
        """Парсит RSS/Atom ленту"""
        try:
            feed = feedparser.parse(channel.link)
            
            if feed.bozo:
                logger.warning(f"Проблема с RSS {channel.link}: {feed.bozo_exception}")
                return cls._parse_html(channel)

            saved_count = 0
            for entry in feed.entries[:50]:
                # Извлекаем дату
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6])

                # Сохраняем в базу
                try:
                    item, created = Item.objects.get_or_create(
                        link=entry.link,
                        channel=channel,
                        defaults={
                            'title': entry.get('title', 'Без заголовка')[:500],
                            'pubDate': pub_date,
                            'description': (entry.get('description', '') or entry.get('summary', ''))[:5000],
                        }
                    )
                    if created:
                        saved_count += 1
                except IntegrityError:
                    logger.warning(f"Дубликат новости: {entry.link}")
                    continue
            
            return saved_count
            
        except Exception as e:
            logger.error(f"Ошибка парсинга RSS {channel.link}: {e}")
            return 0

    @classmethod
    def _parse_html(cls, channel):
        """Парсит HTML-страницу"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(channel.link, headers=headers, timeout=30)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'

            soup = BeautifulSoup(response.text, 'lxml')
            rules = cls.get_rules_for_url(channel.link)

            articles = soup.select(rules['article_selector'])
            saved_count = 0

            for article in articles[:30]:
                # Извлекаем ссылку
                link_elem = article.select_one(rules['link_selector']) if rules['link_selector'] else article.find('a')
                if not link_elem or not link_elem.get('href'):
                    continue
                
                article_url = urljoin(channel.link, link_elem['href'])
                if not article_url.startswith('http'):
                    continue

                # Извлекаем заголовок
                title_elem = article.select_one(rules['title_selector'])
                title = title_elem.get_text(strip=True) if title_elem else 'Без заголовка'
                if len(title) < 5 and link_elem:
                    title = link_elem.get_text(strip=True)

                # Извлекаем дату
                pub_date = None
                date_elem = article.select_one(rules['date_selector']) if rules.get('date_selector') else None
                if date_elem:
                    pub_date = cls._parse_date(date_elem.get_text(strip=True))

                # Извлекаем описание
                desc_elem = article.select_one('.description, .announce, .short-text, p')
                description = desc_elem.get_text(strip=True)[:5000] if desc_elem else title[:500]

                # Сохраняем
                item, created = Item.objects.get_or_create(
                    link=article_url,
                    channel=channel,
                    defaults={
                        'title': title[:500],
                        'pubDate': pub_date or timezone.now(),
                        'description': description,
                    }
                )
                if created:
                    saved_count += 1

            return saved_count
            
        except Exception as e:
            logger.error(f"Ошибка парсинга HTML {channel.link}: {e}")
            return 0

    @staticmethod
    def _parse_date(date_string):
        """Парсит дату из разных форматов"""
        if not date_string:
            return None

        date_string = re.sub(r'\s+', ' ', date_string.strip())
        
        # Распространённые форматы
        formats = [
            '%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y', '%d %B %Y', '%d %b %Y',
            '%d.%m.%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%d %B %Y %H:%M'
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_string, fmt)
            except:
                continue

        # Обработка русских месяцев
        months_ru = {
            'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
            'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
            'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
        }
        for month_ru, month_num in months_ru.items():
            if month_ru in date_string.lower():
                try:
                    match = re.search(r'(\d{1,2})', date_string)
                    if match:
                        day = int(match.group(1))
                        year_match = re.search(r'(\d{4})', date_string)
                        year = int(year_match.group(1)) if year_match else datetime.now().year
                        return datetime(year, month_num, day)
                except:
                    pass
        
        return None


def parse_all_channels():
    """Парсит все каналы из базы данных"""
    channels = Channel.objects.all()
    results = {}
    
    for channel in channels:
        count = NewsParser.parse_channel(channel)
        results[channel.title] = count
        logger.info(f"Канал '{channel.title}': добавлено {count} новостей")
    
    return results


def parse_single_channel(channel_id):
    """Парсит один конкретный канал"""
    try:
        channel = Channel.objects.get(channel_id=channel_id)
        return NewsParser.parse_channel(channel)
    except Channel.DoesNotExist:
        logger.error(f"Канал с ID {channel_id} не найден")
        return 0