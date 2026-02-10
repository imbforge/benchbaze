from django.forms import ValidationError
from django.forms.models import BaseInlineFormSet


class AtLeastOneRequiredInlineFormSet(BaseInlineFormSet):
    # Source - https://stackoverflow.com/a
    # Posted by SuperFunkyMonkey, modified by community. See post 'Timeline' for change history
    # Retrieved 2026-01-27, License - CC BY-SA 3.0

    def clean(self):
        """Check that at least one service has been entered."""
        super().clean()
        if any(self.errors):
            return

        if not any(
            cleaned_data and not cleaned_data.get("DELETE", False)
            for cleaned_data in self.cleaned_data
            if "id" in cleaned_data.keys()  # exclude empty forms
        ):
            raise ValidationError(
                f"At least one {self.model._meta.verbose_name if self.model else 'item'} is required."
            )
