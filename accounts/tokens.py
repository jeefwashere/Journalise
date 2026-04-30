from datetime import timedelta

import jwt
from django.conf import settings
from django.utils import timezone


DEFAULT_ACCESS_TOKEN_SECONDS = 3600
DEFAULT_JWT_ISSUER = "Journalise"


def get_access_token_seconds():
    return getattr(
        settings, "JOURNALISE_ACCESS_TOKEN_SECONDS", DEFAULT_ACCESS_TOKEN_SECONDS
    )


def get_jwt_issuer():
    return getattr(settings, "JOURNALISE_JWT_ISSUER", DEFAULT_JWT_ISSUER)


def create_access_token(user):
    now = timezone.now()
    expires_at = now + timedelta(seconds=get_access_token_seconds())
    payload = {
        "iss": get_jwt_issuer(),
        "sub": str(user.pk),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "type": "access",
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token, expires_at


def decode_access_token(token):
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=["HS256"],
        issuer=get_jwt_issuer(),
        options={"require": ["exp", "iat", "sub", "type"]},
    )
