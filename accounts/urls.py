from django.urls import path
from . import views

urlpatterns = [
    path("google-login/", views.GoogleLoginView.as_view(), name="google-login"),
    path("me/", views.CurrentUserView.as_view(), name="current-user"),
    # path("", views.home),
    # path("logout", views.logout_view)
]
