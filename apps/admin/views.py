import json
from datetime import datetime
from urllib.parse import urlencode
from django.views.decorators.csrf import csrf_exempt
from admin import forms
from course.models import Course, Teacher, CourseCategory
from users.models import User
from utils.qiniu_secrets import qiniu_secret_info
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Count
from django.http import Http404, JsonResponse
from django.shortcuts import render
from news import models
from doc.models import Doc
# Create your views here.
from django.views import View
import qiniu
from utils import page_script
from utils.fastdfs.fdfs import FDFS_Client
from utils.json_fun import to_json_data
from utils.res_code import Code, error_map
import logging
from collections import OrderedDict
from django.utils.decorators import method_decorator
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required


logger = logging.getLogger("django")



#admin后台首页面

class IndexView(LoginRequiredMixin, View):
    #没有登录重定向到login界面
    login_url = "users:login"
    redirect_field_name = "next"

    def get(self, request):
        return render(request, "admin/index/index.html")


#新闻标签修改
class TagsManageView(PermissionRequiredMixin, View):
    #組权限，raise_exception默认false
    permission_required = ("news.view_tag", "news.add_tag", "news.change_tag", "news.delete_tag")
    raise_exception = True
    #如果访问的不是get方法，不允许访问权限
    def handle_no_permission(self):
        if self.request.method != "GET":
            return to_json_data(errno=Code.PARAMERR, errmsg="没有操作权限")
        else:
            return super(TagsManageView, self).handle_no_permission()

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


#新闻编辑，删除，更新
class NewsEditView(View):
    """
    news_id
    """
    def get(self, request, news_id):
        """
        获取待编辑的文章
        :param request:
        :param news_id:
        :return:
        """
        news = models.News.objects.filter(is_delete=False, id=news_id).first()
        if news:
            tags = models.Tag.objects.only("id", "name").filter(is_delete=False)
            context = {
                "news": news,
                "tags": tags,
            }
            return render(request, "admin/news/news_pub.html", context=context)
        else:
            Http404("需要更新的文章不存在")

    def delete(self, request, news_id):
        """
        删除文章
        :param request:
        :param news_id:
        :return:
        """
        news = models.News.objects.only('id').filter(id=news_id).first()
        if news:
            news.is_delete = True
            news.save(update_fields=["is_delete"])
            return to_json_data(errmsg="文章删除成功")
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg="需要删除的文章不存在")

    def put(self, request, news_id):
        """
        更新文章
        :param request:
        :param news_id:
        :return:
        """
        news = models.News.objects.filter(is_delete=False, id=news_id).first()
        if not news:
            return to_json_data(errno=Code.NODATA, errmsg='需要更新的文章不存在')
        #获取前端数据
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))
        #传数据进入表单效验
        form = forms.NewsPubForm(data=dict_data)
        if form.is_valid():
            news.title = form.cleaned_data.get('title')
            news.digest = form.cleaned_data.get('digest')
            news.content = form.cleaned_data.get('content')
            news.image_url = form.cleaned_data.get('image_url')
            news.tag = form.cleaned_data.get('tag')
            news.save()
            return to_json_data(errmsg='文章更新成功')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串

            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


#文章发布
class NewsPubView(View):
    """
    """

    def get(self, request):
        """
        获取文章标签
        """
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)

        return render(request, 'admin/news/news_pub.html', locals())

    def post(self, request):
        """
        新增文章
        """
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))

        form = forms.NewsPubForm(data=dict_data)
        if form.is_valid():

            # 获取表单提交的数据，先创建实例，不保存到数据库
            news_instance = form.save(commit=False)
            news_instance.author_id = request.user.id
            # news_instance.author_id = 1     # for test
            news_instance.save()
            return to_json_data(errmsg='文章创建成功')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串

            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


#图片上传到七牛云
class NewsUploadImage(View):

    # permission_required = ('news.add_news',)
    #
    # def handle_no_permission(self):
    #     return to_json_data(errno=Code.ROLEERR, errmsg='没有上传图片的权限')

    def post(self, request):
        image_file = request.FILES.get('image_file')
        if not image_file:
            logger.info('从前端获取图片失败')
            return to_json_data(errno=Code.NODATA, errmsg='从前端获取图片失败')
        #判断上传图片在不在自定义的图片格式里面
        if image_file.content_type not in ('image/jpeg', 'image/png', 'image/gif'):
            return to_json_data(errno=Code.DATAERR, errmsg='不能上传非图片文件')
        #获取上传的图片后缀名，没有就定义jpg格式
        try:
            image_ext_name = image_file.name.split('.')[-1]
        except Exception as e:
            logger.info('图片拓展名异常：{}'.format(e))
            image_ext_name = 'jpg'
        #图片正常上传图片
        try:            #upload_by_buffer上传一个文件到缓存区
            upload_res = FDFS_Client.upload_by_buffer(image_file.read(), file_ext_name=image_ext_name)
        except Exception as e:
            logger.error('图片上传出现异常：{}'.format(e))
            return to_json_data(errno=Code.UNKOWNERR, errmsg='图片上传异常')
        else:
            #获取上传图片状态
            if upload_res.get('Status') != 'Upload successed.':
                logger.info('图片上传到FastDFS服务器失败')
                return to_json_data(errno=Code.UNKOWNERR, errmsg='图片上传到服务器失败')
            #上传成功返回上传地址的图片id，然后拼接fastfds网址
            else:
                image_name = upload_res.get('Remote file_id')
                image_url = settings.FASTDFS_SERVER_DOMAIN + image_name
                return to_json_data(data={'image_url': image_url}, errmsg='图片上传成功')


#七牛云Token
class UploadToken(View):

    def get(self, request):
        access_key = qiniu_secret_info.QI_NIU_ACCESS_KEY
        secret_key = qiniu_secret_info.QI_NIU_SECRET_KEY
        bucket_name = qiniu_secret_info.QI_NIU_BUCKET_NAME

        # 构建鉴权对象
        q = qiniu.Auth(access_key, secret_key)
        token = q.upload_token(bucket_name)
        return JsonResponse({"uptoken": token})


#新闻编辑页面Markdown上传图片
@method_decorator(csrf_exempt, name="dispatch")
class MarkDownUploadImage(View):

    def post(self, request):
        image_file = request.FILES.get('editormd-image-file')
        if not image_file:
            logger.info('从前端获取图片失败')
            return JsonResponse({'success': 0, 'message': '从前端获取图片失败'})

        if image_file.content_type not in ('image/jpeg', 'image/png', 'image/gif'):
            return JsonResponse({'success': 0, 'message': '不能长传非图片文件'})

        try:
            image_ext_name = image_file.name.split('.')[-1]
        except Exception as e:
            logger.info('图片扩展名异常: {}'.format(e))
            image_ext_name = 'jpg'

        try:
            upload_res = FDFS_Client.upload_by_buffer(image_file.read(), file_ext_name=image_ext_name)
        except Exception as e:
            logger.info('图片上传出现异常: {}'.format(e))
            return JsonResponse({'success': 0, 'message': '图片上传异常'})
        else:
            if upload_res.get('Status') != 'Upload successed.':
                logger.info('图片上传到FastDFS服务器失败')
                return JsonResponse({'success': 0, 'message': '图片上传到服务器失败'})
            else:
                image_name = upload_res.get('Remote file_id')
                image_url = settings.FASTDFS_SERVER_DOMAIN + image_name
                return JsonResponse({'success': 0, 'message': '图片上传成功', 'url': image_url})


#后台文章轮播图管理
class BannerManageView(View):
    """
    url: banners
    """
    def get(self, request):
        """
        OrderedDict:对返回的字典对象进行排序
        :param request:
        :return:
        """
        priority_dict = OrderedDict(models.Banner.PRI_CHOICES)
        banners = models.Banner.objects.only("priority", "image_url").filter(is_delete=False)
        return render(request, 'admin/news/news_banner.html', locals())


#后台文章轮播图删除,更新
class BannerEditView(View):
    #轮播图删除
    def delete(self, request, banner_id):
        """
        通过banner_id更改banner.is_delete
        :param request:
        :param banner_id:
        :return:
        """
        banner = models.Banner.objects.only('id').filter(id=banner_id).first()
        if banner:
            banner.is_delete = True
            banner.save(update_fields=['is_delete'])
            return to_json_data(errmsg='轮播图删除成功！')
        else:
            return to_json_data(errno=Code.NODATA, errmsg='轮播图不存在')

    #轮播图更新
    def put(self, request, banner_id):
        """
        1. priority
        2. image_url
        save()
        :param request:
        :param banner_id:
        :return:
        """
        banner = models.Banner.objects.only('id').filter(id=banner_id).first()
        if not banner:
            return to_json_data(errno=Code.PARAMERR,
                                errmsg='The rotation chart that needs to be updated does not exist')
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))

        try:
            priority = int(dict_data['priority'])
            priority_list = [i for i, _ in models.Banner.PRI_CHOICES]
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='轮播图优先级设置错误')
        except Exception as e:
            logger.info('轮播图优先级异常\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图优先级设置错误')

        image_url = dict_data['image_url']
        if not image_url:
            return to_json_data(errno=Code.PARAMERR, errmsg='图片为空')
        if banner.image_url == priority and banner.image_url == image_url:
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图优先级未更改')

        banner.priority = priority
        banner.image_url = image_url
        banner.save(update_fields=['priority', 'image_url'])
        return to_json_data(errmsg='轮播图更新成功')


#后台轮播图添加功能
class BannerAddView(View):

    def get(self, request):
        tags = models.Tag.objects.values('id', 'name').annotate(num_news=Count('news')). \
            filter(is_delete=False).order_by('-num_news', 'update_time')
        # 优先级列表
        # priority_list = {K: v for k, v in models.Banner.PRI_CHOICES}
        priority_dict = OrderedDict(models.Banner.PRI_CHOICES)

        return render(request, 'admin/news/news_banner_add.html', locals())

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
            priority_list = [i for i, _ in models.Banner.PRI_CHOICES]
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='轮播图的优先级设置错误')
        except Exception as e:
            logger.info('轮播图优先级异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图的优先级设置错误')

        # 获取轮播图url
        image_url = dict_data.get('image_url')
        if not image_url:
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图url为空')

        # 创建轮播图
        banners_tuple = models.Banner.objects.get_or_create(news_id=news_id)
        banner, is_created = banners_tuple

        banner.priority = priority
        banner.image_url = image_url
        banner.save(update_fields=['priority', 'image_url'])
        return to_json_data(errmsg="轮播图创建成功")


#后台文档
class DocManageView(View):

    def get(self, request):
        docs = Doc.objects.only("title", "update_time").filter(is_delete=False)
        return render(request, "admin/news/doc_manage.html", locals())


#后台文档编辑,删除
class DocEditView(View):
    """
    doc_id
    """
    def get(self,request, doc_id):
        doc = Doc.objects.only("id").filter(id=doc_id).first()
        if doc:
            return render(request, "admin/doc/doc_pub.html", locals())
        else:
            raise Http404("需要更新的文档不存在")

    def delete(self, request, doc_id):
        doc = Doc.objects.only('id').filter(id=doc_id).first()
        if doc:
            doc.is_delete = True
            doc.save(update_fields=['is_delete'])
            return to_json_data(errmsg='文档删除成功')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要删除的文档不存在')

    def put(self, request, doc_id):
        doc = Doc.objects.only('id').filter(id=doc_id).first()
        if not doc:
            return to_json_data(errno=Code.NODATA, errmsg="需要更新的文章不存在")
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode("utf8"))

        form = forms.DocsPubForm(data=dict_data)
        if form.is_valid():
            doc.title = form.cleaned_data.get('title')
            doc.desc = form.cleaned_data.get('desc')
            doc.file_url = form.cleaned_data.get('file_url')
            doc.image_url = form.cleaned_data.get('image_url')
            doc.save()
            return to_json_data(errmsg='文档更新成功')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串

            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


#后台文档上传文件
class DocUploadFile(View):
    """
    route: /admin/docs/files/
    """

    def post(self, request):
        text_file = request.FILES.get('text_file')
        if not text_file:
            logger.info('从前端获取文件失败')
            return to_json_data(errno=Code.NODATA, errmsg='从前端获取文件失败')

        if text_file.content_type not in ('application/octet-stream', 'application/pdf',
                                          'application/zip', 'text/plain', 'application/x-rar'):
            return to_json_data(errno=Code.DATAERR, errmsg='不能上传非文本文件')

        try:
            text_ext_name = text_file.name.split('.')[-1]
        except Exception as e:
            logger.info('文件拓展名异常：{}'.format(e))
            text_ext_name = 'pdf'

        try:
            upload_res = FDFS_Client.upload_by_buffer(text_file.read(), file_ext_name=text_ext_name)
        except Exception as e:
            logger.error('文件上传出现异常：{}'.format(e))
            return to_json_data(errno=Code.UNKOWNERR, errmsg='文件上传异常')
        else:
            if upload_res.get('Status') != 'Upload successed.':
                logger.info('文件上传到FastDFS服务器失败')
                return to_json_data(Code.UNKOWNERR, errmsg='文件上传到服务器失败')
            else:
                text_name = upload_res.get('Remote file_id')
                text_url = settings.FASTDFS_SERVER_DOMAIN + text_name
                return to_json_data(data={'text_file': text_url}, errmsg='文件上传成功')


#后台文档发布
class DocsPubView(View):
    """
    route: /admin/docs/pub/
    """

    def get(self, request):

        return render(request, 'admin/doc/doc_pub.html', locals())

    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))

        form = forms.DocsPubForm(data=dict_data)
        if form.is_valid():
            docs_instance = form.save(commit=False)
            docs_instance.author_id = request.user.id
            docs_instance.save()
            return to_json_data(errmsg='文档创建成功')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串

            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


#在线课堂课程管理
class CoursesManageView(View):
    def get(self, request):
        courses = Course.objects.select_related('category', 'teacher').\
            only('title', 'category__name', 'teacher__name').filter(is_delete=False)
        return render(request, 'admin/course/course_manage.html', locals())


#在线课堂编辑和删除
class CourseEditView(View):

    def get(self,request,course_id):
        course = Course.objects.filter(is_delete=False,id=course_id).first()
        if course:
            teachers = Teacher.objects.only('name').filter(is_delete=False)
            categories = CourseCategory.objects.only('name').filter(is_delete=False)
            return render(request,'admin/course/course_pub.html',locals())
        else:
            Http404('需要更新的课程不存在')

    def delete(self,request,course_id):
        course = Course.objects.only('id').filter(is_delete=False,id=course_id).first()
        if course:
            course.is_delete=True
            course.save(update_fields=['is_delete'])
            return to_json_data(errmsg='课程删除成功')
        else:
            return to_json_data(errno=Code.PARAMERR,errmsg='更新的课程不存在')

    def put(self,request,course_id):
        course = Course.objects.filter(is_delete=False,id=course_id).first()
        if not course:
            return to_json_data(errno=Code.NODATA, errmsg='需要更新的课程不存在')
        json_str = request.body
        if not  json_str:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_str.decode('utf8'))
        form = forms.CoursePubForm(data=dict_data)
        if form.is_valid():
            for attr,value in form.cleaned_data.items():
                setattr(course,attr,value)
            course.save()
            return to_json_data(errmsg='课程更新成功')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


#在线课堂发布
class CoursePubView(View):
    def get(self,request):
        teachers = Teacher.objects.only('name').filter(is_delete=False)
        categories = CourseCategory.objects.only('name').filter(is_delete=False)
        return render(request,'admin/course/course_pub.html',locals())

    def post(self,request):
        json_str = request.body
        if not json_str:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        data_dict = json.loads(json_str.decode('utf8'))
        form = forms.CoursePubForm(data=data_dict)
        if form.is_valid():
            course_instance = form.save(commit=False)
            course_instance.save()
            return to_json_data(errmsg='课程发布成功')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


#后台用户组管理
class GroupsManageView(View):
    def get(self, request):
        groups = Group.objects.values("id", "name").annotate(num_users=Count('user')).\
            order_by('-num_users', 'id')
        return render(request, 'admin/user/groups_manage.html', locals())


#后台用户组编辑，删除
class GroupsEditView(View):
    """
    route: /admin/groups/<int:group_id>/
    """
    def get(self, request, group_id):
        """
        :param request:
        :param group_id:
        :return:
        """
        group = Group.objects.filter(id=group_id).first()
        if group:
            permissions = Permission.objects.only('id').all()
            return render(request, 'admin/user/groups_add.html', locals())
        else:
            raise Http404('需要更新的组不存在！')

    def delete(self, request, group_id):
        group = Group.objects.filter(id=group_id).first()
        if group:
            group.permissions.clear()  # 清空权限
            group.delete()
            return to_json_data(errmsg="用户组删除成功")
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg="需要删除的用户组不存在")

    def put(self, request, group_id):
        group = Group.objects.filter(id=group_id).first()
        if not group:
            return to_json_data(errno=Code.NODATA, errmsg='需要更新的用户组不存在')
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))

        # 取出组名，进行判断
        group_name = dict_data.get('name', '').strip()
        if not group_name:
            return to_json_data(errno=Code.PARAMERR, errmsg='组名为空')

        if group_name != group.name and Group.objects.filter(name=group_name).exists():
            return to_json_data(errno=Code.DATAEXIST, errmsg='组名已存在')

        # 取出权限
        group_permissions = dict_data.get('group_permissions')
        if not group_permissions:
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数为空')

        try:        #set() 集合去重
            permissions_set = set(int(i) for i in group_permissions)
        except Exception as e:
            logger.info('传的权限参数异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数异常')

        all_permissions_set = set(i.id for i in Permission.objects.only('id'))
        if not permissions_set.issubset(all_permissions_set):
            return to_json_data(errno=Code.PARAMERR, errmsg='有不存在的权限参数')

        existed_permissions_set = set(i.id for i in group.permissions.all())
        if group_name == group.name and permissions_set == existed_permissions_set:
            return to_json_data(errno=Code.DATAEXIST, errmsg='用户组信息未修改')
        # 设置权限
        for perm_id in permissions_set:
            p = Permission.objects.get(id=perm_id)
            group.permissions.add(p)
        group.name = group_name
        group.save()
        return to_json_data(errmsg='组更新成功！')


#后台用户组添加
class GroupsAddView(View):
    """
    route: /admin/groups/add/
    """
    # permission_required = ('auth.add_group', 'auth.view_group')
    # raise_exception = True
    #
    # def handle_no_permission(self):
    #     if self.request.method.lower() != 'get':
    #         return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
    #     else:
    #         return super(GroupsAddView, self).handle_no_permission()

    def get(self, request):
        permissions = Permission.objects.only('id').all()

        return render(request, 'admin/user/groups_add.html', locals())

    def post(self, request):

        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))

        # 取出组名，进行判断
        group_name = dict_data.get('name', '').strip()
        if not group_name:
            return to_json_data(errno=Code.PARAMERR, errmsg='组名为空')
        #判断組是否存在，get_or_create
        one_group, is_created = Group.objects.get_or_create(name=group_name)
        if not is_created:
            return to_json_data(errno=Code.DATAEXIST, errmsg='组名已存在')

        # 取出权限
        group_permissions = dict_data.get('group_permissions')
        if not group_permissions:
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数为空')

        try:
            permissions_set = set(int(i) for i in group_permissions)
        except Exception as e:
            logger.info('传的权限参数异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数异常')

        all_permissions_set = set(i.id for i in Permission.objects.only('id'))
        #issubset 判断集合的所有元素是否都包含在指定集合中，如果是则返回 True，否则返回 False
        if not permissions_set.issubset(all_permissions_set):
            return to_json_data(errno=Code.PARAMERR, errmsg='有不存在的权限参数')

        # 设置权限，保存到数据库
        for perm_id in permissions_set:
            p = Permission.objects.get(id=perm_id)
            one_group.permissions.add(p)

        one_group.save()
        return to_json_data(errmsg='组创建成功！')


#后台用户管理
class UsersManageView(View):
    """
    url: /admin/users
    """
    def get(self, request):
        users = User.objects.only('username', 'is_staff', 'is_superuser').filter(is_active=True)

        return render(request, 'admin/user/users_manage.html', locals())


#后台用户编辑，删除
class UsersEditView(PermissionRequiredMixin, View):
    """
    route: /admin/users/<int:user_id>/
    """
    permission_required = ('users.change_users', 'users.delete_users')
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(UsersEditView, self).handle_no_permission()

    def get(self, request, user_id):
        user_instance = User.objects.filter(id=user_id).first()
        if user_instance:
            groups = Group.objects.only('name').all()
            return render(request, 'admin/user/users_edit.html', locals())
        else:
            raise Http404('需要更新的用户不存在！')

    def delete(self, request, user_id):
        user_instance = User.objects.filter(id=user_id).first()  # 返回一个查询集
        if user_instance:
            user_instance.groups.clear()    # 清除用户组
            user_instance.user_permissions.clear()  # 清除用户权限
            user_instance.is_active = False  # 设置为不激活状态
            user_instance.save()
            return to_json_data(errmsg="用户删除成功")
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg="需要删除的用户不存在")

    def put(self, request, user_id):
        user_instance = User.objects.filter(id=user_id).first()
        if not user_instance:
            return to_json_data(errno=Code.NODATA, errmsg='需要更新的用户不存在')

        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))

        # 取出参数，进行判断
        try:
            groups = dict_data.get('groups')    # 取出用户组列表

            is_staff = int(dict_data.get('is_staff'))
            is_superuser = int(dict_data.get('is_superuser'))
            is_active = int(dict_data.get('is_active'))
            params = (is_staff, is_superuser, is_active)
            if not all([p in (0, 1) for p in params]):      #判断权限是否是0，1状态
                return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')
        except Exception as e:
            logger.info('从前端获取参数出现异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')

        try:
            groups_set = set(int(i) for i in groups) if groups else set()
        except Exception as e:
            logger.info('传的用户组参数异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='用户组参数异常')

        all_groups_set = set(i.id for i in Group.objects.only('id'))
        if not groups_set.issubset(all_groups_set):
            return to_json_data(errno=Code.PARAMERR, errmsg='有不存在的用户组参数')

        gs = Group.objects.filter(id__in=groups_set)
        # 先清除组
        user_instance.groups.clear()
        user_instance.groups.set(gs)

        user_instance.is_staff = bool(is_staff)
        user_instance.is_superuser = bool(is_superuser)
        user_instance.is_active = bool(is_active)
        user_instance.save()
        return to_json_data(errmsg='用户信息更新成功！')











