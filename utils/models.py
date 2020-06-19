# -*- coding: utf-8 -*-
# @Time    : 2020/6/15 23:25
# @Author  : summer
# @File    : models.py

from django.db import models


#新闻数据库基类
class ModelBase(models.Model):
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    is_delete = models.BooleanField(default=False, verbose_name="逻辑删除")

    class Meta:
        #抽象类，执行数据库迁移不会创建表,用于其他模型来继承
        abstract = True