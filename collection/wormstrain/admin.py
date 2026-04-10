from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.html import format_html

from common.admin import (
    AddDocFileInlineMixin,
    DocFileInlineMixin,
)

from ..plasmid.admin import PlasmidAdmin
from ..shared.admin import (
    AddLocationInline,
    CollectionUserProtectionAdmin,
    CustomGuardedModelAdmin,
    LocationInline,
    SortAutocompleteResultsId,
    create_map_preview,
)
from .forms import WormStrainAlleleAdminForm
from .models import (
    WormStrainAlleleDoc,
    WormStrainDoc,
    WormStrainGenotypingAssay,
)
from .search import WormStrainAlleleQLSchema, WormStrainQLSchema

User = get_user_model()
MEDIA_ROOT = settings.MEDIA_ROOT
LAB_ABBREVIATION_FOR_FILES = getattr(settings, "LAB_ABBREVIATION_FOR_FILES", "")
WORM_ALLELE_LAB_ID_DEFAULT = getattr(settings, "WORM_ALLELE_LAB_ID_DEFAULT", "")
WORM_STRAIN_REGEX = getattr(settings, "WORM_STRAIN_REGEX", r"")
WORM_STRAIN_LAB_ID_DEFAULT = getattr(settings, "WORM_STRAIN_LAB_ID_DEFAULT", "")


class WormStrainGenotypingAssayInline(admin.TabularInline):
    """Inline to view existing worm genotyping assay"""

    model = WormStrainGenotypingAssay
    verbose_name = "genotyping assay"
    verbose_name_plural = "existing genotyping assays"
    extra = 0
    readonly_fields = ["locus_allele", "oligos"]

    def has_add_permission(self, request, obj):
        return False


class AddWormStrainGenotypingAssayInline(admin.TabularInline):
    """Inline to add new worm genotyping assays"""

    model = WormStrainGenotypingAssay
    verbose_name = "genotyping assay"
    verbose_name_plural = "new genotyping assays"
    extra = 0
    autocomplete_fields = ["oligos"]

    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return self.model.objects.none()


class WormStrainDocInline(DocFileInlineMixin):
    """Inline to view existing worm strain documents"""

    model = WormStrainDoc


class WormStrainAddDocInline(AddDocFileInlineMixin):
    """Inline to add new worm strain documents"""

    model = WormStrainDoc


class WormStrainAdmin(
    SortAutocompleteResultsId,
    CustomGuardedModelAdmin,
    CollectionUserProtectionAdmin,
):
    djangoql_schema = WormStrainQLSchema
    inlines = [
        WormStrainGenotypingAssayInline,
        AddWormStrainGenotypingAssayInline,
        LocationInline,
        AddLocationInline,
        WormStrainDocInline,
        WormStrainAddDocInline,
    ]
    change_form_template = "admin/collection/change_form.html"

    @admin.display(description="Stocked", boolean=True)
    def stocked_formatted(self, instance):
        return instance.stocked_formatted()

    def save_related(self, request, form, formsets, change):
        obj, history_obj = super().save_related(request, form, formsets, change)

        obj.history_genotyping_oligos = (
            sorted(
                list(
                    set(
                        obj.wormstraingenotypingassay_set.all().values_list(
                            "oligos", flat=True
                        )
                    )
                )
            )
            if obj.wormstraingenotypingassay_set.exists()
            else []
        )
        obj.save_without_historical_record()

        history_obj.history_genotyping_oligos = obj.history_genotyping_oligos
        history_obj.save()

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)
        filtered_inline_instances = []

        # New objects
        if not obj:
            for inline in inline_instances:
                if inline.verbose_name_plural == "existing genotyping assays":
                    filtered_inline_instances.append(inline)
                else:
                    if not request.user.is_guest:
                        filtered_inline_instances.append(inline)

        # Existing objects
        else:
            for inline in inline_instances:
                # Always show existing docs
                if inline.verbose_name_plural == "Existing docs":
                    filtered_inline_instances.append(inline)
                else:
                    # Do not allow guests to add docs, ever
                    if not request.user.is_guest:
                        filtered_inline_instances.append(inline)

        return filtered_inline_instances

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # Try to get the latest strain ID from name
        if (
            not obj
            and WORM_STRAIN_REGEX
            and WORM_STRAIN_LAB_ID_DEFAULT
            and "name" in form.base_fields
        ):
            strain_greatest_id = (
                self.model.objects.filter(name__iregex=WORM_STRAIN_REGEX)
                .extra(
                    select={
                        "strain_id": f"CAST((REGEXP_MATCH(name, '{WORM_STRAIN_REGEX}'))[1] AS INTEGER)"
                    }
                )
                .order_by("-strain_id")
                .first()
            )
            if strain_greatest_id:
                form.base_fields[
                    "name"
                ].initial = (
                    f"{WORM_STRAIN_LAB_ID_DEFAULT}{strain_greatest_id.strain_id + 1}"
                )
        return form

    def add_view(self, request, form_url="", extra_context=None):
        obj_unmodifiable_fields = self.obj_unmodifiable_fields.copy()
        add_view_main_fields = self.add_view_fieldsets[0][1]["fields"].copy()
        if request.user.is_elevated_user:
            obj_unmodifiable_fields = [
                x for x in obj_unmodifiable_fields if x != "created_by"
            ]
            add_view_main_fields = (
                add_view_main_fields + ["created_by"]
                if "created_by" not in add_view_main_fields
                else add_view_main_fields
            )
        else:
            obj_unmodifiable_fields = set(obj_unmodifiable_fields)
            obj_unmodifiable_fields.add("created_by")
            obj_unmodifiable_fields = list(obj_unmodifiable_fields)
            add_view_main_fields = [
                x for x in add_view_main_fields if x != "created_by"
            ]

        self.obj_unmodifiable_fields = obj_unmodifiable_fields
        self.add_view_fieldsets[0][1]["fields"] = add_view_main_fields

        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        obj_unmodifiable_fields = set(self.obj_unmodifiable_fields)
        obj_unmodifiable_fields.add("created_by")
        self.obj_unmodifiable_fields = list(list(obj_unmodifiable_fields))

        return super().change_view(request, object_id, form_url, extra_context)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Exclude certain users from the 'Created by' field in the form
        if db_field.name == "created_by":
            if request.user.is_elevated_user:
                kwargs["queryset"] = User.objects.exclude(is_system_user=True).order_by(
                    "last_name"
                )
            # kwargs["initial"] = request.user.id # disable this for now

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class WormStrainAlleleDocInline(DocFileInlineMixin):
    """Inline to view existing worm strain documents"""

    model = WormStrainAlleleDoc


class WormStrainAlleleAddDocInline(AddDocFileInlineMixin):
    """Inline to add new worm strain documents"""

    model = WormStrainAlleleDoc


class WormStrainAlleleAdmin(PlasmidAdmin):
    djangoql_schema = WormStrainAlleleQLSchema
    form = WormStrainAlleleAdminForm
    inlines = [WormStrainAlleleDocInline, WormStrainAlleleAddDocInline]
    allele_type = ""

    add_form_template = "admin/collection/wormstrainallele/add_form.html"
    change_form_template = "admin/collection/wormstrainallele/change_form.html"

    def has_module_permission(self, request):
        return False

    def _save_model_approval(self, request, obj, new_obj):
        return None

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        allele_type = ""
        required_fields = []

        if (obj and obj.typ_e == "t") or self.allele_type == "t":
            allele_type = "t"
            required_fields = ["transgene", "transgene_position", "transgene_plasmids"]
        elif (obj and obj.typ_e == "m") or self.allele_type == "m":
            allele_type = "m"
            required_fields = ["mutation", "mutation_type", "mutation_position"]

        if "typ_e" in form.base_fields:
            form.base_fields["typ_e"].initial = allele_type
            form.base_fields["typ_e"].disabled = True
        if self.can_change:
            [setattr(form.base_fields[f], "required", True) for f in required_fields]

        if (
            not obj
            and WORM_ALLELE_LAB_ID_DEFAULT
            and "lab_identifier" in form.base_fields
        ):
            form.base_fields["lab_identifier"].initial = WORM_ALLELE_LAB_ID_DEFAULT

        return form

    def add_view(self, request, form_url="", extra_context=None):
        fields = self.obj_specific_fields.copy()
        self.allele_type = request.GET.get("allele_type")
        obj_unmodifiable_fields = self.obj_unmodifiable_fields.copy()

        if request.user.is_elevated_user:
            obj_unmodifiable_fields = [
                x for x in obj_unmodifiable_fields if x != "created_by"
            ]
            fields = fields + ["created_by"] if "created_by" not in fields else fields
        else:
            obj_unmodifiable_fields = set(obj_unmodifiable_fields)
            obj_unmodifiable_fields.add("created_by")
            obj_unmodifiable_fields = list(obj_unmodifiable_fields)
            fields = [x for x in fields if x != "created_by"]

        self.obj_unmodifiable_fields = obj_unmodifiable_fields

        if self.allele_type == "t":
            fields = [f for f in fields if not f.startswith("mutation")]
        elif self.allele_type == "m":
            fields = [f for f in fields if not f.startswith("transgene")]
        else:
            fields = []

        self.add_view_fieldsets = [
            [
                None,
                {"fields": fields},
            ],
        ]

        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        obj = self.model.objects.get(pk=object_id)
        fields = self.obj_specific_fields.copy()

        if obj.typ_e == "t":
            fields = [f for f in fields if not f.startswith("mutation")]
        elif obj.typ_e == "m":
            fields = [f for f in fields if not f.startswith("transgene")]

        obj_unmodifiable_fields = set(self.obj_unmodifiable_fields)
        obj_unmodifiable_fields.add("created_by")
        self.obj_unmodifiable_fields = list(list(obj_unmodifiable_fields))

        self.change_view_fieldsets = [
            [
                None,
                {"fields": fields + self.obj_unmodifiable_fields},
            ],
        ]

        return super().change_view(request, object_id, form_url, extra_context)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Exclude certain users from the 'Created by' field in the form
        if db_field.name == "created_by":
            if request.user.is_elevated_user:
                kwargs["queryset"] = User.objects.exclude(is_system_user=True).order_by(
                    "last_name"
                )
            # kwargs["initial"] = request.user.id # disable this for now

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Description")
    def description(self, instance):
        return format_html(
            "<b>{}{}</b> - {}", instance.lab_identifier, instance.id, instance.name
        )
