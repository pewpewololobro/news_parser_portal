# core/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Channel, Group, GroupChannel, Item


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ('channel_id', 'short_title', 'title_preview', 'link_preview')
    list_display_links = ('channel_id', 'short_title')
    search_fields = ('title', 'short_title')
    list_filter = ('short_title',)
    ordering = ('channel_id',)
    
    def title_preview(self, obj):
        return obj.title[:80] + '...' if len(obj.title) > 80 else obj.title
    title_preview.short_description = 'Заголовок'
    
    def link_preview(self, obj):
        return format_html('<a href="{}" target="_blank">{}</a>', obj.link, obj.link[:50])
    link_preview.short_description = 'Ссылка'


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'short_title', 'sort', 'hide_content', 'parent')
    list_display_links = ('id', 'name')
    search_fields = ('name', 'short_title')
    list_filter = ('hide_content', 'parent')
    ordering = ('sort',)
    list_editable = ('sort', 'hide_content')


@admin.register(GroupChannel)
class GroupChannelAdmin(admin.ModelAdmin):
    list_display = ('group_link', 'channel_link', 'group', 'channel')
    list_display_links = ('group_link', 'channel_link')
    list_filter = ('group', 'channel')
    search_fields = ('group__name', 'channel__title')
    
    def group_link(self, obj):
        return format_html('<a href="/admin/core/group/{}/change/">{}</a>', 
                          obj.group.id, obj.group.name)
    group_link.short_description = 'Группа'
    
    def channel_link(self, obj):
        return format_html('<a href="/admin/core/channel/{}/change/">{}</a>', 
                          obj.channel.channel_id, obj.channel.short_title)
    channel_link.short_description = 'Канал'


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'title_preview', 'channel', 'pubDate_display')
    list_display_links = ('id', 'title_preview')
    search_fields = ('title', 'description')
    list_filter = ('channel',)
    ordering = ('-id',)  # Сортируем по ID вместо даты
    list_per_page = 50
    
    def title_preview(self, obj):
        return obj.title[:100] + '...' if len(obj.title) > 100 else obj.title
    title_preview.short_description = 'Заголовок'
    
    def pubDate_display(self, obj):
        """Безопасное отображение даты"""
        if obj.pubDate:
            return obj.pubDate.strftime('%Y-%m-%d %H:%M')
        return 'Дата не указана'
    pubDate_display.short_description = 'Дата публикации'
    pubDate_display.admin_order_field = 'pubDate'
    
    def channel_link(self, obj):
        return format_html('<a href="/admin/core/channel/{}/change/">{}</a>', 
                          obj.channel.channel_id, obj.channel.short_title)
    channel_link.short_description = 'Канал'