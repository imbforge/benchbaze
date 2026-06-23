from django.forms import ModelForm

from collection.virus.models import VirusInsect, VirusMammalian


class VirusBaseForm(ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        typ_e = cleaned_data.get("typ_e")

        if typ_e != "other":
            if not cleaned_data.get("helper_plasmids"):
                self.add_error(
                    "helper_plasmids",
                    "Helper plasmids must be set if type is not 'Other'",
                )

        return cleaned_data


class VirusInsectForm(VirusBaseForm):
    class Meta:
        model = VirusInsect
        fields = "__all__"


class VirusMammalianForm(VirusBaseForm):
    class Meta:
        model = VirusMammalian
        fields = "__all__"
