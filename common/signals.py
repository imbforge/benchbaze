import logging
import socket

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver

LOGGER = logging.getLogger("logfile")

FAIL2BAN_ENABLE = getattr(settings, "FAIL2BAN_ENABLE", False)
FAIL2BAN_BAN_TIME_MIN = getattr(settings, "FAIL2BAN_BAN_TIME_MIN", 10)
FAIL2BAN_NUM_ATTEMPTS = getattr(settings, "FAIL2BAN_NUM_ATTEMPTS", 3)


def get_client_ip(request):
    # Stolen from https://stackoverflow.com/questions/4581789/how-do-i-get-user-ip-address-in-django
    # and amended
    x_forwarded_for = request.headers.get("x-forwarded-for")
    ip = "N/A"
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        remote_address = request.META.get("REMOTE_ADDR")
        if remote_address:
            ip = remote_address
    return ip


@receiver(user_login_failed)
def user_login_failed_receiver(sender, credentials, request, **kwargs):
    ip = get_client_ip(request)
    try:
        rev_lookup = socket.getnameinfo((ip, 0), 0)[0]
    except Exception:
        rev_lookup = "none"
    if FAIL2BAN_ENABLE:
        messages.warning(
            request,
            "⚠️ You will be banned from accessing the site "
            f"for {FAIL2BAN_BAN_TIME_MIN} min after "
            f"{FAIL2BAN_NUM_ATTEMPTS} failed login "
            "attempts. ⚠️",
        )
    LOGGER.warning(
        "Failed login attempt, username: "
        f"{credentials.get('username')}, "
        f"DNS lookup: {rev_lookup}, "
        f"ip: {ip}"
    )

    # fail2ban can be used to monitor these log entries
    # datepattern = ^\[WARNING\]\ \[%%d/%%b/%%Y %%H:%%M:%%S\]
    # failregex = Failed login attempt.*, ip: <HOST>
