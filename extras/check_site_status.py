import requests
import time
import warnings
from django.core.mail import mail_admins

from django.conf import settings

SITE_TITLE = getattr(settings, "SITE_TITLE", "BenchBaze")
ALLOWED_HOSTS = getattr(settings, "ALLOWED_HOSTS", [])

warnings.filterwarnings(
    "ignore"
)  # Suppress all warnings, including the InsecureRequestWarning caused by verify=False below

time.sleep(
    900
)  # Give some time to the server to ready itself before starting to check if it works

new_status_code = 200  # Set the intial status to that of a working website

while True:
    old_status_code = new_status_code
    new_status_code = requests.get(
        f"https://{ALLOWED_HOSTS[0]}/login/?next=/", verify=False
    ).status_code

    if new_status_code != 200 and old_status_code == 200:
        mail_admins(
            f"{SITE_TITLE} is down", f"{SITE_TITLE} is down", fail_silently=True
        )

    time.sleep(900)
