from django.contrib.auth.decorators import login_required
from django.urls import path

from .views import convert_any_to_ove_json, create_map_file

urlpatterns = [
    path(
        "create_map_file/",
        login_required(create_map_file),
        name="create_map_file",
    ),
    path(
        "convert_any_to_ove_json/",
        login_required(convert_any_to_ove_json),
        name="convert_any_to_ove_json",
    ),
]
