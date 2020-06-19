# -*- coding: utf-8 -*-
# @Time    : 2020/6/12 21:56
# @Author  : summer
# @File    : forms.py

from django import forms
from django.core.validators import RegexValidator
from django_redis import get_redis_connection
from users.models import User


#创建手机号正则效验器
mobile_validator = RegexValidator(r'^1[3-9]\d{9}$', "手机号格式错误")



#前端表单效验
class CheckImgCodeForm(forms.Form):
    mobile = forms.CharField(max_length=11, min_length=11, validators=[mobile_validator],
                             error_messages={"min_length": "手机号长度有误",
                                             "max_length": "手机号长度有误",
                                             "required": "手机号不能为空"})
    image_code_id = forms.UUIDField(error_messages={"required": "图片UUid不能为空"})
    text = forms.CharField(max_length=4, min_length=4,
                           error_messages={"max_length": "图片验证码长度有误",
                                           "min_length": "图片验证码长度有误",
                                           "required": "图片验证码不能为空"})

    def clean(self):        #clean方法进行效验
        cleaned_data = super().clean()    #继承clean方法
        mobile_num = cleaned_data.get("mobile")
        image_uuid = cleaned_data.get("image_code_id")
        image_text = cleaned_data.get("text")

        if User.objects.filter(mobile=mobile_num).count():
            raise forms.ValidationError("手机号已注册，请重新输入")

         #获取图片验证码,从redis拿出来
        try:
            conn_redis = get_redis_connection(alias="verify_codes")      #alias 指定数据库
        except Exception as e:
            raise forms.ValidationError("未知错误")
        img_key = "img{}".format(image_uuid).encode("utf8")
        real_image_code_origin = conn_redis.get(img_key)     #获取redis数据，b'' 类型


        real_image_code = real_image_code_origin.decode("utf8") if real_image_code_origin else None    #判断数据是否为空
        conn_redis.delete(img_key)  # 获取完成就删除redis图片验证码

        #判断用户输入的图片验证码和数据库里面取得是否一致
        if (not real_image_code) or image_text.upper()  != real_image_code:     #为空抛出异常，不为空就比对
            raise forms.ValidationError("图片验证码验证失败")

        #判断60秒内是否有记录
        sms_flag_fmt = "sms_flag_{}".format(mobile_num).encode("utf8")        #手机号码编码成字节类型
        sms_flg = conn_redis.get(sms_flag_fmt)     #redis获取编码后的手机号码

        if sms_flg:         #如果数据存在就抛错
            raise forms.ValidationError("获取短信验证码过于频繁")

