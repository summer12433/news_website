# -*- coding: utf-8 -*-
# @Time    : 2020/6/20 16:14
# @Author  : summer
# @File    : main.py

from celery import Celery

# 为celery使用django配置文件进行设置
import os
if not os.getenv('DJANGO_SETTINGS_MODULE'):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'news_website.settings'

# 创建celery应用/实例
app = Celery('sms_codes')

# 导入celery配置
app.config_from_object('celery_tasks.config')

# 自动注册celery任务
app.autodiscover_tasks(['celery_tasks.sms'])