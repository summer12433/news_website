# -*- coding: utf-8 -*-
# @Time    : 2020/6/13 23:10
# @Author  : summer
# @File    : forms.py
import re
from django import forms
from django.contrib.auth import login
from django.db.models import Q
from django_redis import get_redis_connection
from users.models import User
from . import constants




#效验用户登录表单
class RegisterForm(forms.Form):
    username = forms.CharField(label="用户名", max_length=20, min_length=5,
                               error_messages={"max_length": "用户名长度不能大于20",
                                               "min_length": "用户名长度不能小于5",
                                               "required": "用户名不能为空"})
    password = forms.CharField(label="密码", max_length=20, min_length=6,
                               error_messages={"max_length": "密码长度不能大于20",
                                               "min_length": "密码长度不能小于6",
                                               "required": "密码不能为空"})
    password_repeat = forms.CharField(label="确认密码", max_length=20, min_length=6,
                               error_messages={"max_length": "密码长度不能大于20",
                                               "min_length": "密码长度不能小于5",
                                               "required": "密码不能为空"})
    mobile = forms.CharField(label="手机号", max_length=11, min_length=11,
                                      error_messages={"max_length": "手机号码不能大于11",
                                                      "min_length": "手机号码不能小于11",
                                                      "required": "手机号不能为空"})
    sms_code = forms.CharField(label="短信验证码", max_length=6, min_length=6,
                                      error_messages={"max_length": "短信验证码长度有误",
                                                      "min_length": "短信验证码长度有误",
                                                      "required": "短信验证码不能为空"})


    def clean_username(self):   #判断用户名
        uname = self.cleaned_data.get("username")
        if User.objects.filter(username=uname).exists():
            raise forms.ValidationError("用户名已注册，请重新输入")
        return uname

    def clean_mobile(self):     #判断手机号
        tel = self.cleaned_data.get("mobile")
        if not re.match(r'^1[3-9]\d{9}$',tel):      #re匹配手机号码
            raise forms.ValidationError("手机号码格式有误")
        if User.objects.filter(mobile=tel).exists():
            raise forms.ValidationError("手机号已经注册，请重新输入")
        return tel



    def clean(self):        #进行表单判断
        cleaned_data = super().clean()
        passwd = cleaned_data.get("password")
        passwd_repeat = cleaned_data.get("password_repeat")

        #密码判断
        if passwd != passwd_repeat:
            raise forms.ValidationError("两次输入的密码不一致")

        tel = cleaned_data.get("mobile")
        sms_text = cleaned_data.get("sms_code")

        #判断短信验证码是否正确
        redis_conn = get_redis_connection("verify_codes")     #连接数据库
        sms_fmt = "sms_{}".format(tel).encode("utf8")
        real_sms = redis_conn.get(sms_fmt)
        if (not real_sms) or (sms_text != real_sms.decode("utf8")):
            raise forms.ValidationError("短信验证码错误")


#登录效验表单
class LoginForm(forms.Form):
    """
    mobile
    username
    password
    remember me
    """
    user_account = forms.CharField()      #可能是手机号或者用户名，不指定
    password = forms.CharField(label="密码", max_length=20, min_length=6,
                               error_messages={"max_length": "密码长度不能大于20",
                                               "min_length": "密码长度不能小于6",
                                               "required": "密码不能为空"})
    remember_me = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):        #重写实例化对象
        self.request = kwargs.pop('request', None)
        super(LoginForm,self).__init__(*args, **kwargs)

    def clean_user_user_account(self):
        user_info = self.cleaned_data.get("user_account")

        if not user_info:
            raise forms.ValidationError("用户名不能为空")

        #and 条件都需要满足
        if not re.match(r'^1[3-9]\d{9}$', user_info) and (len(user_info)<5 or len(user_info)>20):
            raise forms.ValidationError("格式不正确，请重新输入")

        return user_info


    def clean(self):
        cleaned_data = super().clean()
        user_info = cleaned_data.get("user_account")
        passwd = cleaned_data.get("password")
        hold_login = cleaned_data.get("remember_me")

        #查询数据库
        user_queryset = User.objects.filter(Q(mobile=user_info) | Q(username=user_info))
        if user_queryset:
            user = user_queryset.first()
            if user.check_password(passwd):        #check_password验证密码，返回bool值
                if hold_login:      #如果有勾选，设置session时间
                    self.request.session.set_expiry(constants.USER_SESSION_EXPIRES)
                else:
                    self.request.session.set_expiry(0)
                login(self.request, user)       #记住登录状态
            else:
                raise forms.ValidationError("密码错误，请重新输入")
        else:
            raise forms.ValidationError("用户不存在，请重新输入")


