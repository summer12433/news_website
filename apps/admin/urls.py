# -*- coding: utf-8 -*-
# @Time    : 2020/6/19 17:47
# @Author  : summer
# @File    : urls.py

from django.urls import path
from . import views


app_name = "admin"
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('tags/', views.TagsManageView.as_view(), name='tags'),
    path('tags/<int:tag_id>/', views.TagsManageView.as_view(), name='tags_manage'),

    path('hotnews/', views.HotNewsManageView.as_view(), name='hotnews_manage'),
    path('hotnews/<int:hotnews_id>/', views.HotNewsEditView.as_view(), name='hotnews_edit'),
    path('hotnews/add/', views.HotNewsAddView.as_view(), name='hotnews_add'),
    path('tags/<int:tag_id>/news/', views.NewsByTagIdView.as_view(), name='news_by_tagid'),

    path('news/', views.NewsManageView.as_view(), name='news_manage'),
]



