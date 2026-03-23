from django import forms
from django.conf import settings

from ..shared.admin import (
    OptionalChoiceField,
)

WORM_ALLELE_LAB_IDS = getattr(settings, "WORM_ALLELE_LAB_IDS", [])


class WormStrainAlleleAdminForm(forms.ModelForm):
    if WORM_ALLELE_LAB_IDS:
        lab_identifier = OptionalChoiceField(
            choices=WORM_ALLELE_LAB_IDS,
        )
