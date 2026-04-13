from django.core.management.base import BaseCommand
from core.parsers import parse_all_channels, parse_single_channel


class Command(BaseCommand):
    help = 'Парсит новости из всех каналов или указанного'

    def add_arguments(self, parser):
        parser.add_argument(
            '--channel-id',
            type=int,
            help='ID канала для парсинга (если не указан, парсятся все)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Подробный вывод'
        )

    def handle(self, *args, **options):
        channel_id = options.get('channel-id')
        verbose = options.get('verbose')
        
        if verbose:
            import logging
            logging.basicConfig(level=logging.INFO)
        
        if channel_id:
            self.stdout.write(f"Парсинг канала ID={channel_id}...")
            count = parse_single_channel(channel_id)
            self.stdout.write(
                self.style.SUCCESS(f"✅ Добавлено новостей: {count}")
            )
        else:
            self.stdout.write("🚀 Начинаю парсинг всех каналов...")
            results = parse_all_channels()
            
            self.stdout.write("\n📊 Результаты парсинга:")
            for channel, count in results.items():
                status = "✅" if count > 0 else "⚠️"
                self.stdout.write(f"  {status} {channel}: {count} новостей")
            
            total = sum(results.values())
            self.stdout.write(
                self.style.SUCCESS(f"\n🎉 Всего добавлено новостей: {total}")
            )