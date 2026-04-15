import os
import sys
import django

# Настройка Django
sys.path.append('C:/Users/GraborenkoNA/Desktop/news_parser_portal')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'news_parser_portal.settings')
django.setup()

from core.models import Channel
from parser_app.parsers.abakan_parser import AbakanParser

# Находим канал абакан.рф
try:
    channel = Channel.objects.get(short_title__icontains='абакан')
    print(f"Найден канал: {channel.short_title}")
    print(f"html_desc: {channel.html_desc}")
    print(f"link: {channel.link}")
    
    # Создаем парсер
    parser = AbakanParser(channel, channel.link)
    
    # Парсим новости
    print("\nНачинаем парсинг...")
    count = parser.parse()
    print(f"\nДобавлено новостей: {count}")
    
    # Проверяем последние новости
    from core.models import Item
    last_items = Item.objects.filter(channel=channel).order_by('-pubDate')[:5]
    print(f"\nПоследние 5 новостей канала:")
    for item in last_items:
        print(f"  - {item.title[:80]}...")
    
except Channel.DoesNotExist:
    print("Канал абакан.рф не найден в базе данных")
    print("\nДоступные каналы:")
    for ch in Channel.objects.all()[:10]:
        print(f"  - {ch.short_title} (id: {ch.channel_id})")