from django.utils.safestring import mark_safe

from common.admin import (
    AddDocFileInlineMixin,
    DocFileInlineMixin,
    GetParentObjectInlineMixin,
)

from ..sacerevisiaestrain.models import (
    SaCerevisiaeStrainDoc,
    SaCerevisiaeStrainEpisomalPlasmid,
)
from ..shared.admin import (
    AddLocationInline,
    CollectionUserProtectionAdmin,
    CustomGuardedModelAdmin,
    LocationInline,
    SortAutocompleteResultsId,
)
from .forms import SaCerevisiaeStrainAdminForm
from .search import SaCerevisiaeStrainQLSchema


class SaCerevisiaeStrainEpisomalPlasmidInline(GetParentObjectInlineMixin):
    autocomplete_fields = ["plasmid", "formz_projects"]
    model = SaCerevisiaeStrainEpisomalPlasmid
    verbose_name_plural = mark_safe(
        'Episomal plasmids <span style="text-transform:lowercase;">'
        '(highlighted in <span style="color:var(--accent)">yellow</span>, '
        "if present in the stocked strain</span>)"
    )
    verbose_name = "Episomal Plasmid"
    ordering = (
        "-present_in_stocked_strain",
        "id",
    )
    extra = 0
    template = "admin/tabular.html"

    def get_queryset(self, request):
        """Modify to conditionally collapse inline if there is an episomal
        plasmid in the -80 stock"""

        self.classes = ["collapse"]

        parent_object = self.get_parent_object(request)
        if parent_object:
            parent_obj_episomal_plasmids = parent_object.episomal_plasmids.all()
            if parent_obj_episomal_plasmids.filter(
                sacerevisiaestrainepisomalplasmid__present_in_stocked_strain=True
            ):
                self.classes = []
        else:
            self.classes = []
        return super().get_queryset(request)


class SaCerevisiaeStrainDocInline(DocFileInlineMixin):
    """Inline to view existing Sa. cerevisiae strain documents"""

    model = SaCerevisiaeStrainDoc


class SaCerevisiaeStrainAddDocInline(AddDocFileInlineMixin):
    """Inline to add new Sa. cerevisiae strain documents"""

    model = SaCerevisiaeStrainDoc


class SaCerevisiaeStrainAdmin(
    SortAutocompleteResultsId,
    CustomGuardedModelAdmin,
    CollectionUserProtectionAdmin,
):
    djangoql_schema = SaCerevisiaeStrainQLSchema
    form = SaCerevisiaeStrainAdminForm
    inlines = [
        SaCerevisiaeStrainEpisomalPlasmidInline,
        LocationInline,
        AddLocationInline,
        SaCerevisiaeStrainDocInline,
        SaCerevisiaeStrainAddDocInline,
    ]
    form = SaCerevisiaeStrainAdminForm

    def save_related(self, request, form, formsets, change):
        obj, history_obj = super().save_related(
            request,
            form,
            formsets,
            change,
        )

        plasmid_id_list = (
            obj.integrated_plasmids.all()
            | obj.cassette_plasmids.all()
            | obj.episomal_plasmids.filter(
                sacerevisiaestrainepisomalplasmid__present_in_stocked_strain=True
            )
        )
        if plasmid_id_list:
            obj.history_all_plasmids_in_stocked_strain = list(
                plasmid_id_list.order_by("id")
                .distinct("id")
                .values_list("id", flat=True)
            )
            obj.save_without_historical_record()

            history_obj.history_all_plasmids_in_stocked_strain = (
                obj.history_all_plasmids_in_stocked_strain
            )
            history_obj.save()

        # Clear non-relevant fields for in-stock episomal plasmids
        for (
            in_stock_episomal_plasmid
        ) in SaCerevisiaeStrainEpisomalPlasmid.objects.filter(
            sacerevisiae_strain__id=form.instance.id
        ).filter(present_in_stocked_strain=True):
            in_stock_episomal_plasmid.formz_projects.clear()
