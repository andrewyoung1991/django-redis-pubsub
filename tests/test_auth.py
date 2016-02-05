import pytest

from rest_framework.authtoken.models import Token
from rest_framework_jwt.utils import jwt_payload_handler, jwt_encode_handler

from redis_pubsub import auth


@pytest.mark.django_db
@pytest.mark.parametrize("expect", [
    True, False
    ])
def test_authtoken_method(subscription, expect):
    if expect is True:
        token = Token.objects.create(user=subscription.subscriber).key
    else:
        token = "fdksal;j"

    value = auth.authtoken_method(token)
    assert bool(value) is expect


@pytest.mark.django_db
@pytest.mark.parametrize("expect", [
    True, False
    ])
def test_authjwt_method(subscription, expect):
    if expect is True:
        payload = jwt_payload_handler(user=subscription.subscriber)
        token = jwt_encode_handler(payload)
    else:
        token = "fdksal;j"

    value = auth.authjwt_method(token)
    assert bool(value) is expect
