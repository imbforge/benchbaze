from functools import reduce

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db.models.functions import Collate
from djangoql.schema import StrField

User = get_user_model()


class SearchFieldWithOptions(StrField):
    """Search field with unlimited options"""

    suggest_options = True
    limit_options = None

    def get_options(self, search):
        filter_search = {f"{self.model_fieldname}__icontains": search}

        if self.limit_options:
            if len(search) < 3:
                return ["Type 3 or more characters to see suggestions"]
            return (
                self.model.objects.filter(**filter_search)
                .distinct()[: self.limit_options]
                .values_list(
                    self.name
                    if self.name == self.model_fieldname
                    else self.model_fieldname,
                    flat=True,
                )
            )

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
