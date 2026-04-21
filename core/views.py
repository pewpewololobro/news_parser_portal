from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import datetime
from .models import Group, Channel, Item
from datetime import datetime, timedelta
import random



def index(request):
    groups = Group.objects.filter(groupchannel__isnull=False).distinct().order_by('sort')
    news_list = Item.objects.select_related('channel').order_by('?')
    
    # Получаем параметр per_page из GET (по умолчанию 20)
    per_page = request.GET.get('per_page', 20)
    try:
        per_page = int(per_page)
        if per_page not in [10, 20, 50, 100]:
            per_page = 20
    except:
        per_page = 20
    
    paginator = Paginator(news_list, per_page)
    page_number = request.GET.get('page', 1)
    news = paginator.get_page(page_number)
    
    # Сохраняем все параметры для пагинации (кроме page)
    params = request.GET.copy()
    if 'page' in params:
        del params['page']
    params_string = params.urlencode()
    
    context = {
        'groups': groups,
        'news': news,
        'per_page': per_page,
        'current_params': params_string,
    }
    
    return render(request, 'core/index.html', context)


def group_news(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    groups = Group.objects.filter(groupchannel__isnull=False).distinct().order_by('sort')
    
    # Получаем все каналы из этой группы
    channels = Channel.objects.filter(groupchannel__group_id=group_id)
    
    # Получаем новости из этих каналов
    news_list = Item.objects.filter(channel__in=channels).select_related('channel').order_by('-pubDate')
    
    # Получаем параметр per_page из GET
    per_page = request.GET.get('per_page', 20)
    try:
        per_page = int(per_page)
        if per_page not in [10, 20, 50, 100]:
            per_page = 20
    except:
        per_page = 20
    
    paginator = Paginator(news_list, per_page)
    page_number = request.GET.get('page', 1)
    news = paginator.get_page(page_number)
    
    # Сохраняем параметры для пагинации
    params = request.GET.copy()
    if 'page' in params:
        del params['page']
    params_string = params.urlencode()
    
    context = {
        'groups': groups,
        'news': news,
        'current_group': group,
        'per_page': per_page,
        'current_params': params_string,
    }
    return render(request, 'core/group_news.html', context)


def channel_news(request, channel_id):
    channel = get_object_or_404(Channel, channel_id=channel_id)
    groups = Group.objects.filter(groupchannel__isnull=False).distinct().order_by('sort')
    
    # Получаем новости только из этого канала
    news_list = Item.objects.filter(channel=channel).select_related('channel').order_by('-pubDate')
    
    # Получаем параметр per_page из GET
    per_page = request.GET.get('per_page', 20)
    try:
        per_page = int(per_page)
        if per_page not in [10, 20, 50, 100]:
            per_page = 20
    except:
        per_page = 20
    
    paginator = Paginator(news_list, per_page)
    page_number = request.GET.get('page', 1)
    news = paginator.get_page(page_number)
    
    # Сохраняем параметры для пагинации
    params = request.GET.copy()
    if 'page' in params:
        del params['page']
    params_string = params.urlencode()
    
    context = {
        'groups': groups,
        'news': news,
        'current_channel': channel,
        'per_page': per_page,
        'current_params': params_string,
    }
    return render(request, 'core/channel_news.html', context)

def search_news(request):
    groups = Group.objects.filter(groupchannel__isnull=False).distinct().order_by('sort')
    query = request.GET.get('q', '')
    date_filter = request.GET.get('date', '')
    
    news_list = Item.objects.select_related('channel')
    
    if query:
        news_list = news_list.filter(Q(title__icontains=query) | Q(description__icontains=query))
    
    if date_filter:
        try:
            # Парсим дату из запроса
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
            
            # Создаем диапазон: от начала дня до конца дня
            start_date = datetime.combine(date_obj, datetime.min.time())
            end_date = datetime.combine(date_obj, datetime.max.time())
            
            # Фильтруем по диапазону
            news_list = news_list.filter(pubDate__range=(start_date, end_date))
            
        except ValueError:
            pass
    
    news_list = news_list.order_by('-pubDate')
    
    # Получаем параметр per_page из GET
    per_page = request.GET.get('per_page', 20)
    try:
        per_page = int(per_page)
        if per_page not in [10, 20, 50, 100]:
            per_page = 20
    except:
        per_page = 20
    
    paginator = Paginator(news_list, per_page)
    page_number = request.GET.get('page', 1)
    news = paginator.get_page(page_number)
    
    # Сохраняем параметры для пагинации (исключая page)
    params = request.GET.copy()
    if 'page' in params:
        del params['page']
    params_string = params.urlencode()
    
    context = {
        'groups': groups,
        'news': news,
        'search_query': query,
        'search_date': date_filter,
        'per_page': per_page,
        'current_params': params_string,
    }
    return render(request, 'core/search_results.html', context)

