from django.contrib.auth import get_user_model
from django_better_admin_arrayfield.admin.mixins import DynamicArrayMixin

from common.admin import (
    AddDocFileInlineMixin,
    DocFileInlineMixin,
)
from formz.models import Species

from ..shared.admin import (
    CollectionSimpleAdmin,
)
from .models import SiRnaDoc
from .search import SiRnaQLSchema

User = get_user_model()


class InhibitorDocInline(DocFileInlineMixin):
    """Inline to view existing Inhibitor documents"""

    model = SiRnaDoc


class InhibitorAddDocInline(AddDocFileInlineMixin):
    """Inline to add new Inhibitor documents"""

    model = SiRnaDoc


class SiRnaAdmin(
    DynamicArrayMixin,
    CollectionSimpleAdmin,
):
    djangoql_schema = SiRnaQLSchema
    inlines = [InhibitorDocInline, InhibitorAddDocInline]

    def add_view(self, request, form_url="", extra_context=None):
        if "created_by" in self.obj_unmodifiable_fields:
            self.obj_unmodifiable_fields.remove("created_by")

        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        if "created_by" not in self.obj_unmodifiable_fields:
            self.obj_unmodifiable_fields = self.obj_unmodifiable_fields + ["created_by"]

        return super().change_view(request, object_id, form_url, extra_context)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        try:
            request.resolver_match.args[0]
        except Exception:
            # Exclude certain users from the 'Created by' field
            if db_field.name == "created_by":
                if request.user.is_elevated_user:
                    kwargs["queryset"] = User.objects.exclude(
                        is_system_user=True
                    ).order_by("last_name")
                kwargs["initial"] = request.user.id

            # Only show species that have been set to be shown in cell line collection
            if db_field.name == "species":
                kwargs["queryset"] = Species.objects.filter(
                    show_in_cell_line_collection=True
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
