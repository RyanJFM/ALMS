from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    CourseViewSet,
    AssignmentViewSet,
    AssignmentSessionViewSet,
    EventLogViewSet,
    SubmissionViewSet
)

# initialize the router
router = DefaultRouter()

# register the viewset with a url prefix
router.register(r'users', UserViewSet, basename='user')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'assignments', AssignmentViewSet, basename='assignment')
router.register(r'sessions', AssignmentSessionViewSet, basename='session')
router.register(r'events', EventLogViewSet, basename='event')
router.register(r'submissions', SubmissionViewSet, basename='submission')

# include the router's urls in the urlpatterns
urlpatterns = [
    path('', include(router.urls)),
]