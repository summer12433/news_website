from django.db import models
from utils.models import ModelBase
import pytz
# Create your models here.


#文章分类表
class Tag(ModelBase):
    name = models.CharField(max_length=60, verbose_name="标签名", help_text="标签名")

    class Meta:
        ordering = ["-update_time", "-id"]      #逆序排序
        db_table = "tb_tag"
        verbose_name = "新闻标签"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


#新闻表
class News(ModelBase):
    title = models.CharField(max_length=150, verbose_name="标题", help_text="标题")
    digest = models.CharField(max_length=200, verbose_name="摘要", help_text="摘要")
    content = models.TextField(verbose_name="内容", help_text="内容")
    clicks = models.IntegerField(default=0, verbose_name="点击量", help_text="点击量")
    image_url = models.URLField(default="", verbose_name="图片url", help_text="图片url")
    tag = models.ForeignKey("Tag", on_delete=models.SET_NULL, null=True)
    author = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ["-update_time", "-id"]
        db_table = "tb_news"  # 指明数据库表名
        verbose_name = "新闻"  # 在admin站点中显示的名称
        verbose_name_plural = verbose_name  # 显示的复数名称

    def __str__(self):
        return self.title


#新闻评论表
class Comments(ModelBase):
    """
    """
    content = models.TextField(verbose_name="内容", help_text="内容")

    author = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    news = models.ForeignKey('News', on_delete=models.CASCADE)
    parent = models.ForeignKey("self", on_delete=models.CASCADE,null=True, blank=True)  #self实例关联自己的，子评论可以为空，blank允许输入为空


    class Meta:
        ordering = ['-update_time', '-id']
        db_table = "tb_comments"  # 指明数据库表名
        verbose_name = "评论"  # 在admin站点中显示的名称
        verbose_name_plural = verbose_name  # 显示的复数名称

    #content update_time author__username parent__content parent__author__username
    #parent__update_time
    def to_dict_data(self):  #子评论信息展示

        #修改时间成上海时区
        asia_shanghai = pytz.timezone("Asia/Shanghai")
        update_time_local = asia_shanghai.normalize(self.update_time)

        comment_dict = {
            "news_id": self.news_id,
            "content_id": self.id,
            "content": self.content,
            "author": self.author.username,
            "update_time": update_time_local.strftime("%Y年%m月%d日 %H:%M"),
            "parent": self.parent.to_dict_data() if self.parent else None,
        }
        return comment_dict

    def __str__(self):
        return '<评论{}>'.format(self.id)


#热门新闻表
class HotNews(ModelBase):
    """
    """
    PRI_CHOICES = [             #优先级默认值
        (1, "第一级"),
        (2, "第二级"),
        (3, "第三级"),
    ]
    news = models.OneToOneField('News', on_delete=models.CASCADE)
    priority = models.IntegerField(choices=PRI_CHOICES, verbose_name="优先级", help_text="优先级")

    class Meta:
        ordering = ['-update_time', '-id']
        db_table = "tb_hotnews"  # 指明数据库表名
        verbose_name = "热门新闻"  # 在admin站点中显示的名称
        verbose_name_plural = verbose_name  # 显示的复数名称

    def __str__(self):
        return '<热门新闻{}>'.format(self.id)


#轮播图表
class Banner(ModelBase):
    """
    """
    PRI_CHOICES = [  # 优先级默认值
        (1, "第一级"),
        (2, "第二级"),
        (3, "第三级"),
        (4, "第四级"),
        (5, "第五级"),
        (6, "第六级"),
    ]
    image_url = models.URLField(verbose_name="轮播图url", help_text="轮播图url")
    priority = models.IntegerField(choices=PRI_CHOICES, default=6, verbose_name="优先级", help_text="优先级")
    news = models.OneToOneField('News', on_delete=models.CASCADE)

    class Meta:
        ordering = ['priority', '-update_time', '-id']
        db_table = "tb_banner"  # 指明数据库表名
        verbose_name = "轮播图"  # 在admin站点中显示的名称
        verbose_name_plural = verbose_name  # 显示的复数名称

    def __str__(self):
        return '<轮播图{}>'.format(self.id)


