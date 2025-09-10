import itertools
import os

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.forms import ValidationError
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

FILE_SIZE_LIMIT_MB = getattr(settings, "FILE_SIZE_LIMIT_MB", 2)
OVE_URL = getattr(settings, "OVE_URL", "")
LAB_ABBREVIATION_FOR_FILES = getattr(settings, "LAB_ABBREVIATION_FOR_FILES", "")
MEDIA_URL = settings.MEDIA_URL
MAX_UPLOAD_FILE_SIZE_MB = getattr(settings, "MAX_UPLOAD_FILE_SIZE_MB", 2)
ALLOWED_DOC_FILE_EXTS = getattr(settings, "ALLOWED_DOC_FILE_EXTS", ["pdf"])
LAB_MANAGER_GROUP = getattr(settings, "LAB_MANAGER_GROUP")
GUEST_GROUP = getattr(settings, "GUEST_GROUP")
ORDER_MANAGER_GROUP = getattr(settings, "ORDER_MANAGER_GROUP")
FORMZ_MANAGER_GROUP = getattr(settings, "FORMZ_MANAGER_GROUP")
REGULAR_LAB_MEMBER_GROUP = getattr(settings, "REGULAR_LAB_MEMBER_GROUP")
PAST_MEMBER_GROUP = getattr(settings, "PAST_MEMBER_GROUP")
APPROVAL_MANAGER_GROUP = getattr(settings, "APPROVAL_MANAGER_GROUP")


class OwnUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    https://tech.serhatteker.com/post/2020-01/email-as-username-django/
    """

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError(_("The Email must be set"))
        email = self.normalize_email(email)
        extra_fields.setdefault("username", email.split("@")[0].lower())
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    email = models.EmailField(
        _("email address"), db_collation="case_insensitive", unique=True
    )
    is_pi = models.BooleanField("is principal investigator?", default=False)
    oidc_id = models.CharField(
        "OIDC identifier",
        max_length=255,
        null=True,
        unique=True,
        default=None,
        blank=True,
    )
    is_system_user = models.BooleanField("is system user?", default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = OwnUserManager()

    class Meta:
        db_table = "auth_user"

    @property
    def is_lab_manager(self):
        return self.groups.filter(name=LAB_MANAGER_GROUP).exists()

    @property
    def is_guest(self):
        return self.groups.filter(name=GUEST_GROUP).exists()

    @property
    def is_order_manager(self):
        return self.groups.filter(name=ORDER_MANAGER_GROUP).exists()

    @property
    def is_formz_manager(self):
        return self.groups.filter(name=FORMZ_MANAGER_GROUP).exists()

    @property
    def is_approval_manager(self):
        return self.groups.filter(name=APPROVAL_MANAGER_GROUP).exists()

    @property
    def is_regular_lab_member(self):
        return self.groups.filter(name=REGULAR_LAB_MEMBER_GROUP).exists()

    @property
    def is_past_member(self):
        return self.groups.filter(name=PAST_MEMBER_GROUP).exists()

    @property
    def is_elevated_user(self):
        """Defined as a user who is a Lab manager, PI or superuser"""
        return self.is_lab_manager or self.is_pi or self.is_superuser


# For django-guardian, custom AnonymousUser to be created upon
# running migrations
def get_anonymous_user_instance(User):
    return User(username="AnonymousUser", email="AnonymousUser", is_system_user=True)


class SaveWithoutHistoricalRecord:
    def save_without_historical_record(self, *args, **kwargs):
        """Allows inheritance of a method to save an object without
        saving a historical record as described in
        https://django-simple-history.readthedocs.io/en/2.7.2/querying_history.html?highlight=save_without_historical_record
        """

        self.skip_history_when_saving = True
        try:
            ret = self.save(*args, **kwargs)
        finally:
            del self.skip_history_when_saving
        return ret


class RenameFileField:
    def rename_file(self, field_name, new_file_name, upload_to):
        field = getattr(self, field_name)
        file_name = force_str(field)
        name, ext = os.path.splitext(file_name)
        ext = ext.lower()
        final_name = os.path.join(upload_to, f"{new_file_name}{ext}")

        # Essentially, rename file
        if file_name != final_name:
            field.storage.delete(final_name)
            field.storage.save(final_name, field)
            field.close()
            field.storage.delete(file_name)
            setattr(self, field_name, final_name)


class DocFileMixin(models.Model, RenameFileField):
    name = models.FileField(
        "file name", upload_to="temp/", max_length=150, blank=False, null=True
    )
    description = models.CharField("description", max_length=75, blank=False)
    comment = models.CharField("comment", max_length=150, blank=True)

    created_date_time = models.DateTimeField("created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)

    class Meta:
        abstract = True

    # !!! Remember to set ForeignKey to parent model
    # !!! such Plasmid, Oligo, etc.

    # Override the following when inheriting DocFileMixin
    # in the final model
    _mixin_props = {
        "destination_dir": "collection/abc/",
        "file_prefix": "pabc",
        "parent_field_name": "abc",
    }

    @property
    def download_file_name(self):
        parent_field_name = self._mixin_props.get("parent_field_name")
        parent = getattr(self, parent_field_name)
        return (
            f"{parent._model_abbreviation}{LAB_ABBREVIATION_FOR_FILES}{parent}, "
            f"Doc# {self.id}, {self.description.title()}"
        )

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        # Rename a file of any given name to a standard name
        # after the corresponding entry has been created
        super().save(force_insert, force_update, using, update_fields)
        parent = getattr(self, self._mixin_props.get("parent_field_name"))
        new_file_name = (
            f"{self._mixin_props.get('file_prefix')}"
            f"{LAB_ABBREVIATION_FOR_FILES}{parent.id}_"
            f"{timezone.now().strftime('%Y%m%d_%H%M%S_%f')}_{self.id}"
        )
        self.rename_file(
            "name",
            new_file_name,
            self._mixin_props.get("destination_dir"),
        )
        super().save(False, True, using, update_fields)

    def __str__(self):
        return str(self.id)

    def clean(self):
        errors = []
        file_size_limit = MAX_UPLOAD_FILE_SIZE_MB * 1024 * 1024

        if self.name:
            # Check if file is bigger than FILE_SIZE_LIMIT_MB
            if self.name.size > file_size_limit:
                errors.append(
                    ValidationError(
                        f"File too large. Size cannot exceed {MAX_UPLOAD_FILE_SIZE_MB} MB."
                    )
                )

            # Check if file has extension
            try:
                file_ext = self.name.name.split(".")[-1].lower()
            except:
                errors.append(
                    ValidationError(
                        "Invalid file format. File does not have an extension"
                    )
                )
                file_ext = None
            if file_ext and file_ext not in ALLOWED_DOC_FILE_EXTS:
                errors.append(
                    ValidationError(
                        f"Invalid file format. Only {', '.join(ALLOWED_DOC_FILE_EXTS)} files are allowed"
                    )
                )

        if len(errors) > 0:
            raise ValidationError(errors)


class DownloadFileNameMixin:
    @property
    def download_file_name(self):
        return f"{self._model_abbreviation}{LAB_ABBREVIATION_FOR_FILES}{self}"


class HistoryFieldMixin(models.Model):
    """Common history field"""

    _unified_map_field = False

    class Meta:
        abstract = True

    history = HistoricalRecords(inherit=True)

    @property
    def history_changes(self):
        def pairwise(iterable):
            """Create pairs of consecutive items from
            iterable"""

            a, b = itertools.tee(iterable)
            next(b, None)
            return zip(a, b)

        class FieldChange:
            def __init__(
                self,
                field: None = None,
                new_value: str = "",
                old_value: str = "",
            ) -> None:
                self.field = field
                self.new_value = new_value
                self.old_value = old_value

            @staticmethod
            def _pretty_format_value(field, value):
                value_out = value if value else "None"
                field_type = field.get_internal_type()

                if field_type == "FileField":
                    link_text = os.path.basename(value)

                    # # Prettify DNA map field name
                    if getattr(field, "prettify_map_path", False):
                        link_text = os.path.splitext(link_text)[0]
                    value_out = (
                        format_html(
                            "<a href={}>{}</a>",
                            f"{MEDIA_URL}{value}",
                            link_text,
                        )
                        if value
                        else "None"
                    )

                elif field_type == "ForeignKey":
                    field_model = field.remote_field.model
                    value_out = (
                        format_html(
                            '<a target="_blank" href={}>{}</a>',
                            reverse(
                                f"admin:{field_model._meta.app_label}_{field_model._meta.model_name}_change",
                                args=(value,),
                            ),
                            field_model.objects.get(id=value),
                        )
                        if value
                        else "None"
                    )

                elif field_type == "ArrayField":
                    array_field_model = self._history_array_fields.get(field.name, None)
                    if array_field_model:
                        value_out = (
                            ", ".join(
                                map(
                                    str,
                                    array_field_model.objects.filter(id__in=value),
                                )
                            )
                            if value
                            else "None"
                        )
                    else:
                        value_out = ", ".join(value)

                return value_out

            @property
            def new_value_prettified(self):
                return self._pretty_format_value(self.field, self.new_value)

            @property
            def old_value_prettified(self):
                return self._pretty_format_value(self.field, self.old_value)

        class HistoryChange:
            def __init__(
                self,
                timestamp: timezone.datetime = None,
                activity_user: User = None,
                field_changes: list[FieldChange] = [],
            ) -> None:
                self.timestamp = timestamp
                self.activity_user = activity_user
                self.field_changes = field_changes

        # Create data structure for history summary
        history_summary_data = []

        # If more than one history obj, create pairs of history objs
        pairs = pairwise(self.history.all()) if self.history.count() > 1 else []

        for newer_hist_obj, older_hist_obj in pairs:
            # Get differences between history obj pairs and add them to a list
            delta = newer_hist_obj.diff_against(older_hist_obj)

            if delta and getattr(delta, "changes", False):
                changes_list = []

                # Do not show fields that should be ignored
                for change in [
                    c
                    for c in delta.changes
                    if c.field not in self._history_view_ignore_fields
                ]:
                    field = self._meta.get_field(change.field)

                    # Prettify DNA map field name
                    if self._unified_map_field and field.name.startswith("map"):
                        field.verbose_name = field.verbose_name.replace(" (.dna)", "")
                        field.prettify_map_path = True

                    field_change = FieldChange(
                        field=field,
                        new_value=change.new,
                        old_value=change.old,
                    )
                    changes_list.append(field_change)

                if changes_list:
                    history_change = HistoryChange(
                        timestamp=newer_hist_obj.last_changed_date_time,
                        activity_user=User.objects.get(
                            id=int(newer_hist_obj.history_user_id)
                        )
                        if newer_hist_obj.history_user_id
                        else None,
                        field_changes=changes_list,
                    )

                    history_summary_data.append(history_change)

        return history_summary_data


class ZebraLabelFieldsMixin:
    @property
    def zebra_n0jtt_label_content(self):
        return [
            f"<b>{self._model_abbreviation}{LAB_ABBREVIATION_FOR_FILES}{self.id}</b>",
            self.name,
            "",
            "",
            str(self.created_by)[:17],
        ]
