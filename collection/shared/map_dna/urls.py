from django.contrib.auth.decorators import login_required
from django.urls import path

from .views import create_map_file, map_dna_detect_features, convert_snapgene_to_genbank

urlpatterns = [
    path(
        "detect_features/",
        login_required(map_dna_detect_features),
        name="map_dna_detect_features",
    ),
    path(
        "create_map_file/",
        login_required(create_map_file),
        name="create_map_file",
    ),
    path(
        "convert_snapgene_to_genbank/",
        login_required(convert_snapgene_to_genbank),
        name="convert_snapgene_to_genbank",
    ),
]
