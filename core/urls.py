from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('group/<int:group_id>/', views.group_news, name='group_news'),
    path('channel/<int:channel_id>/', views.channel_news, name='channel_news'),
    path('search/', views.search_news, name='search_news'),
]