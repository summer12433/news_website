import json


from django.contrib.auth import login, logout
from django.shortcuts import render, redirect, reverse
# Create your views here.
from django.views import View
from utils.json_fun import to_json_data
from utils.res_code import Code
from . import forms
from .forms import RegisterForm, LoginForm
from .models import User

#用户注册
class RegisterView(View):
    """
    url: /users/register/
    """
    def get(self,request):
        return render(request, 'users/register.html')

    def post(self, request):
        """
        1. 获取参数
        2. 效验参数
        3. 效验好的数据存入数据库
        4. 给用户提示
        :param request:
        :return:
        """
        # 1
        json_data = request.body    #获取前端数据
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg="参数为空，请从新输入")
        dict_data = json.loads(json_data.decode("utf8"))    #数据转换成字典格式

        # 2
        form = RegisterForm(data=dict_data)     #连接表单效验
        if form.is_valid():     #表单效验。返回true  False
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            mobile = form.cleaned_data.get("mobile")

        # 3
            user = User.objects.create_user(username=username, password=password,mobile=mobile)
            login(request,user)     #记住用户的登录状态

            return to_json_data("恭喜您。注册成功")

        else:
            #定义错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():       #返回元祖
                err_msg_list.append(item[0].get("message"))

            err_msg_str = "/".join(err_msg_list)
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)



#用户登录
class LoginView(View):
    """
    url: /users/login/
    """
    def get(self, request):
        return render(request, "users/login.html")

    def post(self, request):
        #获取参数
        json_data = request.body

        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg="参数为空，请从新输入")

        dict_data = json.loads(json_data.decode("utf8"))

        #参数效验
        form = LoginForm(data=dict_data, request=request)
        if form.is_valid():
            return to_json_data(errmsg="登陆成功")

        else:
            #定义错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():       #返回元祖
                err_msg_list.append(item[0].get("message"))

            err_msg_str = "/".join(err_msg_list)
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)



#用户退出
class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect(reverse("users:login"))






