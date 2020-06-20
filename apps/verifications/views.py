import json
import random

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from utils.json_fun import to_json_data
from utils.res_code import Code, error_map
from users.models import User
from utils.yuntongxun.sms import CCP
from . import constants, forms
# Create your views here.
from django.views import View
from django_redis import get_redis_connection
import logging
from utils.captcha.captcha import captcha
from celery_tasks.sms import tasks as sms_tasks


logger = logging.getLogger("django")        #图形验证码放在日志器输出


#生成uuid的图形验证码
class ImageCode(View):

    def get(self, request, image_code_id):
        text, image = captcha.generate_captcha()  #获取第三方包生成的图片内容

        conn_redis = get_redis_connection('verify_codes')    #get_redis_connection方法获取数据库
        conn_redis.setex('img{}'.format(image_code_id), constants.IMAGE_CODE_REDIS_EXPIRES, text)      #保存图片id，内容和设置过期时间到redis
        logger.info("Image code: {}".format(text))
        return HttpResponse(content=image, content_type='image/jpg')   #指定返回格式


#判断用户是否存在
class CheckUsernameView(View):
    """
    GET usernames/(?<username>\w{5,20})/
    """
    def get(self,request, username):
        count = User.objects.filter(username=username).count()
        data = {
            'username': username,
            'count': count,
        }
        return to_json_data(data=data)         #通过jsonResponse方法把数据传给前台


#判断手机号是否注册
class CheckMobileView(View):
    """
    url: GET  mobile/(?P<mobile>1[3-9]\d{9])/
    """
    def get(self, request, mobile):
        data = {
            'mobile': mobile,
            'count': User.objects.filter(mobile=mobile).count(),
        }
        return to_json_data(data=data)     #自定义一个json方法传给前端


#短信验证码
class SmsCodesView(View):
    """
    1.获取参数
    2.验证参数
    3.发送短信
    4.保存短信验证码
    5.返回给前端
    url: POST/sms_codes/
    - 检查图片验证码是否正确
    - 检查是否60秒有记录
    - 生成短信验证码
    - 保存记录
    - 发送短信
    """
    def post(self, request):
        json_str = request.body     #获取前端数据
        if not json_str:        #判断数据是否为空
            return to_json_data(errno=Code.PARAMERR, errmsg="参数为空，请重新输入")
        #json字符串转字典
        dict_data = json.loads(json_str.decode("utf8"))

        form = forms.CheckImgCodeForm(data=dict_data)      #通过forms获取数据

        #效验参数
        if form.is_valid():
            #获取手机号 mobile
            mobile = form.cleaned_data.get("mobile")
            #创建短信验证码功能
            sms_num = "%06d" % random.randint(0, 999999)
            #将生成的短信验证码内容保存到数据库
            conn_redis = get_redis_connection(alias="verify_codes")
            #创建一个在60秒内是否发送短信的标记
            sms_flag_fmt = "sms_flag + {}".format(mobile).encode("utf8")
            #创建保存短信验证码的标记key有效时间
            sms_text_fmt = "sms_{}".format(mobile).encode("utf8")
            #将数据保存到redis
            p1 = conn_redis.pipeline()      #定义一个redis管道，一次性保存数据
            try:
                p1.setex(sms_flag_fmt, constants.SEND_SMS_CODE_INTERVAL, 1)       #1号为短信模板
                p1.setex(sms_text_fmt, constants.SMS_CODE_REDIS_EXPIRES, sms_num)
                p1.execute()  # 通知redis 执行命令
            except Exception as e:
                logger.debug("redis 执行异常: {}".format(e))
                return to_json_data(errno=Code.UNKOWNERR, errmsg=error_map[Code.UNKOWNERR])

            #发送短信，通知平台
            logger.info("SMS code:{}".format(sms_num))      #把验证码输出在打印台

            #调用celery发送短信
            expires = 5
            sms_tasks.send_sms_code.delay(mobile, sms_num, expires, 1)
            return to_json_data(errno=Code.OK, errmsg="短信验证码发送成功")

            # logger.info("发送短信验证码正常：[mobile:{}, sms_code: {}]".format(mobile, sms_num))
            # return to_json_data(errno=Code.OK, errmsg="短信验证码发送成功")

            # try:
            #     result = CCP().send_template_sms(mobile, [sms_num, 5], 1)
            # except Exception as e:
            #     logger.error("发送短信验证码异常：[mobile:{}, message: {}]".format(mobile, e))
            #     return to_json_data(errno=Code.SMSERROR, errmsg=error_map[Code.SMSERROR])
            #
            # else:
            #     if result == 0:
            #         logger.info("发送短信验证码正常：[mobile:{}, sms_code: {}]".format(mobile, sms_num))
            #         return to_json_data(errno=Code.OK, errmsg="短信验证码发送成功")
            #
            #     else:
            #         logger.warning("发送验证码短信[失败][ mobile: %s ]" % mobile)
            #         return to_json_data(errno=Code.SMSFAIL, errmsg=error_map[Code.SMSFAIL])

        else:
            #定义错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():       #返回元祖
                err_msg_list.append(item[0].get("message"))

            err_msg_str = "/".join(err_msg_list)
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)












