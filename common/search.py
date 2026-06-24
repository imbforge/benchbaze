from django.contrib.auth import get_user_model
from django.db.models.functions import Collate
from djangoql.schema import StrField

User = get_user_model()


def check_search_length(search):
    """Check if the search string is less than 3 characters long and
    return a default message if so."""
    if len(search) < 3:
        return ["Type 3 or more characters to see suggestions"]
    return None


class SearchFieldWithOptions(StrField):
    """Search field with a certain number of options"""

    def __init__(self, limit_options=20, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.limit_options = limit_options

    suggest_options = True

    def get_options(self, search):
        filter_search = {f"{self.model_fieldname}__icontains": search}

        if self.limit_options:
            if default_option := check_search_length(search):
                return default_option

            option_field = (
                self.name if self.name == self.model_fieldname else self.model_fieldname
            )
            options = list(
                self.model.objects.filter(**filter_search)
                .distinct()
                .order_by(option_field)
                .values_list(option_field, flat=True)[: self.limit_options + 1]
            )

            if len(options) > self.limit_options:
                return options[: self.limit_options] + ["..."]
            return options

        return (
            self.model.objects.filter(**filter_search)
            .order_by(self.model_fieldname)
            .values_list(self.model_fieldname, flat=True)
        )

    def get_lookup_name(self):
        if self.name == self.model_fieldname:
            return self.name
        return f"{self.name}__{self.model_fieldname}"


class SearchFieldUserUsernameWithOptions(StrField):
    """Create a list of unique users' usernames for search"""

    model = User
    name = User.USERNAME_FIELD
    model_user_options = None
    suggest_options = True

    def __init__(self, model_user_options=None, **kwargs):
        self.model_user_options = model_user_options
        super().__init__(**kwargs)

    def get_options(self, search):
        """Removes system users from the list of options,
        distinct() returns only unique values
        sorted in alphabetical order by last name"""

        if self.model_user_options:
            return (
                self.model.objects.annotate(
                    **{f"{self.name}_deterministic": Collate(self.name, "und-x-icu")},
                )
                .filter(
                    **{
                        "id__in": self.model_user_options.objects.all()
                        .values_list("created_by_id", flat=True)
                        .distinct(),
                        f"{self.name}_deterministic__icontains": search,
                    }
                )
                .exclude(is_system_user=True)
                .distinct()
                .order_by("last_name")
                .values_list(self.name, flat=True)
            )
        else:
            return (
                self.model.objects.annotate(
                    **{f"{self.name}_deterministic": Collate(self.name, "und-x-icu")},
                )
                .filter(**{f"{self.name}_deterministic__icontains": search})
                .exclude(is_system_user=True)
                .distinct()
                .order_by("last_name")
                .values_list(self.name, flat=True)
            )


class SearchFieldUserLastnameWithOptions(StrField):
    """Create a list of unique user's last names for search"""

    model = User
    name = "last_name"
    model_user_options = None
    suggest_options = True
    id_list = []

    def __init__(self, model_user_options=None, **kwargs):
        self.model_user_options = model_user_options
        super().__init__(**kwargs)

    def get_options(self, search):
        """Removes system users from the list of options,
        distinct() returns only unique values sorted in
        alphabetical order"""

        if self.model_user_options:
            return (
                self.model.objects.filter(
                    id__in=self.model_user_options.objects.all()
                    .values_list("created_by_id", flat=True)
                    .distinct(),
                    last_name__icontains=search,
                )
                .exclude(is_system_user=True)
                .distinct()
                .order_by(self.name)
                .values_list(self.name, flat=True)
            )
        else:
            return (
                self.model.objects.filter(last_name__icontains=search)
                .exclude(is_system_user=True)
                .distinct()
                .order_by(self.name)
                .values_list(self.name, flat=True)
            )
