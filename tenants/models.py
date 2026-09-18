from django.contrib.postgres.fields import ArrayField
from django.db import models
from django_tenants.models import DomainMixin, TenantMixin

from collection.plasmid.models import PLASMID_STORAGE_TYPE_CHOICES


class Tenant(TenantMixin):
    lab_name = models.CharField(max_length=50, default="Smith", blank=False)
    site_title = models.CharField(max_length=255, default="BenchBaze - Smith")
    lab_abbreviation_for_files = models.CharField(
        max_length=10, default="", blank=False
    )
    worm_strain_regex = models.CharField(max_length=255, default="", blank=True)
    worm_strain_lab_id = models.CharField(max_length=50, default="", blank=True)
    worm_allele_lab_ids = ArrayField(
        base_field=models.CharField(max_length=50),
        default=list,
        blank=True,
    )
    worm_allele_lab_id = models.CharField(max_length=50, default="")
    ecoli_strain_ids = ArrayField(
        base_field=models.PositiveIntegerField(),
        default=list,
        blank=True,
    )
    plasmid_storage_type = models.CharField(
        max_length=20,
        choices=PLASMID_STORAGE_TYPE_CHOICES,
        default="plasmid",
    )
    helper_ecoli_virus_insect_id = models.PositiveIntegerField(
        null=True, blank=True, default=None
    )
    helper_cellline_virus_insect_id = models.PositiveIntegerField(
        null=True, blank=True, default=None
    )
    order_email_addresses = ArrayField(
        base_field=models.EmailField(max_length=255),
        default=list,
        blank=True,
    )
    oidc_allowed_groups = ArrayField(
        base_field=models.CharField(max_length=100),
        default=list,
        blank=True,
    )
    oidc_allowed_user_emails = ArrayField(
        base_field=models.EmailField(max_length=255),
        help_text="All emails should be in lowercase.",
        default=list,
        blank=True,
    )
    ms_teams_webhook_logger = models.URLField(max_length=500, blank=True, default="")
    ms_teams_webhook_purchasing = models.URLField(
        max_length=500, blank=True, default=""
    )
    snapgene_enabled = models.BooleanField(default=False)
    docs_url = models.URLField(max_length=500, blank=False, default="")

    created_on = models.DateTimeField(auto_now_add=True)
    trial = models.BooleanField(default=False)
    trial_start_date = models.DateField(null=True, blank=True)
    trial_end_date = models.DateField(null=True, blank=True)
    paid_until = models.DateField(null=True, blank=True)

    auto_create_schema = True

    def save(self, *args, **kwargs):
        self.site_title = f"BenchBaze @ {self.lab_name.title()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.schema_name


class Domain(DomainMixin):
    def __str__(self):
        return self.domain
