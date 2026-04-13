from django.shortcuts import render, get_object_or_404
from .models import Group, Channel, Item
from django.db.models import Q
from datetime import datetime

def index(request):
    groups = Group.objects.filter(groupchannel__isnull=False).distinct().order_by('sort')
    news = Item.objects.select_related('channel').order_by('-pubDate')[:20]
    
    context = {
        'groups': groups,
        'news': news,
    }
    return render(request, 'core/index.html', context)

def group_news(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    groups = Group.objects.filter(groupchannel__isnull=False).distinct().order_by('sort')
    
    # Получаем все каналы из этой группы
    channels = Channel.objects.filter(groupchannel__group_id=group_id)
    
    # Получаем новости из этих каналов
    news = Item.objects.filter(channel__in=channels).select_related('channel').order_by('-pubDate')
    
    context = {
        'groups': groups,
        'news': news,
        'current_group': group,
    }
    return render(request, 'core/group_news.html', context)

def channel_news(request, channel_id):
    channel = get_object_or_404(Channel, channel_id=channel_id)
    groups = Group.objects.filter(groupchannel__isnull=False).distinct().order_by('sort')
    
    # Получаем новости только из этого канала
    news = Item.objects.filter(channel=channel).select_related('channel').order_by('-pubDate')
    
    context = {
        'groups': groups,
        'news': news,
        'current_channel': channel,
    }
    return render(request, 'core/channel_news.html', context)

def search_news(request):
    groups = Group.objects.filter(groupchannel__isnull=False).distinct().order_by('sort')
    query = request.GET.get('q', '')
    date_filter = request.GET.get('date', '')
    
    news = Item.objects.select_related('channel')
    
    if query:
        news = news.filter(Q(title__icontains=query) | Q(description__icontains=query))
    
    if date_filter:
        try:
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
            news = news.filter(pubDate__date=date_obj)
        except ValueError:
            pass
    
    news = news.order_by('-pubDate')
    
    context = {
        'groups': groups,
        'news': news,
        'search_query': query,
        'search_date': date_filter,
    }
    return render(request, 'core/search_results.html', context)