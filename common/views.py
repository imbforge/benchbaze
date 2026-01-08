from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

User = get_user_model()


DOCS_URL = getattr(settings, "DOCS_URL", "")
IMPRESSUM_URL = getattr(settings, "IMPRESSUM_URL", "")
DATA_PROTECTION_URL = getattr(settings, "DATA_PROTECTION_URL", "")
OIDC_ENABLE = getattr(settings, "OIDC_ENABLE", False)
OIDC_PROVIDER_NAME = getattr(settings, "OIDC_PROVIDER_NAME", "")
LAB_NAME = getattr(settings, "LAB_NAME", "")
LOGIN_REDIRECT_URL = getattr(settings, "LOGIN_REDIRECT_URL", "")
LOGOUT_REDIRECT_URL = getattr(settings, "LOGOUT_REDIRECT_URL", "")


class OwnLoginView(LoginView):
    extra_context = {
        "oidc_enable": OIDC_ENABLE,
        "oidc_provider_name": OIDC_PROVIDER_NAME,
        "lab_name": LAB_NAME,
        "impressum_url": IMPRESSUM_URL,
        "data_protection_url": DATA_PROTECTION_URL,
    }


class OwnLogoutView(LogoutView):
    extra_context = {
        "lab_name": LAB_NAME,
        "impressum_url": IMPRESSUM_URL,
        "data_protection_url": DATA_PROTECTION_URL,
    }

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if "benchbaze-api" in [h.lower() for h in request.headers]:
            return JsonResponse({"success": True})
        return response


class SettingsApiView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request):
        settings = {
            "lab_name": LAB_NAME,
            "login_url": LOGIN_REDIRECT_URL,
            "logout_url": LOGOUT_REDIRECT_URL,
            "docs_url": DOCS_URL,
            "impressum_url": IMPRESSUM_URL,
            "data_protection_url": DATA_PROTECTION_URL,
        }
        return Response(settings)
