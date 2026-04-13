import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Channel
from parser_app.models import ParsingLog
from parser_app.parsers import get_parser

class Command(BaseCommand):
    help = 'Парсинг новостей из всех каналов'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--channel-id',
            type=int,
            help='ID канала для парсинга (если не указан, парсятся все)'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1,
            help='Задержка между запросами (секунды)'
        )
    
    def handle(self, *args, **options):
        channel_id = options.get('channel_id')
        delay = options.get('delay')
        
        # Проверяем, что модели созданы
        try:
            if channel_id:
                channels = Channel.objects.filter(channel_id=channel_id)
            else:
                channels = Channel.objects.all()
            
            if not channels.exists():
                self.stdout.write(self.style.WARNING("Нет каналов для парсинга"))
                return
            
            self.stdout.write(f"Начинаем парсинг {channels.count()} каналов...")
            
            for channel in channels:
                self.stdout.write(f"\nПарсинг канала: {channel.short_title or channel.title}")
                self.stdout.write(f"URL: {channel.html_desc}")
                url_for_parsing = channel.html_desc if channel.html_desc and channel.html_desc != '-' else channel.link
                self.stdout.write(f"URL для парсинга: {url_for_parsing}")
                
                start_time = time.time()
                log = ParsingLog(channel=channel)
                
                try:
                    # Получаем подходящий парсер
                    parser = get_parser(channel)
                    
                    # Парсим новости
                    added_count = parser.parse()
                    
                    duration = time.time() - start_time
                    
                    log.items_added = added_count
                    log.duration_seconds = duration
                    log.save()
                    
                    self.stdout.write(self.style.SUCCESS(
                        f"✓ Добавлено новостей: {added_count} (за {duration:.2f} сек)"
                    ))
                    
                except Exception as e:
                    duration = time.time() - start_time
                    log.error_message = str(e)
                    log.duration_seconds = duration
                    log.save()
                    
                    self.stdout.write(self.style.ERROR(
                        f"✗ Ошибка: {str(e)}"
                    ))
                
                # Задержка между запросами
                time.sleep(delay)
            
            self.stdout.write(self.style.SUCCESS("\nПарсинг завершен!"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Критическая ошибка: {str(e)}"))
