# -*- coding: utf-8 -*-
# @Time    : 2020/6/19 16:07
# @Author  : summer
# @File    : urls.py
from django.urls import path
from . import views



app_name = "course"
urlpatterns = [
    path('', views.course_list, name='index'),
    path('<int:course_id>/', views.CourseDetailView.as_view(), name='course_detail'),

]