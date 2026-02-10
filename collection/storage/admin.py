from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe
from django.utils.text import capfirst

from .forms import LocationInlineFormSet
from .models import Location


class LocationInline(admin.TabularInline):
    model = Location
    extra = 1
    template = "admin/tabular.html"
    formset = LocationInlineFormSet
    fields = []
    ordering = ["level"]


class StorageAdmin(admin.ModelAdmin):
    list_display = ("collection_display", "locations_display", "species")
    list_display_links = ("collection_display",)
    list_per_page = 25
    autocomplete_fields = ["species"]
    inlines = [LocationInline]

    @admin.display(description="Collection")
    def collection_display(self, instance):
        return str(instance)

    def has_module_permission(self, request):
        # Show this model on the admin home page only for an elevated user
        return getattr(request.user, "is_elevated_user", False)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Include only collection models that have a locations property"""

        # Include only relevant models from collection app

        if db_field.name == "collection":
            # Get relevant models: 1) from collection, 2) have locations property
            ct_models = [
                (ct, model)
                for ct in ContentType.objects.filter(app_label="collection")
                if (model := ct.model_class()) and hasattr(model, "locations")
            ]
            # Return content type ids sorted by the verbose name of the model
            sorted_model_ids = [
                ct.id
                for ct, _ in sorted(ct_models, key=lambda e: e[1]._meta.verbose_name)
            ]
            # Create queryset of content types with manual ordering
            # to preserve the order of models by verbose name
            kwargs["queryset"] = ContentType.objects.filter(
                id__in=sorted_model_ids
            ).extra(
                select={
                    "manual_order": f"CASE id {' '.join([f'WHEN {id} THEN {i}' for i, id in enumerate(sorted_model_ids)])} END"
                },
                order_by=["manual_order"],
            )

            # Force verbose name as label
            form_field = super().formfield_for_foreignkey(db_field, request, **kwargs)
            form_field.label_from_instance = lambda obj: capfirst(
                obj.model_class()._meta.verbose_name
            )
            return form_field

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Locations")
    def locations_display(self, instance):
        return mark_safe(
            "<br>".join(
                [str(location) for location in instance.locations.order_by("level")]
            )
        )


class LocationNameAdmin(admin.ModelAdmin):
    list_display = ("name",)
    list_per_page = 25

    def has_module_permission(self, request):
        # Hide module from Admin
        return False
