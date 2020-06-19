import json

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import render
from django.views import View
from utils.json_fun import to_json_data
from utils.res_code import Code, error_map
from . import models
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import logging
from haystack.views import SearchView as _SearchView


logger = logging.getLogger("django")
# Create your views here.

# def index(request):
#     return render(request, "news/index.html")



#新闻标签页面,和热门新闻
class IndexView(View):

    def get(self, request):
        tags = models.Tag.objects.only("id", "name").filter(is_delete=False)

        #热门新闻
        hot_news = models.HotNews.objects.select_related("news").\
        only("news__title", "news__image_url", "news__id").\
        filter(is_delete=False).order_by("priority", "-news__clicks")[0:3]

        return render(request, "news/index.html", locals())     #把查出来的数据返回给前台，函数局部变量全部返回


#新闻列表页面
class NewsListView(View):
    """
    1. 获取参数
    2. 效验参数
    3. 数据库拿数据
    4. 分页
    5. 返回给前端
    :param 必传
    tag_id
    page
    """
    def get(self, request):

        try:
            tag_id = int(request.GET.get("tag_id", 0))         #前端获取数据，强转为int类型
        except Exception as e:
            logger.error("标签错误: \n{}".format(e))
            tag_id = 0

        #page
        try:
            page = request.GET.get("page", 1)
        except Exception as e:
            logger.error("当前页数错误: \n{}".format(e))
            page = 1

        #数据库拿取数据
        #select_related,一次性查出news外键关联的对象
        news_queryset = models.News.objects.select_related("tag", "author").\
            only("title", "digest","image_url", "update_time", "tag__name",
                 "author__username")

        news = news_queryset.filter(is_delete=False, tag_id=tag_id) or news_queryset.filter(is_delete=False)

        #分页,第一个参数为分页对象，第二个参数是页面暂时的数据
        paginator = Paginator(news, 10)
        try:
            #page（）  接收一个页码作为参数，返回当前页对象
            news_info = paginator.page(page)
        except EmptyPage:
            logging.info("用户访问的页数大于总页数")
            #num_pages  返回总页数
            news_info = paginator.page(paginator.num_pages)

        #把查询到的数据通过追加方式构建成列表
        news_info_list = []
        for n in news_info:
            news_info_list.append({
                "id": n.id,
                "title": n.title,
                "digest": n.digest,
                "image_url": n.image_url,
                "tag_name": n.tag.name,
                "author": n.author.username,
                "update_time": n.update_time.strftime("%Y年%m月%d日 %H:%M")
            })

        #创建给前端返回的数据
        data = {
            "total_pages": paginator.num_pages,
            "news": news_info_list
        }
        return to_json_data(data=data)


#新闻轮播图功能接口
class NewsBannerView(View):
    """
    url: /news/banners/
    前台不需要传参
    :param
    image_url
    news__id
    news__title
    """
    def get(self, request):
        banners = models.Banner.objects.select_related("news").\
            only("image_url", "news__id", "news__title").\
            filter(is_delete=False)[0:6]

        #定义一个序列化输出
        banners_info_list = []
        for a in banners:
            banners_info_list.append({
                "image_url": a.image_url,
                "news_id": a.news.id,
                "news_title": a.news.title,
            })
        #构建字典给前端传输
        data = {
            "banners": banners_info_list
        }
        return to_json_data(data=data)



#新闻详情页面
class NewsDetailView(View):
    """
    url: /news/<int:news_id>/
    :param
    title
    content
    update_time
    tag__name
    author__username
    """
    def get(self, request, news_id):
        news = models.News.objects.select_related("tag", "author").\
            only("title","content","update_time","tag__name","author__username").\
            filter(is_delete=False, id=news_id).first()

        if news:
            #新闻评论
            comments = models.Comments.objects.select_related("author", "parent").\
                only("content", "author__username", "update_time",
                     "parent__content", "parent__author__username", "parent__update_time").\
                filter(is_delete=False, news_id=news_id)
            #定义列表，序列化
            comment_list = []
            for comm in comments:
                comment_list.append(comm.to_dict_data())

            return render(request, "news/news_detail.html", locals())
        else:
            return HttpResponseNotFound("<h1>Page Not Found</h1>")


#新闻评论
class NewsCommentView(View):
    """
    url: /news/<int: news_id>/comments/
    1. 判断用户是否登录
    2.  获取参数
    3. 效验参数
    4. 保存到数据库
    """
    def post(self, request, news_id):
        if not request.user.is_authenticated:       #判断用户是否登录
            # request.user   #拿到用户
            return to_json_data(errno=Code.SESSIONERR, errmsg=error_map[Code.SESSIONERR])

        if not models.News.objects.only("id").filter(is_delete=False, id=news_id).exists():
            return to_json_data(errno=Code.PARAMERR, errmsg="新闻不存在！")

        #2
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])

        dict_data = json.loads(json_data.decode("utf8"))
        #一级评论
        content = dict_data.get("content")
        if not dict_data.get("content"):
            return to_json_data(errno=Code.PARAMERR, errmsg="评论信息不能为空")

        #回复评论
        parent_id = dict_data.get("parent_id")
        try:
            if parent_id:
                parent_id = int(parent_id)
                if not models.Comments.objects.only('id'). \
                        filter(is_delete=False, id=parent_id, news_id=news_id).exists():
                    return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])

        except Exception as e:
            logging.info("前端传过来的parent_id异常：\n{}".format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg="未知异常")

        # 保存到数据库
        new_content = models.Comments()
        new_content.content = content
        new_content.news_id = news_id
        new_content.author = request.user
        new_content.parent_id = parent_id if parent_id else None
        new_content.save()
        return to_json_data(data=new_content.to_dict_data())



#新闻搜索
class SearchView(_SearchView):
    """
    指定模板文件
    """
    template = 'news/search.html'

    #重写call方法
    def create_response(self):
        kw = self.request.GET.get("q", "")      #定义查询路径q=
        if not kw:
            show_all = True         #没有查询默认显示数据，false不显示
            hot_news = models.HotNews.objects.select_related("news").\
                only("news__title",'news__image_url', 'news__id'). \
                filter(is_delete=False).order_by('priority', '-news__clicks')

            #分页
            paginator = Paginator(hot_news, settings.HAYSTACK_SEARCH_RESULTS_PER_PAGE)
            try:    #获取传入的页码。默认为1
                page = paginator.page(int(self.request.GET.get("page", 1)))
                #假如传的不是整数，返回第一页数据
            except PageNotAnInteger:    #返回第一页数据
                page = paginator.page(1)
            except EmptyPage:
                #获取整页数
                page = paginator.page(paginator.num_pages)

            return render(self.request, self.template, locals())

        else:       #查询有值，展示查询数据
            show_all = False
            qs = super(SearchView, self).create_response()      #复用SearchView
            return qs




