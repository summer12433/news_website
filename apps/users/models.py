from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager as _UserManager

# Create your models here.


class UserManager(_UserManager):     #调用父类方法重写，创建超级管理员
    """
    define user manager for modifing 'no need email'
    when 'python manager.py createsuperuser '

    """

    def create_superuser(self, username,  password, email=None, **extra_fields):

        #调用super方法重写方法
        super(UserManager, self).create_superuser(username=username, password=password,email=email,**extra_fields)


class User(AbstractUser):   #继承用户模型类
    """
    add mobile email_active fields to Django users models
    """
    objects = UserManager()     #指定管理器

    REQUIRED_FIELDS = ['mobile']     #指定用什么方式注册账户

    mobile = models.CharField(max_length=11, unique=True, verbose_name="手机号码",
                              help_text="手机号码", error_messages={"unique": "此手机号已经被注册"})

    email_active = models.BooleanField(default=False, verbose_name="邮箱验证状态")

    class Meta:
        db_table = "tb_users"      # 指明数据库表名
        verbose_name = "用户"     #后台显示的名字
        verbose_name_plural = verbose_name    #显示复数名称


    def __str__(self):    #打印显示名字，对用户友好
        return self.username


    #关联用户组
    def get_group_name(self):
        group_name_list = (i.name for i in self.groups.all())

        return "|".join(group_name_list)






