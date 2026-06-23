from django.contrib.admin.widgets import AdminFileWidget
from django.contrib.contenttypes.forms import BaseGenericInlineFormSet
from django.forms import ValidationError
from django.utils.html import format_html


class PersistentClearableFileInput(AdminFileWidget):
    """A ClearableFileInput that adds a hidden <name>_temp_path input when
    temp_path has been set on the widget instance

    The view is responsible for:
    - Saving the uploaded file to a temporary location on the first (failing)
      POST and storing the relative path + original filename on the request
    - Creating this widget via get_form with those values
    - Restoring the file from the temp path on the next POST (when no file
      is re-uploaded by the browser)
    """

    def __init__(self, *args, temp_path=None, original_filename=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.temp_path = temp_path
        self.original_filename = original_filename

    def render(self, name, value, attrs=None, renderer=None):
        html = super().render(name, value, attrs, renderer)
        if self.temp_path:
            html = html + format_html(
                '<input type="hidden" name="{}_temp_path" value="{}">',
                name,
                self.temp_path,
            )
        return html


class LocationCheckNumberInlineFormSet(BaseGenericInlineFormSet):
    def clean(self):
        """Check how many locations have been assigned to instance.
        If location is mandatory and no location has been assigned,
        raise ValidationError."""
        super().clean()

        errors = []

        # Get all forms that are not marked for deletion and have a
        # location assigned (that is they are not empty)
        forms = [
            form.cleaned_data
            for form in self.forms
            if form.cleaned_data.get("location", None)
            and not form.cleaned_data.get("DELETE", False)
        ]

        # Storage for the parent model
        storage = getattr(self.instance, "get_model_storage", lambda: None)()

        # If location is mandatory, check that at least one location is provided
        if storage and storage.mandatory_location and len(forms) == 0:
            # New object or existing object with no existing locations
            if not self.instance.pk or (
                self.instance.pk and not self.instance.locations.exists()
            ):
                raise ValidationError(
                    f"At least one {self.model._meta.verbose_name if self.model else 'item'} is required."
                )

        if errors:
            raise ValidationError(errors)
