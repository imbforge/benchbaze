from django.core.exceptions import FieldDoesNotExist
from djangoql.schema import DjangoQLSchema, RelationField, StrField

from common.search import (
    SearchFieldUserLastnameWithOptions,
    SearchFieldUserUsernameWithOptions,
)

from ..storage.models import Location, LocationItem


class FieldLocation(RelationField):
    name = "location"
    related_model = LocationItem
    suggest_options = True

    def __init__(self, model):
        super().__init__(model, self.name, self.related_model)

    def get_lookup_name(self):
        return "locations"


class FieldLocationField(StrField):
    def __init__(self, field_name, lookup_name=None, suggest_options=False, model=None):
        """Search field for a specific field of the LocationItem model"""
        self.name = field_name
        self.lookup_name = lookup_name or field_name
        self.suggest_options = suggest_options
        self.model = model
        super().__init__()

    def _field_choices(self):
        """Get field choices for the specified field of the Location model, if it has any"""

        field_name = self.lookup_name.replace("location__", "")
        try:
            return Location._meta.get_field(field_name).choices
        except (FieldDoesNotExist, AttributeError):
            pass
        return []

    def get_lookup_name(self):
        return self.lookup_name

    def get_lookup(self, path, operator, value):
        """Override parent's method to replace 'location' with 'locations' in path"""

        path = [p if p != "location" else "locations" for p in path]
        return super().get_lookup(path, operator, value)

    def get_options(self, search):
        """Suggestions based on the search input, looking in the specified field of related LocationItem records"""

        options = []

        # Search through related Location model
        if self.lookup_name.startswith("location__"):
            locations = getattr(self.model, "get_model_locations", lambda: [])()
            if locations:
                field_name = self.lookup_name.replace("location__", "")
                # Apply search filtering if search term is provided
                lookup = {}
                if search:
                    lookup["%s__icontains" % self.name] = search
                # Filter locations based on the search term in the specified field
                options = (
                    locations.filter(**lookup)
                    .values_list(field_name, flat=True)
                    .order_by(field_name)
                    .distinct()
                )
                # If the field has choices defined, filter options to include only
                # those choices and replace option values with their display names
                field_choices = dict(self._field_choices())
                if field_choices:
                    options = [
                        field_choices[option]
                        for option in options
                        if option in field_choices
                    ]
        # Search through related LocationItem model
        else:
            lookup = {}
            if search:
                lookup["%s__icontains" % self.name] = search
            options = (
                self.model.objects.filter(**lookup)
                .order_by(self.lookup_name)
                .values_list(self.lookup_name, flat=True)
                .distinct()
            )

        return [str(option) for option in options]


class CollectionQLSchema(DjangoQLSchema):
    """Customize search functionality for Collection models"""

    def get_fields(self, model):
        """Define fields that can be searched"""

        # Replace 'locations' with FieldLocation -> location
        fields = [
            FieldLocation(model=self.current_model) if f == "locations" else f
            for f in self.fields
        ]

        if model == self.current_model:
            return fields
        elif model.__name__ == "User":
            return [
                SearchFieldUserUsernameWithOptions(
                    model_user_options=self.current_model
                ),
                SearchFieldUserLastnameWithOptions(
                    model_user_options=self.current_model
                ),
            ]
        elif model.__name__ == "LocationItem":
            return [
                FieldLocationField(
                    "name",
                    "location__name__name",
                    suggest_options=True,
                    model=self.current_model,
                ),
                FieldLocationField(
                    "storage_temp",
                    "location__storage_temperature",
                    suggest_options=True,
                    model=self.current_model,
                ),
                FieldLocationField(
                    "storage_format",
                    "location__storage_format",
                    suggest_options=True,
                    model=self.current_model,
                ),
                FieldLocationField(
                    "storage_level",
                    "location__level",
                    suggest_options=True,
                    model=self.current_model,
                ),
                FieldLocationField(
                    "box",
                    "locations__box",
                    suggest_options=True,
                    model=self.current_model,
                ),
                FieldLocationField(
                    "coordinate",
                    "locations__coordinate",
                    model=self.current_model,
                ),
            ]

        return super().get_fields(model)
