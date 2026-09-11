from django.conf import settings


def global_settings(request):
    return {
        "OIDC_PROVIDER_NAME": getattr(settings, "OIDC_PROVIDER_NAME", ""),
        "DOCS_URL": request.tenant.docs_url,
        "SUPPORT_TICKET_URL": getattr(settings, "SUPPORT_TICKET_URL", ""),
        "OVE_URL": getattr(settings, "OVE_URL", ""),
    }
