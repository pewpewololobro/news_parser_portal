import time
import sys
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Channel, Item
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
        parser.add_argument(
            '--max-news',
            type=int,
            default=50,
            help='Максимальное количество новостей с канала'
        )
    
    def handle(self, *args, **options):
        channel_id = options.get('channel_id')
        delay = options.get('delay')
        max_news = options.get('max_news')
        
        try:
            if channel_id:
                channels = Channel.objects.filter(channel_id=channel_id)
            else:
                channels = Channel.objects.all()
            
            if not channels.exists():
                self.stdout.write(self.style.WARNING("Нет каналов для парсинга"))
                return
            
            self.stdout.write(self.style.SUCCESS(f"Начинаем парсинг {channels.count()} каналов..."))
            
            total_added = 0
            success_count = 0
            error_count = 0
            
            for channel in channels:
                self.stdout.write(f"\n{'='*60}")
                self.stdout.write(f"Канал: {channel.short_title or channel.title}")
                self.stdout.write(f"URL: {channel.html_desc if channel.html_desc and channel.html_desc != '-' else channel.link}")
                self.stdout.write(f"{'='*60}")
                
                start_time = time.time()
                log = ParsingLog(channel=channel)
                
                try:
                    parser = get_parser(channel)
                    parser_class = parser.__class__.__name__
                    self.stdout.write(f"Используем парсер: {parser_class}")
                    
                    added_count = parser.parse()
                    
                    duration = time.time() - start_time
                    
                    log.items_added = added_count
                    log.duration_seconds = duration
                    log.save()
                    
                    total_added += added_count
                    success_count += 1
                    
                    self.stdout.write(self.style.SUCCESS(
                        f"✓ Добавлено новостей: {added_count} (за {duration:.2f} сек)"
                    ))
                    
                except Exception as e:
                    duration = time.time() - start_time
                    log.error_message = str(e)
                    log.duration_seconds = duration
                    log.save()
                    
                    error_count += 1
                    
                    self.stdout.write(self.style.ERROR(
                        f"✗ Ошибка: {str(e)}"
                    ))
                    import traceback
                    self.stdout.write(traceback.format_exc())
                
                if delay > 0:
                    time.sleep(delay)
            
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(self.style.SUCCESS("ПАРСИНГ ЗАВЕРШЕН"))
            self.stdout.write(f"Всего каналов: {channels.count()}")
            self.stdout.write(f"Успешно: {success_count}")
            self.stdout.write(f"С ошибками: {error_count}")
            self.stdout.write(f"Всего добавлено новостей: {total_added}")
            self.stdout.write(f"{'='*60}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Критическая ошибка: {str(e)}"))
            import traceback
            self.stdout.write(traceback.format_exc())
            sys.exit(1)