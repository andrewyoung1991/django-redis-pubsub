from django.conf import settings

import pytest

from model_mommy import mommy


@pytest.fixture
def subscription(request):
    subscription_ = mommy.make("redis_pubsub.Subscription")

    def fin():
        subscription_.delete()
    request.addfinalizer(fin)
    return subscription_


@pytest.fixture
def subscriber(request):
    subscriber_ = mommy.make(settings.AUTH_USER_MODEL)
    def fin():
        subscriber_.delete()
    request.addfinalizer(fin)
    return subscriber_
