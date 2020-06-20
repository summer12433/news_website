import json
from datetime import datetime
from urllib.parse import urlencode

from django.core.paginator import Paginator, EmptyPage
from django.db.models import Count
from django.shortcuts import render
from news import models
# Create your views here.
from django.views import View

from utils import page_script
from utils.json_fun import to_json_data
from utils.res_code import Code, error_map
import logging
from collections import OrderedDict


logger = logging.getLogger("django")



#admin后台首页面
class IndexView(View):
    def get(self, request):
        return render(request, "admin/index/index.html")


#新闻标签修改
class TagsManageView(View):
    #标签展示
    def get(self, request):
        tags = models.Tag.objects.values("id", "name").annotate(num_news=Count("news")).\
            filter(is_delete=False).order_by("-num_news")
        return render(request, "admin/news/tags_manage.html", locals())

    #标签添加
    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        #数据解码
        dict_data = json.loads(json_data.decode("utf8"))
        #字典取值
        tag_name = dict_data.get("name")

        if tag_name and tag_name.strip():
            tag_tuple = models.Tag.objects.get_or_create(name=tag_name)
            if tag_tuple[-1]:
                return to_json_data(errmsg="标签创建成功")
            else:
                return to_json_data(errno=Code.DATAEXIST, errmsg="标签名已存在")
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg="标签名为空")

    #标签编辑
    def put(self, request, tag_id):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])

        #解码
        dict_data = json.loads(json_data.decode("utf8"))
        tag_name = dict_data.get("name")
        #数据库取数据
        tag = models.Tag.objects.only("id").filter(id=tag_id).first()
        if tag:
            if tag_name and tag_name.strip():
                if not models.Tag.objects.only("id").filter(name=tag_name).exists():
                    tag.name = tag_name
                    #保存到数据库并标记
                    tag.save(update_fields=["name"])
                    return to_json_data(errmsg='标签更新成功')
                else:
                    return to_json_data(errno=Code.DATAEXIST, errmsg='标签名已存在')
            else:
                return to_json_data(errno=Code.PARAMERR, errmsg='标签名为空')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要更新的标签不存在')


    #删除标签
    def delete(self, request, tag_id):
        tag = models.Tag.objects.only('id').filter(id=tag_id).first()
        if tag:
            tag.delete()
            return to_json_data(errmsg="标签更新成功")
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg="需要删除的标签不存在")



#热门新闻管理
class HotNewsManageView(View):
    """
    id title tag_name priority
    """
    def get(self, request):
        hot_news = models.HotNews.objects.select_related('news__tag'). \
                       only('news_id', 'news__title', 'news__tag__name', 'priority'). \
                       filter(is_delete=False).order_by('priority', '-news__clicks')[0:3]

        return render(request, 'admin/news/news_hot.html', locals())


#热门新闻编辑
class HotNewsEditView( View):

    #删除
    def delete(self, request, hotnews_id):
        hotnews = models.HotNews.objects.only('id').filter(id=hotnews_id).first()
        if hotnews:
            hotnews.is_delete = True
            hotnews.save(update_fields=['is_delete'])
            return to_json_data(errmsg="热门文章删除成功")
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg="需要删除的热门文章不存在")

    #更新
    def put(self, request, hotnews_id):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))

        try:
            priority = int(dict_data.get('priority'))
            priority_list = [i for i, _ in models.HotNews.PRI_CHOICES]
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='热门文章的优先级设置错误')
        except Exception as e:
            logger.info('热门文章优先级异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='热门文章的优先级设置错误')

        hotnews = models.HotNews.objects.only('id').filter(id=hotnews_id).first()
        if not hotnews:
            return to_json_data(errno=Code.PARAMERR, errmsg="需要更新的热门文章不存在")

        if hotnews.priority == priority:
            return to_json_data(errno=Code.PARAMERR, errmsg="热门文章的优先级未改变")

        hotnews.priority = priority
        hotnews.save(update_fields=['priority'])
        return to_json_data(errmsg="热门文章更新成功")



#热门新闻添加
class HotNewsAddView(View):
    """
    分组查询 id  name   每条标签对应的新闻数量
    url: /admin/hotnews/add/
    """
    def get(self, request):
        tags = models.Tag.objects.values("id", "name").annotate(num_news=Count("news")).\
            filter(is_delete=False).order_by("-num_news", "update_time")

        # 优先级列表
        # priority_list = {K: v for k, v in models.HotNews.PRI_CHOICES}
        priority_dict = OrderedDict(models.HotNews.PRI_CHOICES)

        return render(request, 'admin/news/news_hot_add.html', locals())

    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))

        try:
            news_id = int(dict_data.get('news_id'))
        except Exception as e:
            logger.info('前端传过来的文章id参数异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')

        if not models.News.objects.filter(id=news_id).exists():
            return to_json_data(errno=Code.PARAMERR, errmsg='文章不存在')

        try:
            priority = int(dict_data.get('priority'))
            priority_list = [i for i, _ in models.HotNews.PRI_CHOICES]
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='热门文章的优先级设置错误')
        except Exception as e:
            logger.info('热门文章优先级异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='热门文章的优先级设置错误')

        # 创建热门新闻
        hotnews_tuple = models.HotNews.objects.get_or_create(news_id=news_id)
        hotnews, is_created = hotnews_tuple
        hotnews.priority = priority  # 修改优先级
        hotnews.save(update_fields=['priority'])
        return to_json_data(errmsg="热门文章创建成功")


#热门新闻标签
class NewsByTagIdView(View):

    def get(self, request, tag_id):
        newses = models.News.objects.values('id', 'title').filter(is_delete=False, tag_id=tag_id)
        news_list = [i for i in newses]

        return to_json_data(data={
            'news': news_list
        })


#新闻文章管理
class NewsManageView(View):
    """
    """
    def get(self, request):
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
        newses = models.News.objects.only('id', 'title', 'author__username', 'tag__name', 'update_time').\
            select_related('author', 'tag').filter(is_delete=False)

        # 通过时间进行过滤
        try:
            start_time = request.GET.get('start_time', '')
            start_time = datetime.strptime(start_time, '%Y/%m/%d') if start_time else ''

            end_time = request.GET.get('end_time', '')
            end_time = datetime.strptime(end_time, '%Y/%m/%d') if end_time else ''
        except Exception as e:
            logger.info("用户输入的时间有误：\n{}".format(e))
            start_time = end_time = ''
        #判断输入的时间是否在起始时间以内
        if start_time and not end_time:
            newses = newses.filter(update_time__lte=start_time)
        if end_time and not start_time:
            newses = newses.filter(update_time__gte=end_time)

        if start_time and end_time:
            newses = newses.filter(update_time__range=(start_time, end_time))

        # 通过title进行过滤
        title = request.GET.get('title', '')
        if title:
            newses = newses.filter(title__icontains=title)      #icontains模糊查询,忽略大小写

        # 通过作者名进行过滤
        author_name = request.GET.get('author_name', '')
        if author_name:
            newses = newses.filter(author__username__icontains=author_name)

        # 通过标签id进行过滤
        try:
            tag_id = int(request.GET.get('tag_id', 0))
        except Exception as e:
            logger.info("标签错误：\n{}".format(e))
            tag_id = 0
        newses = newses.filter(is_delete=False, tag_id=tag_id) or \
               newses.filter(is_delete=False)

        # 获取第几页内容
        try:
            page = int(request.GET.get('page', 1))
        except Exception as e:
            logger.info("当前页数错误：\n{}".format(e))
            page = 1
        paginator = Paginator(newses, 20)
        try:
            news_info = paginator.page(page)    #通过page方法把用户输入的页码传入
        except EmptyPage:
            # 若用户访问的页数大于实际页数，则返回最后一页数据
            logging.info("用户访问的页数大于总页数。")
            news_info = paginator.page(paginator.num_pages)     #默认显示最后一页

        #调用自定义翻页page_script
        paginator_data = page_script.get_paginator_data(paginator, news_info)

        #时间清洗
        start_time = start_time.strftime('%Y/%m/%d') if start_time else ''
        end_time = end_time.strftime('%Y/%m/%d') if end_time else ''
        context = {     #页面显示的数据
            'news_info': news_info,
            'tags': tags,
            'paginator': paginator,
            'start_time': start_time,
            "end_time": end_time,
            "title": title,
            "author_name": author_name,
            "tag_id": tag_id,

            "other_param": urlencode({      #把查询数据返回给前端作为url关键字参数
                "start_time": start_time,
                "end_time": end_time,
                "title": title,
                "author_name": author_name,
                "tag_id": tag_id,
            })
        }
        context.update(paginator_data)
        return render(request, 'admin/news/news_manage.html', context=context)

