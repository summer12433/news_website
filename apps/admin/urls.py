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


]


