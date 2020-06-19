import json

from django.db.models import Count
from django.shortcuts import render
from news import models
# Create your views here.
from django.views import View


#admin后台首页面
from utils.json_fun import to_json_data
from utils.res_code import Code, error_map


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














