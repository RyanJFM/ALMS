from django.contrib import admin

from .models import User, Course, Assignment, AssignmentSession, EventLog, Submission

admin.site.register(User)       
admin.site.register(Course)
admin.site.register(Assignment)
admin.site.register(AssignmentSession)
admin.site.register(EventLog)
admin.site.register(Submission)
