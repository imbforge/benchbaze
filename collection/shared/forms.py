from django.contrib.contenttypes.forms import BaseGenericInlineFormSet
from django.forms import ValidationError


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

        raise ValidationError(errors)
