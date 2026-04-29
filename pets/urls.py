from django.urls import path

from .views import PetDetailView, PetListView, PetMoodView

urlpatterns = [
    path("pets/", PetListView.as_view(), name="pet-list"),
    path("pets/mood/", PetMoodView.as_view(), name="pet-mood"),
    path("pets/<int:pk>/", PetDetailView.as_view(), name="pet-detail"),
]
