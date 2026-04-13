# core/admin.py
from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.html import format_html
from .models import Channel, Group, GroupChannel, Item
from .parsers import parse_single_channel  # Добавляем импорт парсера


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ('channel_id', 'short_title', 'title_preview', 'link_preview', 'parse_button')
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
    
    def parse_button(self, obj):
        """Кнопка для запуска парсинга канала"""
        return format_html(
            '<a class="button" href="{}" style="background: #28a745; color: white; padding: 5px 10px; '
            'text-decoration: none; border-radius: 3px; font-weight: bold;">🔄 Парсить сейчас</a>',
            f'parse/{obj.channel_id}/'
        )
    parse_button.short_description = 'Парсинг'
    parse_button.allow_tags = True
    
    def get_urls(self):
        """Добавляем кастомный URL для парсинга"""
        urls = super().get_urls()
        custom_urls = [
            path('parse/<int:channel_id>/', self.admin_site.admin_view(self.parse_channel), name='parse_channel'),
        ]
        return custom_urls + urls
    
    def parse_channel(self, request, channel_id):
        """Запускает парсинг канала"""
        if not request.user.is_staff:
            messages.error(request, 'У вас нет прав для выполнения этого действия')
            return redirect('admin:core_channel_changelist')
        
        try:
            count = parse_single_channel(channel_id)
            if count > 0:
                messages.success(request, f'✅ Парсинг завершён! Добавлено {count} новостей.')
            else:
                messages.warning(request, f'⚠️ Парсинг завершён, но новых новостей не найдено.')
        except Exception as e:
            messages.error(request, f'❌ Ошибка при парсинге: {str(e)}')
        
        return redirect('admin:core_channel_changelist')


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
    ordering = ('-id',)
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