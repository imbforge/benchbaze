from django.apps import AppConfig
from django.core.signals import request_finished
from django.contrib.auth import get_user_model


class OwnAdminConfig(AppConfig):
    name = "common"

    def ready(self):
        from .signals import user_login_failed_receiver

        User = get_user_model()
        request_finished.connect(user_login_failed_receiver, sender=User)
