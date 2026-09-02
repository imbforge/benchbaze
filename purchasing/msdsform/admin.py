import os

from django.contrib import admin
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.safestring import mark_safe
from djangoql.admin import DjangoQLSearchMixin

from .forms import MsdsFormForm
from .search import MsdsFormQLSchema


class MsdsFormAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    list_display = ("id", "pretty_file_name", "view_file_link")
    list_per_page = 25
    ordering = ["label"]
    djangoql_schema = MsdsFormQLSchema
    djangoql_completion_enabled_by_default = False
    search_fields = ["id", "label"]
    form = MsdsFormForm

    @admin.display(description="File name", ordering="label")
    def pretty_file_name(self, instance):
        """Custom file name"""
        return instance.file_name_description

    @admin.display(description="")
    def view_file_link(self, instance):
        """Shows the url of a MSDS form as a HTML <a> tag with text View"""
        return mark_safe(
            '<a class="magnific-popup-iframe-pdflink" href="{}">{}</a>'.format(
                instance.name.url, "View"
            )
        )

    def save_model(self, request, obj, form, change):
        rename = False

        if obj.pk is None:
            rename = True
            obj.label = os.path.basename(obj.name.name)
            obj.save()

        saved_obj = self.model.objects.get(pk=obj.pk)

        # Rename file, if necessary
        if rename or obj.name.name != saved_obj.name.name:
            obj.save()
            obj.label = os.path.basename(obj.name.name)
            storage = obj.name.storage
            old_name = obj.name.name
            _, ext = os.path.splitext(old_name)
            now = timezone.now().strftime("%Y%m%d_%H%M%S_%f")
            new_storage_name = os.path.join(
                self.model._model_upload_to,
                f"msds{request.tenant.lab_abbreviation_for_files}{obj.id}_"
                f"{now}{ext.lower()}",
            )

            if old_name != new_storage_name:
                with storage.open(old_name, "rb") as f:
                    content = ContentFile(f.read())

                saved_path = storage.save(new_storage_name, content)
                obj.name.name = saved_path
                storage.delete(old_name)

        return super().save_model(request, obj, form, change)

    def add_view(self, request, extra_context=None):
        self.fields = [
            "name",
        ]
        return super().add_view(request)

    def change_view(self, request, object_id, extra_context=None):
        self.fields = ["name", "label"]
        return super().change_view(request, object_id)

    def get_readonly_fields(self, request, obj):
        if obj:
            return [
                "label",
            ]
        else:
            return []
