import pytest
from model_mommy import mommy

from testapp.models import Message


@pytest.mark.django_db
def test_undelivered(subscription):
    message = mommy.make(Message, channel=subscription.channel)
    undelivered = Message.objects.get_undelivered()
    assert len(undelivered), "this message should not have been delivered."
    assert (subscription.subscriber, message) in undelivered
