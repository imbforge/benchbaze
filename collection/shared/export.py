from import_export import resources
from import_export.fields import Field


class LocationExportMixin(resources.ModelResource):
    locations = Field()

    def dehydrate_locations(self, obj):
        return "; ".join(
            str(location.minimal_str)
            for location in obj.locations.all().order_by("location__level")
        )


class CollectionExportMixin(LocationExportMixin):
    pass
