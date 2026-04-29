from rest_framework import generics, permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import BearerTokenAuthentication
from accounts.models import UserProfile

from .choices import PetMood
from .models import Pet
from .serializers import PetMoodActionSerializer, PetSerializer


class PetListView(generics.ListAPIView):
    authentication_classes = [BearerTokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    queryset = Pet.objects.all()
    serializer_class = PetSerializer


class PetDetailView(generics.RetrieveAPIView):
    authentication_classes = [BearerTokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    queryset = Pet.objects.all()
    serializer_class = PetSerializer


class PetMoodView(APIView):
    authentication_classes = [BearerTokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PetMoodActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.pet_mood = serializer.get_mood()
        update_fields = ["pet_mood", "updated_at"]

        if profile.current_pet_id:
            mood_pet = Pet.objects.filter(
                pet_type=profile.current_pet.pet_type,
                level=profile.current_pet.level,
                mood=profile.pet_mood,
            ).first()
            if mood_pet is not None:
                profile.current_pet = mood_pet
                update_fields.append("current_pet")

        profile.save(update_fields=update_fields)

        return Response(
            {
                "pet_mood": profile.pet_mood,
                "pet_mood_display": PetMood(profile.pet_mood).label,
                "current_pet": PetSerializer(profile.current_pet).data
                if profile.current_pet_id
                else None,
            }
        )
