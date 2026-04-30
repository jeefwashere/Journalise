from .models import Activity
from .serializers import ActivitySerializer
from rest_framework import generics, permissions, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import BearerTokenAuthentication
from journal.activity_ingest import persist_sessions
from journal.tracking_runtime import get_tracking_status, start_tracking, stop_tracking


class CreateActivityList(generics.ListCreateAPIView):
    authentication_classes = [BearerTokenAuthentication, SessionAuthentication]
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
    authentication_classes = [BearerTokenAuthentication, SessionAuthentication]
    serializer_class = ActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Activity.objects.filter(user=self.request.user)


class ActivityTrackingView(APIView):
    authentication_classes = [BearerTokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(get_tracking_status(request.user), status=status.HTTP_200_OK)

    def post(self, request):
        sessions = request.data.get("sessions")
        if sessions is None and "session" in request.data:
            sessions = [request.data["session"]]

        if sessions is None and "enabled" in request.data:
            if bool(request.data["enabled"]):
                return Response(start_tracking(request.user), status=status.HTTP_200_OK)

            result = stop_tracking(request.user)
            activity = result.pop("activity")
            if activity is not None:
                result["activity_id"] = activity.pk
            return Response(result, status=status.HTTP_200_OK)

        if sessions is None:
            sessions = []

        if not isinstance(sessions, list):
            return Response(
                {"sessions": "Expected a list of activity sessions."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = persist_sessions(request.user, sessions)
        except (KeyError, TypeError, ValueError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "tracking": bool(request.data.get("enabled", True)),
                "imported": len(result["activities"]),
                "created": result["created_count"],
                "updated": result["updated_count"],
                "activity_ids": [activity.pk for activity in result["activities"]],
            },
            status=status.HTTP_200_OK,
        )
