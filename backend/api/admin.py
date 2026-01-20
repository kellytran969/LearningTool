from django.contrib import admin
from .models import UserPerformanceMetric, Course, LearningProgress, APIResponseLog, SystemMetric

# Register your models here.

admin.site.register(UserPerformanceMetric)
admin.site.register(Course)
admin.site.register(LearningProgress)
admin.site.register(APIResponseLog)
admin.site.register(SystemMetric)
