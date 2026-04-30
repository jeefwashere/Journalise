from django.urls import path
from .views import ActivityTrackingView, CreateActivityList, GetActivityDetail

urlpatterns = [
    path("activities/", CreateActivityList.as_view()),
    path("activities/<int:pk>/", GetActivityDetail.as_view()),
    path("tracking/", ActivityTrackingView.as_view(), name="activity-tracking"),
]
