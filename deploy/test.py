# -*- coding: utf-8 -*-
# @Time    : 2020/6/23 23:17
# @Author  : summer
# @File    : test.py

def application(env, start_response):
    start_response('200 OK', [('Content-Type','text/html')])
    return [b"Hello World"] # python3