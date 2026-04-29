from django.urls import path
from .views import CreateActivityList, GetActivityDetail

urlpatterns = [
    path("activities/", CreateActivityList.as_view()),
    path("activities/<int:pk>/", GetActivityDetail.as_view()),
]
