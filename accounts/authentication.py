import jwt
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions

from .tokens import decode_access_token


class BearerTokenAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).split()
        if not auth:
            token = request.COOKIES.get("access_token")
            if not token:
                return None
        else:
            if auth[0].lower() != self.keyword.lower().encode():
                return None

            if len(auth) == 1:
                raise exceptions.AuthenticationFailed("No token provided.")

            if len(auth) > 2:
                raise exceptions.AuthenticationFailed("Invalid token header.")

            try:
                token = auth[1].decode()
            except UnicodeError as exc:
                raise exceptions.AuthenticationFailed("Invalid token header.") from exc

        try:
            payload = decode_access_token(token)
        except jwt.ExpiredSignatureError as exc:
            raise exceptions.AuthenticationFailed("Token has expired.") from exc
        except jwt.InvalidTokenError as exc:
            raise exceptions.AuthenticationFailed("Invalid token.") from exc

        if payload.get("type") != "access":
            raise exceptions.AuthenticationFailed("Invalid token type.")

        user_model = get_user_model()
        try:
            user = user_model.objects.get(pk=payload["sub"])
        except user_model.DoesNotExist as exc:
            raise exceptions.AuthenticationFailed("User not found.") from exc

        if not user.is_active:
            raise exceptions.AuthenticationFailed("User account is disabled.")

        return user, payload

    def authenticate_header(self, request):
        return self.keyword
