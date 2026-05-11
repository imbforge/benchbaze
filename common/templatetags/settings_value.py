# Plainly stolen from https://stackoverflow.com/questions/433162/can-i-access-constants-in-settings-py-from-templates-in-django

from django import template
from django.conf import settings

register = template.Library()


# settings value
@register.simple_tag
def settings_value(name):
    # return getattr(settings, name, "")
    if name in {
        "OIDC_PROVIDER_NAME",
        "DOCS_URL",
        "SUPPORT_TICKET_URL",
        "OVE_URL",
    }:
        return getattr(settings, name, "")
    return ""
