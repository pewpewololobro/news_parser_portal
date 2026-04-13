from django.db import models
from django.utils import timezone

class ParsingLog(models.Model):
    channel = models.ForeignKey('core.Channel', on_delete=models.CASCADE, verbose_name="Канал")
    parsed_at = models.DateTimeField(auto_now_add=True, verbose_name="Время парсинга")
    items_found = models.IntegerField(default=0, verbose_name="Найдено новостей")
    items_added = models.IntegerField(default=0, verbose_name="Добавлено новостей")
    error_message = models.TextField(blank=True, verbose_name="Ошибка")
    duration_seconds = models.FloatField(default=0, verbose_name="Длительность (сек)")

    class Meta:
        db_table = 'parsing_logs'
        verbose_name = "Лог парсинга"
        verbose_name_plural = "Логи парсинга"
        ordering = ['-parsed_at']

    def __str__(self):
        return f"{self.channel.short_title} - {self.parsed_at}"