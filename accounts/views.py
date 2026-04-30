import jwt
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate
from django.utils.text import slugify
from rest_framework import generics, permissions, serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from .authentication import BearerTokenAuthentication
from .models import UserProfile
from .serializers import (
    GoogleLoginSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .tokens import create_access_token

GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


def get_google_client_id():
    client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    if client_id:
        return client_id

    try:
        from allauth.socialaccount.models import SocialApp
    except ImportError:
        return ""

    social_app = SocialApp.objects.filter(provider="google").first()
    if social_app:
        return social_app.client_id

    return ""


def verify_google_id_token(id_token):
    client_id = get_google_client_id()
    if not client_id:
        raise serializers.ValidationError(
            {"id_token": "GOOGLE_OAUTH_CLIENT_ID is not configured."}
        )

    try:
        jwk_client = jwt.PyJWKClient(GOOGLE_CERTS_URL)
        signing_key = jwk_client.get_signing_key_from_jwt(id_token)
        payload = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=client_id,
            options={"require": ["exp", "iat", "sub", "aud"]},
        )
    except jwt.InvalidTokenError as exc:
        raise serializers.ValidationError(
            {"id_token": "Invalid Google ID token."}
        ) from exc

    if payload.get("iss") not in GOOGLE_ISSUERS:
        raise serializers.ValidationError({"id_token": "Invalid Google issuer."})

    return payload


def is_verified_email(value):
    return value is True or value == "true"


def make_unique_username(email, google_sub):
    user_model = get_user_model()
    base = slugify(email.split("@", maxsplit=1)[0]) or f"google-{google_sub[:12]}"
    base = base[:150]
    username = base
    suffix = 1

    while user_model.objects.filter(username=username).exists():
        ending = f"-{suffix}"
        username = f"{base[: 150 - len(ending)]}{ending}"
        suffix += 1

    return username


def get_or_create_google_user(google_payload):
    google_sub = google_payload.get("sub")
    email = google_payload.get("email", "").strip().lower()

    if not google_sub:
        raise serializers.ValidationError({"id_token": "Google subject is missing."})

    if not email:
        raise serializers.ValidationError({"id_token": "Google email is missing."})

    if not is_verified_email(google_payload.get("email_verified")):
        raise serializers.ValidationError({"id_token": "Google email is not verified."})

    user_model = get_user_model()
    user = user_model.objects.filter(email__iexact=email).first()

    if user is None:
        user = user_model.objects.create_user(
            username=make_unique_username(email, google_sub),
            email=email,
        )

    update_fields = []
    first_name = google_payload.get("given_name", "")
    last_name = google_payload.get("family_name", "")

    if first_name and not user.first_name:
        user.first_name = first_name
        update_fields.append("first_name")

    if last_name and not user.last_name:
        user.last_name = last_name
        update_fields.append("last_name")

    if user.email != email:
        user.email = email
        update_fields.append("email")

    if update_fields:
        user.save(update_fields=update_fields)

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.display_name = google_payload.get("name", profile.display_name)
    profile.avatar_url = google_payload.get("picture", profile.avatar_url)
    profile.save()

    return user


def auth_response(user, access_token, status_code=status.HTTP_200_OK):
    response = Response(
        {
            "token_type": "Bearer",
            "access_token": access_token,
            "expires_in": settings.JOURNALISE_ACCESS_TOKEN_SECONDS,
            "user": UserSerializer(user).data,
        },
        status=status_code,
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        max_age=settings.JOURNALISE_ACCESS_TOKEN_SECONDS,
        path="/",
    )

    return response


# Google Login/Register view
class GoogleLoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        google_payload = verify_google_id_token(serializer.validated_data["id_token"])
        user = get_or_create_google_user(google_payload)
        access_token, _ = create_access_token(user)

        return auth_response(user, access_token, status.HTTP_200_OK)


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        access_token, _ = create_access_token(user)

        return auth_response(user, access_token, status.HTTP_201_CREATED)


class LogoutView(APIView):
    authentication_classes = [BearerTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        response = Response(
            {"detail": "Logged out successfully."}, status=status.HTTP_200_OK
        )

        response.delete_cookie(key="access_token", path="/", samesite="Lax")

        return response


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        user = authenticate(username=username, password=password)

        if not user:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        access_token, _ = create_access_token(user)

        return auth_response(user, access_token, status.HTTP_200_OK)


class CurrentUserView(generics.RetrieveUpdateAPIView):
    authentication_classes = [BearerTokenAuthentication, SessionAuthentication]
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
