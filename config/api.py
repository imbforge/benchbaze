from rest_framework import routers

from common.viewsets import (
    LayoutFrontendViewSet,
    ModelViewSet,
    NavigationViewSet,
    UserViewSet,
)

router = routers.DefaultRouter()
router.register(r"auth/user", UserViewSet, basename="user")
router.register(r"layout", LayoutFrontendViewSet, basename="layout")
router.register(r"navigation", NavigationViewSet, basename="navigation")
router.register(
    r"^(?P<app_label>[^/.]+)/(?P<model>[^/.]+)", ModelViewSet, basename="models"
)
