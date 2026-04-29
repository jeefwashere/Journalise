from django.shortcuts import render
from .models import Activity
from .serializers import ActivitySerializer
from rest_framework import generics, permissions


class CreateActivityList(generics.ListCreateAPIView):
    serializer_class = ActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        activities = Activity.objects.filter(user=self.request.user)

        date = self.request.query_params.get("date")

        if date:
            activities = activities.filter(started_at__date=date)

        return activities.order_by("-started_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class GetActivityDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Activity.objects.filter(user=self.request.user)
