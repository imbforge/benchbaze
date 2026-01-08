from django.conf import settings
from django.db import models

from common.actions import export_tsv_action, export_xlsx_action
from common.models import (
    DocFileMixin,
    DownloadFileNameMixin,
    HistoryFieldMixin,
    SaveWithoutHistoricalRecord,
)

from ..shared.models import (
    HistoryDocFieldMixin,
    InfoSheetMaxSizeMixin,
    OwnershipFieldsMixin,
)

FILE_SIZE_LIMIT_MB = getattr(settings, "FILE_SIZE_LIMIT_MB", 2)


class AntibodyDoc(DocFileMixin):
    class Meta:
        verbose_name = "antibody document"

    # Fields
    antibody = models.ForeignKey("Antibody", on_delete=models.PROTECT)

    # Static properties
    _inline_foreignkey_fieldname = "antibody"
    _mixin_props = {
        "destination_dir": "collection/antibodydoc/",
        "file_prefix": "abDoc",
        "parent_field_name": "antibody",
    }


class Antibody(
    SaveWithoutHistoricalRecord,
    DownloadFileNameMixin,
    InfoSheetMaxSizeMixin,
    HistoryDocFieldMixin,
    HistoryFieldMixin,
    OwnershipFieldsMixin,
    models.Model,
):
    class Meta:
        verbose_name = "antibody"
        verbose_name_plural = "antibodies"

    _model_upload_to = "collection/antibody/"

    # Fields
    name = models.CharField("name", max_length=255, blank=False)
    species_isotype = models.CharField("species/isotype", max_length=255, blank=False)
    clone = models.CharField("clone", max_length=255, blank=True)
    received_from = models.CharField("received from", max_length=255, blank=True)
    catalogue_number = models.CharField("catalogue number", max_length=255, blank=True)
    l_ocation = models.CharField("location", max_length=255, blank=True)
    a_pplication = models.CharField("application", max_length=255, blank=True)
    description_comment = models.TextField("description/comments", blank=True)
    info_sheet = models.FileField(
        "info sheet",
        help_text=f"only .pdf files, max. {FILE_SIZE_LIMIT_MB} MB",
        upload_to=_model_upload_to,
        blank=True,
        null=True,
    )
    availability = models.BooleanField("available?", default=True, null=False)

    # Static properties
    _model_abbreviation = "ab"
    _show_in_frontend = True
    _is_guarded_model = False
    _history_array_fields = {
        "history_documents": AntibodyDoc,
    }
    _representation_field = "name"
    _list_display_links = ["id"]
    _search_fields = [
        "id",
        "name",
    ]
    _export_field_names = [
        "id",
        "name",
        "species_isotype",
        "clone",
        "received_from",
        "catalogue_number",
        "l_ocation",
        "a_pplication",
        "description_comment",
        "info_sheet",
        "availability",
    ]
    _export_custom_fields = {
        "fields": dict(),
        "dehydrate_methods": {
            "availability": lambda obj: "Yes" if obj.availability else "No"
        },
    }
    _actions = [
        export_xlsx_action,
        export_tsv_action,
    ]
    _list_display_frozen = _search_fields
    _list_display = [
        "catalogue_number",
        "received_from",
        "species_isotype",
        "clone",
        "l_ocation",
        "info_sheet_formatted",
        "availability",
    ]
    _obj_specific_fields = [
        "name",
        "species_isotype",
        "clone",
        "received_from",
        "catalogue_number",
        "l_ocation",
        "a_pplication",
        "description_comment",
        "info_sheet",
        "availability",
    ]
    _obj_unmodifiable_fields = [
        "created_date_time",
        "last_changed_date_time",
    ]
    _add_view_fieldsets = [
        [
            None,
            {"fields": _obj_specific_fields},
        ],
    ]
    _change_view_fieldsets = [
        [
            None,
            {"fields": _obj_specific_fields + _obj_unmodifiable_fields},
        ],
    ]
    _clone_ignore_fields = ["info_sheet"]

    # Methods
    def __str__(self):
        return f"{self.id} - {self.name}"
