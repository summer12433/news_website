from django.shortcuts import render
from django.views import View
import logging
from course import models
from django.http import Http404
# Create your views here.
logger = logging.getLogger("django")




#课程列表
def course_list(request):
    courses = models.Course.objects.only("title", "cover_url", "teacher__positional_title").filter(is_delete=False)

    return render(request, "course/course.html", locals())


#课程详情页
class CourseDetailView(View):
    """
    url: <int: course_id>
    """
    def get(self, request, course_id):
        try:
            course = models.Course.objects.only("title", "cover_url", "video_url", "profile", "outline",
                                                "teacher__name", "teacher__avatar_url", "teacher__positional_title",
                                                "teacher__profile").select_related("teacher").\
                filter(is_delete=False, id=course_id).first()

            return render(request, "course/course_detail.html", locals())
        except models.Course.DoesNotExist as e:
            logger.info("当前课程出现异常: \n{}".format(e))













