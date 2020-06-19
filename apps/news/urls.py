# -*- coding: utf-8 -*-
# @Time    : 2020/6/11 23:14
# @Author  : summer
# @File    : urls.py

from django.urls import path
from . import views


app_name = 'news'
urlpatterns = [
    # path('', views.index, name='index'),
    path('', views.IndexView.as_view(), name='index'),
    path('news/', views.NewsListView.as_view(), name='news_list'),
    path('news/banners/', views.NewsBannerView.as_view(), name='news_banner'),
    path('news/<int:news_id>/', views.NewsDetailView.as_view(), name='news_detail'),
    path('news/<int:news_id>/comments/', views.NewsCommentView.as_view(), name='news_comment'),
    path('search/', views.SearchView(), name='search'),
]