from rest_framework import routers

from common.viewsets import (
    LayoutFrontendViewSet,
    ModelViewSet,
    NavigationListViewSet,
    NavigationViewSet,
    UserViewSet,
)

router = routers.DefaultRouter()
router.register(r"common/user", UserViewSet, basename="user")
router.register(r"layout", LayoutFrontendViewSet, basename="layout")
router.register(r"navigation", NavigationListViewSet, basename="navigation-tree")
router.register(
    r"navigation/(?P<app_label>[^/.]+)/(?P<model>[^/.]+)",
    NavigationViewSet,
    basename="navigation",
)
router.register(
    r"(?P<app_label>[^/.]+)/(?P<model>[^/.]+)", ModelViewSet, basename="models"
)
