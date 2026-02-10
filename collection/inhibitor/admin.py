from common.admin import AddDocFileInlineMixin, DocFileInlineMixin

from ..shared.admin import (
    AddLocationInline,
    CollectionSimpleAdmin,
    LocationInline,
)
from .models import InhibitorDoc
from .search import InhibitorQLSchema


class InhibitorDocInline(DocFileInlineMixin):
    """Inline to view existing Inhibitor documents"""

    model = InhibitorDoc


class InhibitorAddDocInline(AddDocFileInlineMixin):
    """Inline to add new Inhibitor documents"""

    model = InhibitorDoc


class InhibitorAdmin(CollectionSimpleAdmin):
    djangoql_schema = InhibitorQLSchema
    actions = [export_inhibitor]
    search_fields = ["id", "name"]
    inlines = [InhibitorDocInline, InhibitorAddDocInline]
    clone_ignore_fields = ["info_sheet"]
    obj_specific_fields = [
        "name",
        "other_names",
        "target",
        "received_from",
        "catalogue_number",
        "l_ocation",
        "ic50",
        "amount",
        "stock_solution",
        "description_comment",
        "info_sheet",
    ]
    obj_unmodifiable_fields = [
        "created_date_time",
        "last_changed_date_time",
    ]
    add_view_fieldsets = [
        [
            None,
            {"fields": obj_specific_fields},
        ],
    ]
    change_view_fieldsets = [
        [
            None,
            {"fields": obj_specific_fields + obj_unmodifiable_fields},
        ],
    ]
