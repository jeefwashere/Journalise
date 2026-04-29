from django.urls import path
from .views import ActivityStatsView

urlpatterns = [
    path("stats/", ActivityStatsView.as_view(), name="activity-stats"),
]
