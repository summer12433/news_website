from django.shortcuts import render
from django.views import View
from django.conf import settings
from .models import Doc
import requests
import logging
from django.http import FileResponse, Http404
from django.utils.encoding import escape_uri_path
# Create your views here.
logger = logging.getLogger("django")



#书籍页面
def doc_index(request):
    docs = Doc.objects.defer('author', 'create_time', 'update_time', 'is_delete').filter(is_delete=False)
    return render(request, 'doc/docDownload.html', locals())

#文档下载
class DocDownload(View):
    """
    url: /doc/<int: doc_id>
    """
    def get(self, request, doc_id):
        doc = Doc.objects.only("file_url").filter(is_delete=False, id=doc_id).first()
        if doc:
            doc_url = doc.file_url
            #http://47.100.201.79:8888/
            #拼接文档地址
            if doc_url.split("/")[1] == "media":
                doc_url = settings.SITE_DOMAIN_PORT + doc_url
            try:
                #获取文件二进制，FileResponse接收带有任何二进制类容的对象，stream=True,指定访问才下载，不指定会立即保存到redis
                res = FileResponse(requests.get(doc_url, stream=True))
            except Exception as e:
                logger.info("获取文档内容出现异常：\n{}".format(e))
                raise Http404("文档下载异常！")

            #指定文档格式,split切割返回列表
            ex_name = doc_url.split('.')[-1]
            #判断文件地址是否存在
            if not ex_name:
                raise Http404("文件地址异常")
            else:
                #lower() 转换小写
                ex_name = ex_name.lower()

            if ex_name == "pdf":        #判断格式，指定格式
                res["Content-type"] = "application/pdf"
            elif ex_name == "zip":
                res["Content-type"] = "application/zip"
            elif ex_name == "doc":
                res["Content-type"] = "application/msword"
            elif ex_name == "xls":
                res["Content-type"] = "application/vnd.ms-excel"
            elif ex_name == "docx":
                res["Content-type"] = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            elif ex_name == "ppt":
                res["Content-type"] = "application/vnd.ms-powerpoint"
            elif ex_name == "pptx":
                res["Content-type"] = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            else:
                raise Http404("文档格式不正确！")

            #escape_uri_path,把文件名转换成url编码
            doc_filename = escape_uri_path(doc_url.split('/')[-1])
            # 设置为inline，会直接打开
            res["Content-Disposition"] = "attachment; filename*=UTF-8''{}".format(doc_filename)
            return res

        else:
            raise Http404("文档不存在！")






