from django.urls import path
from . import views
from .views import (
    CurrentUserView,
    GoogleConfigView,
    GoogleLoginView,
    LoginView,
    LogoutView,
    RegisterView,
)

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("google-login/", views.GoogleLoginView.as_view(), name="google-login"),
    path("me/", views.CurrentUserView.as_view(), name="current-user"),
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/google/config/", GoogleConfigView.as_view(), name="google-config"),
    path("auth/google/", GoogleLoginView.as_view(), name="google-login"),
    path("auth/me/", CurrentUserView.as_view(), name="current-user"),
]
