from django.forms import ValidationError

from common.forms import AtLeastOneRequiredInlineFormSet


class LocationInlineFormSet(AtLeastOneRequiredInlineFormSet):
    def clean(self):
        """Check that order levels start at 1 and are consecutive"""

        if any(self.errors):
            return
        super().clean()

        order_levels = [
            level
            for cleaned_data in self.cleaned_data
            if (level := cleaned_data.get("level", False))
            and not cleaned_data.get("DELETE", False)
        ]

        # Check if order levels start at 1 and are consecutive
        if not sorted(order_levels) == list(range(1, max(order_levels) + 1)):
            raise ValidationError("Order levels must start at 1 and be consecutive.")
