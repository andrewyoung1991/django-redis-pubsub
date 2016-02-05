from django.contrib.auth import get_user_model

__all__ = (
    "authtoken_method", "authjwt_method"
    )


def authtoken_method(token):
    """ an authentication method using rest_framework Token
    """
    from rest_framework.authtoken.models import Token
    user = Token.objects.filter(key=token).first()
    if user is not None:
        user = user.user
    return user


def authjwt_method(token):
    """ an authentication method using rest_framework_jwt
    """
    import jwt
    from rest_framework_jwt.authentication import (jwt_decode_handler,
                                                    jwt_get_username_from_payload)
    try:
        payload = jwt_decode_handler(token)
    except (jwt.ExpiredSignature, jwt.DecodeError, jwt.InvalidTokenError):
        return None

    User = get_user_model()
    username = jwt_get_username_from_payload(payload)
    if not username:  # pragma: no cover
        return None

    try:
        user = User.objects.get_by_natural_key(username)
    except User.DoesNotExist:  # pragma: no cover
        return None

    return user
