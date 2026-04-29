from django.urls import path
from . import views
from .views import GoogleLoginView, CurrentUserView

urlpatterns = [
    path("google-login/", views.GoogleLoginView.as_view(), name="google-login"),
    path("me/", views.CurrentUserView.as_view(), name="current-user"),
    path("auth/google/", GoogleLoginView.as_view(), name="google-login"),
    path("auth/me/", CurrentUserView.as_view(), name="current-user"),
]
