from django.db import models
from django.utils import timezone

class Channel(models.Model):
    channel_id = models.BigIntegerField(primary_key=True, verbose_name="ID канала")
    title = models.TextField(verbose_name="Заголовок")
    link = models.TextField(verbose_name="Ссылка")
    short_title = models.CharField(max_length=32, default='', verbose_name="Короткий заголовок")
    html_desc = models.TextField(verbose_name="Описание в HTML")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        db_table = 'channels'
        verbose_name = "Канал"
        verbose_name_plural = "Каналы"

    def __str__(self):
        return self.short_title or self.title[:50]


class Group(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, verbose_name="Название")
    sort = models.IntegerField(verbose_name="Порядок сортировки")
    hide_content = models.BooleanField(default=False, verbose_name="Скрыть содержимое")
    short_title = models.CharField(max_length=64, verbose_name="Короткий заголовок")
    html_desc = models.TextField(verbose_name="Описание в HTML")
    parent = models.BigIntegerField(verbose_name="ID родительской группы")

    class Meta:
        db_table = 'groups'
        verbose_name = "Группа"
        verbose_name_plural = "Группы"

    def __str__(self):
        return self.name


class GroupChannel(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, db_column='group_id')
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, db_column='channel_id')

    class Meta:
        db_table = 'group_channels'
        unique_together = (('group', 'channel'),)
        verbose_name = "Связь группы и канала"
        verbose_name_plural = "Связи групп и каналов"


class Item(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.TextField(verbose_name="Заголовок новости")
    link = models.TextField(verbose_name="Ссылка на новость")
    pubDate = models.DateTimeField(null=True, blank=True, verbose_name="Дата публикации")
    description = models.TextField(verbose_name="Текст новости")
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, db_column='channel_id')

    class Meta:
        db_table = 'items'
        verbose_name = "Новость"
        verbose_name_plural = "Новости"
        indexes = [
            models.Index(fields=['pubDate']),
            models.Index(fields=['channel']),
        ]


    def __str__(self):
        return self.title[:100]