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
    path('news/<int:news_id>/',views.NewsEditView.as_view(), name='news_edit'),
    path('news/images/', views.NewsUploadImage.as_view(), name='upload_image'),
    path('token/', views.UploadToken.as_view(), name='upload_token'),
    path('markdown/iamges/', views.MarkDownUploadImage.as_view(), name='markdown_image_upload'),
    path('news/pub/', views.NewsPubView.as_view(), name='news_pub'),

    path('banners/', views.BannerManageView.as_view(), name='banner_manage'),
    path('banners/<int:banner_id>/', views.BannerEditView.as_view(), name='banner_edit'),
    path('banners/add/', views.BannerAddView.as_view(), name='banner_add'),

    path('docs/', views.DocManageView.as_view(), name='doc_manage'),
    path('docs/<int:doc_id>/', views.DocEditView.as_view(), name='doc_edit'),
    path('docs/files/', views.DocUploadFile.as_view(), name='upload_text'),
    path('docs/pub/', views.DocsPubView.as_view(), name='docs_pub'),

    path('courses/', views.CoursesManageView.as_view(), name='course_manage'),
    path('courses/<int:course_id>/', views.CourseEditView.as_view(), name='course_edit'),
    path('courses/pub/', views.CoursePubView.as_view(), name='course_pub'),

    path('groups/', views.GroupsManageView.as_view(), name='groups_manage'),
    path('groups/<int:group_id>/', views.GroupsEditView.as_view(), name='groups_edit'),
    path('groups/add/', views.GroupsAddView.as_view(), name='groups_add'),

    path('users/', views.UsersManageView.as_view(), name='users_manage'),
    path('users/<int:user_id>/', views.UsersEditView.as_view(), name='users_edit'),
]



